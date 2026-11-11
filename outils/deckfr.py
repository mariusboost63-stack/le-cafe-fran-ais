#!/usr/bin/env python3
"""DeckFR, le jeu de cartes du bot du café : chiffres du jeu, meilleurs collectionneurs, derniers grands tirages et
dernières cartes sorties, lus dans la base du bot (tables cartes_*) et publiés sans rien de sensible.

Lancé toutes les heures par GitHub Actions avec le classement (.github/workflows/classement.yml). Le résultat,
deckfr.json, est publié sur la branche « data » du dépôt, et le site le lit. La lecture se fait en lecture seule,
avec les mêmes secrets que le classement (CAFE_DB_URL, DISCORD_TOKEN). Les membres privés de cartes
(users.blacklistCartes) n'apparaissent dans aucune liste.

Usage : python3 outils/deckfr.py <fichier de sortie>
Nécessite PyMySQL (pip install pymysql).
"""
import datetime
import json
import os
import pathlib
import re
import sys
import time

from classement import lire_adresse, profil, signaler
from historique import Historique

TAILLE = 10       # collectionneurs
TIRAGES = 8       # derniers grands tirages
NOUVELLES = 8     # dernières cartes sorties


def date_iso(v):
    """Les dates du bot sont des horodatages (en millisecondes ou en secondes) : en date ISO, ou None."""
    try:
        v = int(v)
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    if v > 10**12:
        v //= 1000
    return datetime.datetime.fromtimestamp(v, datetime.timezone.utc).replace(microsecond=0).isoformat()


def image(valeur):
    """L'image d'une carte : une adresse https, ou le nom du fichier sur le serveur du bot (« Charlemagne_recto_….png »),
    que le site cherche dans son dossier cartes/."""
    u = str(valeur or "").strip()
    if u.startswith("https://") and len(u) < 500:
        return u
    return u if re.fullmatch(r"[\w.-]{1,120}\.(png|jpe?g|webp|gif)", u, re.I) else None


