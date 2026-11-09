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
import sys
import time

from classement import lire_adresse, profil, signaler

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


def image(url):
    u = str(url or "").strip()
    return u if u.startswith("https://") and len(u) < 500 else None


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
                "niveau": r, "cartes": catalogue.get(r, 0),
                "tirage": round(100 * tirees.get(r, 0) / nb_tirees, 2) if nb_tirees else None,
            } for r in sorted(set(catalogue) | set(tirees))]
            # Les chiffres du jeu
            c.execute("SELECT COUNT(*), COALESCE(SUM(boosters_ouverts), 0) FROM cartes_profils WHERE boosters_ouverts > 0")
            joueurs, boosters = (int(x) for x in c.fetchone())
            # Échanges conclus : les deux joueurs ont confirmé, ou le statut le dit
            c.execute("SELECT COUNT(*) FROM cartes_echanges WHERE (conf_a = 1 AND conf_b = 1)"
                      " OR LOWER(statut) IN ('termine', 'terminé', 'accepte', 'accepté', 'conclu', 'valide', 'validé', 'fini', 'effectue', 'effectué')")
            echanges = int(c.fetchone()[0])
            # Ventes au marché : une carte qui a trouvé un acheteur
            c.execute("SELECT COUNT(*), COALESCE(SUM(prix), 0) FROM cartes_marches WHERE acheteur IS NOT NULL AND acheteur <> ''")
            ventes, grains_marche = (int(x) for x in c.fetchone())
            sortie["chiffres"] = {"cartes": total, "joueurs": joueurs, "boosters": boosters, "tirees": nb_tirees,
                                  "echanges": echanges, "ventes": ventes, "grains_marche": grains_marche}
            max_rarete = max(catalogue) if catalogue else 5
            # Les meilleurs collectionneurs : le plus de cartes différentes (encore en jeu)
            c.execute("SELECT c.user_id, COUNT(DISTINCT c.carte_id) AS n, COALESCE(SUM(c.quantite), 0)"
                      " FROM cartes_collections c JOIN cartes_catalogue k ON k.id = c.carte_id AND k.actif = 1"
                      " LEFT JOIN users u ON u.id = c.user_id"
                      " WHERE c.quantite > 0 AND COALESCE(u.blacklistCartes, 0) = 0"
                      " GROUP BY c.user_id ORDER BY n DESC, MIN(c.premiere_obtention) ASC LIMIT %s", (TAILLE,))
            sortie["top"] = [(str(i), int(n), int(q)) for i, n, q in c.fetchall()]
            # Les derniers grands tirages : les deux raretés les plus hautes
            c.execute("SELECT o.user_id, k.nom, oc.rarete, k.recto, o.cree_le FROM cartes_ouvertures_cartes oc"
                      " JOIN cartes_ouvertures o ON o.id = oc.ouverture_id JOIN cartes_catalogue k ON k.id = oc.carte_id"
                      " LEFT JOIN users u ON u.id = o.user_id"
                      " WHERE oc.rarete >= %s AND COALESCE(u.blacklistCartes, 0) = 0"
                      " ORDER BY o.cree_le DESC, oc.position ASC LIMIT %s", (max_rarete - 1, TIRAGES))
            sortie["grands"] = [(str(i), str(nom), int(r), image(img), date_iso(t)) for i, nom, r, img, t in c.fetchall()]
            # Les dernières cartes sorties
            c.execute("SELECT nom, rarete, recto, cree_le FROM cartes_catalogue WHERE actif = 1 ORDER BY cree_le DESC, id DESC LIMIT %s", (NOUVELLES,))
            sortie["nouvelles"] = [{"nom": str(nom), "rarete": int(r), "image": image(img), "date": date_iso(t)} for nom, r, img, t in c.fetchall()]
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
    collectionneurs = [{"rang": rang, **membre(i), "cartes": n, "pourcent": round(100 * n / total, 1), "exemplaires": q}
                       for rang, (i, n, q) in enumerate(d.pop("top"), 1)]
    grands = [{**membre(i), "carte": nom, "rarete": r, "image": img, "date": quand} for i, nom, r, img, quand in d.pop("grands")]
    donnees = {"maj": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(), **d,
               "collectionneurs": collectionneurs, "grands_tirages": grands}
    sortie = pathlib.Path(sys.argv[1])
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    signaler(f"DeckFR publié : {d['chiffres']['cartes']} cartes, {len(collectionneurs)} collectionneurs, {len(grands)} grands tirages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
