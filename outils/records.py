#!/usr/bin/env python3
"""Les records de tous les temps du café, lus dans la base du bot pour le livre d'or (page Classement) :
le tout premier booster ouvert, la première carte Mythique tirée, la plus grosse ouverture d'un coup, le plus de
boosters ouverts, le plus de Mythiques tirées, le plus beau booster, la vente la plus chère au marché, et les cartes
la plus rare et la plus tirée. Les records du moment (fortune, série, #infini, collection, trésors) viennent déjà de
classement.json et deckfr.json : le site les lit là-bas.

Lancé toutes les heures par GitHub Actions avec le classement (.github/workflows/classement.yml). Le résultat,
records.json, est publié sur la branche « data » du dépôt, et le site le lit. Lecture seule, mêmes secrets que le
classement (CAFE_DB_URL et DISCORD_TOKEN). Les membres privés de cartes (users.blacklistCartes) n'apparaissent
dans aucun record. Seuls comptent les boosters ouverts depuis l'ouverture officielle de DeckFR (deckfr.OUVERTURE) :
les tests d'avant n'en font pas partie.

Usage : python3 outils/records.py <fichier de sortie>
Nécessite PyMySQL (pip install pymysql).
"""
import datetime
import json
import os
import pathlib
import sys
import time

from classement import lire_adresse, profil, signaler
from deckfr import apres_ouverture, date_iso