def lire_base(adresse):
    import pymysql
    connexion = pymysql.connect(**lire_adresse(adresse), connect_timeout=10, read_timeout=30, charset="utf8mb4")
    sortie = {}
    try:
        with connexion.cursor() as c:
            # Lecture seule, par précaution : cette session ne peut rien modifier
            try:
                c.execute("SET SESSION TRANSACTION READ ONLY")
            except pymysql.MySQLError:
                pass
            # Le catalogue : cartes en jeu, par rareté
            c.execute("SELECT rarete, COUNT(*) FROM cartes_catalogue WHERE actif = 1 GROUP BY rarete ORDER BY rarete")
            catalogue = {int(r): int(n) for r, n in c.fetchall()}
            total = sum(catalogue.values())
            # Les tirages réels : la part de chaque rareté parmi toutes les cartes sorties des boosters
            c.execute("SELECT rarete, COUNT(*) FROM cartes_ouvertures_cartes GROUP BY rarete")
            tirees = {int(r): int(n) for r, n in c.fetchall()}
            nb_tirees = sum(tirees.values())
            sortie["raretes"] = [{
                "niveau": r, "cartes": catalogue.get(r, 0), "tirees": tirees.get(r, 0),
                "tirage": round(100 * tirees.get(r, 0) / nb_tirees, 2) if nb_tirees else None,
            } for r in sorted(set(catalogue) | set(tirees))]
            # Chaque partie est lue à part : un souci sur l'une n'empêche pas de publier les autres
            def partie(nom, lire, defaut):
                try:
                    return lire()
                except pymysql.MySQLError as err:
                    code = err.args[0] if err.args and isinstance(err.args[0], int) else ""
                    signaler(f"DeckFR : {nom} illisible ({type(err).__name__} {code}).".replace(" )", ")"), "warning")
                    return defaut

            def un(sql, args=None):
                c.execute(sql, args)
                return c.fetchone()

            def tous(sql, args=None):
                c.execute(sql, args)
                return c.fetchall()

            # Les membres privés de cartes, lus à part : la table users n'a pas la même collation que les tables
            # cartes_*, une jointure de texte entre les deux est refusée par la base (erreur 1267)
            exclus = partie("membres exclus", lambda: {str(i) for (i,) in tous("SELECT id FROM users WHERE blacklistCartes = 1")}, set())
            # Les chiffres du jeu
            joueurs, boosters = partie("profils", lambda: tuple(int(x) for x in un(
                "SELECT COUNT(*), COALESCE(SUM(boosters_ouverts), 0) FROM cartes_profils WHERE boosters_ouverts > 0")), (0, 0))
            # Échanges conclus : les deux joueurs ont confirmé, ou le statut le dit (comparé ici, pas dans la base)
            faits = {"termine", "terminé", "accepte", "accepté", "conclu", "valide", "validé", "fini", "effectue", "effectué"}
            echanges = partie("échanges", lambda: sum(int(n) for statut, a, b, n in tous(
                "SELECT statut, conf_a, conf_b, COUNT(*) FROM cartes_echanges GROUP BY statut, conf_a, conf_b")
                if (a and b) or str(statut or "").strip().lower() in faits), 0)
            # Ventes au marché : une carte qui a trouvé un acheteur
            ventes, grains_marche = partie("marché", lambda: tuple(int(x) for x in un(
                "SELECT COUNT(*), COALESCE(SUM(prix), 0) FROM cartes_marches WHERE acheteur IS NOT NULL AND acheteur <> ''")), (0, 0))
            sortie["chiffres"] = {"cartes": total, "joueurs": joueurs, "boosters": boosters, "tirees": nb_tirees,
                                  "echanges": echanges, "ventes": ventes, "grains_marche": grains_marche}
            # Les deux raretés les plus hautes qu'on peut vraiment tirer : une rareté qui n'est jamais sortie d'un booster
            # (cartes spéciales, offertes à part) ne vide pas la liste des grands tirages
            max_rarete = max((r for r, n in tirees.items() if n), default=max(catalogue) if catalogue else 5)
            # Les meilleurs collectionneurs : le plus de cartes différentes (encore en jeu), sans les membres exclus
            # (toutes les collections : la photo du jour sert aux flèches de progression)
            toutes = partie("collections", lambda: tous(
                "SELECT c.user_id, COUNT(DISTINCT c.carte_id) AS n, COALESCE(SUM(c.quantite), 0)"
                " FROM cartes_collections c JOIN cartes_catalogue k ON k.id = c.carte_id AND k.actif = 1"
                " WHERE c.quantite > 0 GROUP BY c.user_id ORDER BY n DESC, MIN(c.premiere_obtention) ASC"), [])
            toutes = [(str(i), int(n), int(q)) for i, n, q in toutes if str(i) not in exclus]
            sortie["collections"] = {i: n for i, n, _ in toutes}
            sortie["top"] = toutes[:TAILLE]
            # Les derniers grands tirages : Légendaire et au-dessus (ou les deux raretés les plus hautes déjà sorties,
            # si le jeu en a moins), sans les membres exclus
            grands = partie("tirages", lambda: tous(
                "SELECT o.user_id, k.nom, oc.rarete, k.recto, o.cree_le FROM cartes_ouvertures_cartes oc"
                " JOIN cartes_ouvertures o ON o.id = oc.ouverture_id JOIN cartes_catalogue k ON k.id = oc.carte_id"
                " WHERE oc.rarete >= %s ORDER BY o.cree_le DESC, oc.position ASC LIMIT %s", (min(4, max_rarete - 1), TIRAGES * 5)), [])
            sortie["grands"] = [(str(i), str(nom), int(r), image(img), date_iso(t)) for i, nom, r, img, t in grands
                                if str(i) not in exclus][:TIRAGES]
            # Les cartes bonus (Mystère, Spécial) : qui a tiré chacune en premier, et quand. Sert aux chasses au trésor
            # (« la Mascotte d'Or est cachée dans les boosters ») : le site annonce le gagnant. Un membre exclu reste
            # anonyme, mais la carte compte bien comme trouvée.
            premieres = partie("cartes bonus", lambda: tous(
                "SELECT k.nom, oc.rarete, o.user_id, o.cree_le FROM cartes_ouvertures_cartes oc"
                " JOIN cartes_ouvertures o ON o.id = oc.ouverture_id JOIN cartes_catalogue k ON k.id = oc.carte_id"
                " WHERE oc.rarete >= 6 ORDER BY o.cree_le ASC, oc.position ASC LIMIT 500"), [])
            vues = {}
            for nom, r, i, t in premieres:
                vues.setdefault(str(nom), (str(nom), int(r), None if str(i) in exclus else str(i), date_iso(t)))
            sortie["tresors"] = list(vues.values())
            # Les dernières cartes sorties
            nouvelles = partie("catalogue récent", lambda: tous(
                "SELECT nom, rarete, recto, cree_le FROM cartes_catalogue WHERE actif = 1 ORDER BY cree_le DESC, id DESC LIMIT %s", (NOUVELLES,)), [])
            sortie["nouvelles"] = [{"nom": str(nom), "rarete": int(r), "image": image(img), "date": date_iso(t)} for nom, r, img, t in nouvelles]
            return sortie
    finally:
        connexion.close()


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    adresse, jeton = os.environ.get("CAFE_DB_URL", ""), os.environ.get("DISCORD_TOKEN", "")
    if not adresse or not jeton:
        signaler("Secrets CAFE_DB_URL et DISCORD_TOKEN à ajouter dans les réglages du dépôt : DeckFR non publié.", "warning")
        return 2
    try:
        d = lire_base(adresse)
    except Exception as err:  # base injoignable ou tables absentes : le site garde la version précédente
        code = err.args[0] if getattr(err, "args", None) and isinstance(err.args[0], int) else ""
        signaler(f"DeckFR illisible ({type(err).__name__} {code}) : rien n'est publié.".replace(" )", ")"), "warning")
        return 2
    profils = {}

    def membre(identifiant):
        if identifiant not in profils:
            try:
                profils[identifiant] = profil(identifiant, jeton)
            except Exception as err:
                signaler(f"Profil Discord illisible ({type(err).__name__}).", "warning")
                profils[identifiant] = {"nom": "Membre", "avatar": None}
            time.sleep(.4)  # Discord limite les appels rapprochés
        return profils[identifiant]

    total = d["chiffres"]["cartes"] or 1
    meilleurs = d.pop("top")
    historique = Historique(os.environ.get("HISTORIQUE"))
    evolutions = historique.evolutions("deckfr", [(i, n) for i, n, _ in meilleurs])
    historique.photo("deckfr", d.pop("collections"))
    collectionneurs = []
    for rang, ((i, n, q), evo) in enumerate(zip(meilleurs, evolutions), 1):
        ligne = {"rang": rang, **membre(i), "cartes": n, "pourcent": round(100 * n / total, 1), "exemplaires": q}
        if evo is not None:
            ligne["evolution"] = evo
        collectionneurs.append(ligne)
    grands = [{**membre(i), "carte": nom, "rarete": r, "image": img, "date": quand} for i, nom, r, img, quand in d.pop("grands")]
    tresors = [{"carte": nom, "rarete": r, "date": quand, **(membre(i) if i else {})} for nom, r, i, quand in d.pop("tresors", [])]
    donnees = {"maj": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(), **d,
               "collectionneurs": collectionneurs, "grands_tirages": grands, "tresors": tresors}
    sortie = pathlib.Path(sys.argv[1])
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    historique.enregistrer()
    signaler(f"DeckFR publié : {d['chiffres']['cartes']} cartes, {len(collectionneurs)} collectionneurs, {len(grands)} grands tirages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
