#!/usr/bin/env python3
"""La Bourse des cartes DeckFR : la cote de chaque carte d'après les vraies ventes au marché (dernier prix, prix
médian, nombre de ventes, variation), les dernières ventes, et les cartes en vente en ce moment au marché, lues dans
la base du bot (table cartes_marches) pour la page DeckFR. Les prix sont ramenés à l'exemplaire. Seules comptent les
ventes depuis l'ouverture officielle de DeckFR (deckfr.OUVERTURE), et à partir de DON grains l'exemplaire (en
dessous, c'est un cadeau entre membres). Les membres privés de cartes (users.blacklistCartes)
n'apparaissent pas.

Lancé toutes les heures par GitHub Actions avec le classement (.github/workflows/classement.yml). Le résultat,
bourse.json, est publié sur la branche « data » du dépôt, et le site le lit. Lecture seule, mêmes secrets que le
classement (CAFE_DB_URL et DISCORD_TOKEN).

Usage : python3 outils/bourse.py <fichier de sortie>
Nécessite PyMySQL (pip install pymysql).
"""
import collections
import datetime
import json
import os
import pathlib
import sys
import time

from classement import lire_adresse, profil, signaler
from deckfr import OUVERTURE, date_iso

VENTES = 12    # dernières ventes publiées
DON = 1000     # en dessous de ce prix par exemplaire, c'est un cadeau entre membres, pas un prix de marché
OFFRES = 24    # offres en cours publiées
# Une offre sans acheteur est encore en vente, sauf si son statut dit le contraire (comparé ici, en minuscules)
FINIES = {"annule", "annulé", "annulee", "annulée", "expire", "expiré", "expiree", "expirée", "retire", "retiré",
          "retiree", "retirée", "vendu", "vendue", "termine", "terminé", "clos", "ferme", "fermé", "supprime", "supprimé"}


def en_ms(v):
    try:
        v = int(v)
    except (TypeError, ValueError):
        return 0
    return v if v > 10**12 else v * 1000


def lire_base(adresse):
    import pymysql
    connexion = pymysql.connect(**lire_adresse(adresse), connect_timeout=10, read_timeout=30, charset="utf8mb4")
    try:
        with connexion.cursor() as c:
            try:
                c.execute("SET SESSION TRANSACTION READ ONLY")
            except pymysql.MySQLError:
                pass
            c.execute("SELECT id FROM users WHERE blacklistCartes = 1")
            exclus = {str(i) for (i,) in c.fetchall()}
            c.execute("SELECT id, nom, rarete FROM cartes_catalogue")
            cartes = {int(i): (str(n), int(r)) for i, n, r in c.fetchall()}
            c.execute("SELECT id, vendeur, acheteur, carte_id, quantite, prix, statut, cree_le, maj_le FROM cartes_marches")
            return exclus, cartes, c.fetchall()
    finally:
        connexion.close()


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    adresse, jeton = os.environ.get("CAFE_DB_URL", ""), os.environ.get("DISCORD_TOKEN", "")
    if not adresse or not jeton:
        signaler("Secrets CAFE_DB_URL et DISCORD_TOKEN à ajouter dans les réglages du dépôt : Bourse non publiée.", "warning")
        return 2
    try:
        exclus, cartes, marches = lire_base(adresse)
    except Exception as err:
        code = err.args[0] if getattr(err, "args", None) and isinstance(err.args[0], int) else ""
        signaler(f"Bourse illisible ({type(err).__name__} {code}) : rien n'est publié.".replace(" )", ")"), "warning")
        return 2

    # Le relevé des statuts du marché, pour vérifier FINIES (seulement des comptes)
    statuts = collections.Counter((str(s or "").strip().lower(), bool(str(a or "").strip())) for _, _, a, _, _, _, s, _, _ in marches)
    signaler("Statuts du marché : " + "; ".join(f"« {s} » {'avec' if a else 'sans'} acheteur : {n}" for (s, a), n in sorted(statuts.items())) + ".")

    debut = OUVERTURE.timestamp() * 1000
    ventes, offres = [], []
    for ident, vendeur, acheteur, carte_id, quantite, prix, statut, cree, maj in marches:
        if int(carte_id or 0) not in cartes or not prix or int(prix) <= 0:
            continue
        nom, rarete = cartes[int(carte_id)]
        q = max(1, int(quantite or 1))
        unitaire = round(int(prix) / q)
        vendu = bool(str(acheteur or "").strip())
        if vendu:
            quand = en_ms(maj) or en_ms(cree)
            if quand < debut or str(vendeur) in exclus or str(acheteur) in exclus or unitaire < DON:
                continue
            ventes.append({"carte": nom, "rarete": rarete, "prix": unitaire, "quantite": q, "date": date_iso(quand), "_t": quand})
        elif str(statut or "").strip().lower() not in FINIES and str(vendeur) not in exclus and en_ms(cree) >= debut:
            offres.append({"carte": nom, "rarete": rarete, "prix": unitaire, "quantite": q, "vendeur": str(vendeur), "date": date_iso(cree), "_t": en_ms(cree)})

    # La cote de chaque carte vendue : dernier prix, moyenne, nombre de ventes, variation depuis la vente d'avant
    ventes.sort(key=lambda v: v["_t"])
    par_carte = collections.defaultdict(list)
    for v in ventes:
        par_carte[v["carte"]].append(v)
    cotes = []
    for nom, liste in par_carte.items():
        prix = [v["prix"] for v in liste]
        tries = sorted(prix)
        milieu = len(tries) // 2
        mediane = tries[milieu] if len(tries) % 2 else round((tries[milieu - 1] + tries[milieu]) / 2)
        cote = {"carte": nom, "rarete": liste[-1]["rarete"], "dernier": prix[-1], "cote": mediane,
                "ventes": sum(v["quantite"] for v in liste), "date": liste[-1]["date"]}
        if len(prix) > 1 and prix[-2] > 0:
            cote["variation"] = round(100 * (prix[-1] - prix[-2]) / prix[-2], 1)
        cotes.append(cote)
    cotes.sort(key=lambda c: (-c["rarete"], -c["dernier"], c["carte"]))

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

    offres.sort(key=lambda o: -o["_t"])
    offres = offres[:OFFRES]
    for o in offres:
        o["vendeur"] = membre(o.pop("vendeur"))
        o.pop("_t")
    dernieres = [{k: v for k, v in x.items() if k != "_t"} for x in reversed(ventes[-VENTES:])]
    donnees = {"maj": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
               "chiffres": {"ventes": sum(v["quantite"] for v in ventes), "grains": sum(v["prix"] * v["quantite"] for v in ventes), "offres": len(offres)},
               "cotes": cotes, "ventes": dernieres, "offres": offres}
    sortie = pathlib.Path(sys.argv[1])
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    signaler(f"Bourse publiée : {len(cotes)} cartes cotées, {len(ventes)} ventes, {len(offres)} offres en cours.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