def lire_base(adresse):
    """Chaque record est lu à part : un souci sur l'un (table absente, colonne renommée) n'empêche pas de publier les
    autres. Les membres exclus sont filtrés ici, pas dans la base : users et cartes_* n'ont pas la même collation, une
    jointure de texte entre elles est refusée (erreur 1267). Les jointures se font sur les identifiants numériques."""
    import pymysql
    connexion = pymysql.connect(**lire_adresse(adresse), connect_timeout=10, read_timeout=30, charset="utf8mb4")
    r = {}
    try:
        with connexion.cursor() as c:
            # Lecture seule, par précaution : cette session ne peut rien modifier
            try:
                c.execute("SET SESSION TRANSACTION READ ONLY")
            except pymysql.MySQLError:
                pass

            def tous(sql, args=None):
                c.execute(sql, args)
                return c.fetchall()

            def partie(nom, lire, defaut=None):
                try:
                    return lire()
                except pymysql.MySQLError as err:
                    code = err.args[0] if err.args and isinstance(err.args[0], int) else ""
                    signaler(f"Records : {nom} illisible ({type(err).__name__} {code}).".replace(" )", ")"), "warning")
                    return defaut

            exclus = partie("membres exclus", lambda: {str(i) for (i,) in tous("SELECT id FROM users WHERE blacklistCartes = 1")}, set())
            libre = lambda i: i is not None and str(i) not in exclus and str(i).strip() != ""
            noms = {}

            def carte(identifiant):
                """Le nom et la rareté d'une carte du catalogue, lus une seule fois."""
                if identifiant not in noms:
                    ligne = partie("carte", lambda: tous("SELECT nom, rarete FROM cartes_catalogue WHERE id = %s", (identifiant,)), [])
                    noms[identifiant] = (str(ligne[0][0]), int(ligne[0][1])) if ligne else (None, None)
                return noms[identifiant]

            # Le tout premier booster ouvert au café
            lignes = partie("premier booster", lambda: tous(
                f"SELECT user_id, cree_le, nb_boosters FROM cartes_ouvertures WHERE {apres_ouverture('cree_le')}"
                " ORDER BY cree_le ASC, id ASC LIMIT 50"), [])
            for u, t, n in lignes:
                if libre(u):
                    r["premier_booster"] = {"membre": str(u), "date": date_iso(t), "boosters": int(n or 1)}
                    break

            # La première carte Mythique tirée
            lignes = partie("première Mythique", lambda: tous(
                "SELECT o.user_id, k.nom, o.cree_le FROM cartes_ouvertures_cartes oc"
                " JOIN cartes_ouvertures o ON o.id = oc.ouverture_id JOIN cartes_catalogue k ON k.id = oc.carte_id"
                f" WHERE oc.rarete = 5 AND {apres_ouverture('o.cree_le')} ORDER BY o.cree_le ASC, oc.position ASC LIMIT 50"), [])
            for u, nom, t in lignes:
                if libre(u):
                    r["premiere_mythique"] = {"membre": str(u), "carte": str(nom), "rarete": 5, "date": date_iso(t)}
                    break

            # La plus grosse ouverture d'un coup (le plus de boosters ouverts en une fois)
            lignes = partie("plus grosse ouverture", lambda: tous(
                f"SELECT user_id, nb_boosters, cree_le FROM cartes_ouvertures WHERE nb_boosters > 1 AND {apres_ouverture('cree_le')}"
                " ORDER BY nb_boosters DESC, cree_le ASC LIMIT 50"), [])
            for u, n, t in lignes:
                if libre(u):
                    r["grosse_ouverture"] = {"membre": str(u), "valeur": int(n), "date": date_iso(t)}
                    break

            # Le plus de boosters ouverts en tout (compté sur les ouvertures : le compteur des profils inclut les tests)
            lignes = partie("plus de boosters", lambda: tous(
                f"SELECT user_id, SUM(nb_boosters) AS n FROM cartes_ouvertures WHERE {apres_ouverture('cree_le')}"
                " GROUP BY user_id ORDER BY n DESC, MIN(cree_le) ASC LIMIT 50"), [])
            for u, n in lignes:
                if libre(u):
                    r["plus_de_boosters"] = {"membre": str(u), "valeur": int(n)}
                    break

            # Le plus de cartes Mythiques tirées
            lignes = partie("plus de Mythiques", lambda: tous(
                "SELECT o.user_id, COUNT(*) AS n FROM cartes_ouvertures_cartes oc JOIN cartes_ouvertures o ON o.id = oc.ouverture_id"
                f" WHERE oc.rarete = 5 AND {apres_ouverture('o.cree_le')} GROUP BY o.user_id ORDER BY n DESC, MIN(o.cree_le) ASC LIMIT 50"), [])
            for u, n in lignes:
                if libre(u):
                    r["plus_de_mythiques"] = {"membre": str(u), "valeur": int(n)}
                    break

            # Le plus beau booster : les 5 cartes d'un même booster, le plus de Mythiques puis de Légendaires (et mieux)
            lignes = partie("plus beau booster", lambda: tous(
                "SELECT oc.ouverture_id, oc.booster, SUM(oc.rarete = 5) AS m, SUM(oc.rarete >= 4) AS l, SUM(oc.rarete) AS s"
                " FROM cartes_ouvertures_cartes oc JOIN cartes_ouvertures o ON o.id = oc.ouverture_id"
                f" WHERE oc.rarete <= 5 AND {apres_ouverture('o.cree_le')} GROUP BY oc.ouverture_id, oc.booster"
                " HAVING l >= 2 ORDER BY m DESC, l DESC, s DESC, oc.ouverture_id ASC LIMIT 50"), [])
            for ouverture, booster, m, l, _ in lignes:
                qui = partie("ouverture", lambda: tous("SELECT user_id, cree_le FROM cartes_ouvertures WHERE id = %s", (ouverture,)), [])
                if not qui or not libre(qui[0][0]):
                    continue
                cartes = partie("cartes du booster", lambda: tous(
                    "SELECT k.nom, oc.rarete FROM cartes_ouvertures_cartes oc JOIN cartes_catalogue k ON k.id = oc.carte_id"
                    " WHERE oc.ouverture_id = %s AND oc.booster = %s ORDER BY oc.position ASC", (ouverture, booster)), [])
                r["plus_beau_booster"] = {"membre": str(qui[0][0]), "date": date_iso(qui[0][1]), "mythiques": int(m or 0),
                                          "legendaires": int(l or 0), "cartes": [{"nom": str(n), "rarete": int(x)} for n, x in cartes]}
                break

            # La vente la plus chère au marché
            lignes = partie("vente record", lambda: tous(
                "SELECT vendeur, acheteur, carte_id, quantite, prix, maj_le FROM cartes_marches"
                f" WHERE acheteur IS NOT NULL AND acheteur <> '' AND prix > 0 AND {apres_ouverture('maj_le')}"
                " ORDER BY prix DESC, maj_le ASC LIMIT 50"), [])
            for vendeur, acheteur, carte_id, quantite, prix, t in lignes:
                if libre(vendeur) and libre(acheteur):
                    nom, rarete = carte(carte_id)
                    if nom:
                        r["vente_record"] = {"vendeur": str(vendeur), "acheteur": str(acheteur), "carte": nom, "rarete": rarete,
                                             "quantite": int(quantite or 1), "valeur": int(prix), "date": date_iso(t)}
                        break

            # La carte la plus rare (la moins sortie des boosters) et la plus tirée, parmi les cartes encore en jeu
            sorties = partie("cartes sorties", lambda: tous(
                "SELECT k.nom, k.rarete, COUNT(*) AS n FROM cartes_ouvertures_cartes oc JOIN cartes_catalogue k ON k.id = oc.carte_id"
                " JOIN cartes_ouvertures o ON o.id = oc.ouverture_id"
                f" WHERE k.actif = 1 AND {apres_ouverture('o.cree_le')} GROUP BY k.id, k.nom, k.rarete ORDER BY n ASC, k.rarete DESC"), [])
            if sorties:
                nom, rarete, n = sorties[0]
                r["carte_plus_rare"] = {"carte": str(nom), "rarete": int(rarete), "valeur": int(n)}
                nom, rarete, n = max(sorties, key=lambda x: (int(x[2]), -int(x[1])))
                r["carte_plus_tiree"] = {"carte": str(nom), "rarete": int(rarete), "valeur": int(n)}
            return r
    finally:
        connexion.close()


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    adresse, jeton = os.environ.get("CAFE_DB_URL", ""), os.environ.get("DISCORD_TOKEN", "")
    if not adresse or not jeton:
        signaler("Secrets CAFE_DB_URL et DISCORD_TOKEN à ajouter dans les réglages du dépôt : records non publiés.", "warning")
        return 2
    try:
        records = lire_base(adresse)
    except Exception as err:  # base injoignable : le site garde les records précédents
        code = err.args[0] if getattr(err, "args", None) and isinstance(err.args[0], int) else ""
        signaler(f"Records illisibles ({type(err).__name__} {code}) : rien n'est publié.".replace(" )", ")"), "warning")
        return 2
    if not records:
        signaler("Aucun record lu : rien n'est publié.", "warning")
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

    # Les identifiants Discord ne sont jamais publiés : seulement le pseudo et l'avatar
    for record in records.values():
        for cle in ("membre", "vendeur", "acheteur"):
            if cle in record:
                record[cle] = membre(record[cle])
    sortie = pathlib.Path(sys.argv[1])
    sortie.parent.mkdir(parents=True, exist_ok=True)
    donnees = {"maj": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(), "records": records}
    sortie.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    signaler(f"Records publiés : {len(records)} ({', '.join(sorted(records))}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
