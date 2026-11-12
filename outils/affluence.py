#!/usr/bin/env python3
"""Les heures d'affluence du café : chaque heure, le nombre de membres en ligne et le nombre total de membres, lus sur
l'invitation publique du serveur (discord.gg/france, sans secret). L'historique garde les 35 derniers jours ; le site
affiche la moyenne de chaque heure de chaque jour de la semaine sur les 28 derniers jours, à l'heure de Paris. Le récap
du dimanche s'en sert aussi (nouveaux membres, pic de la semaine).

Lancé toutes les heures par GitHub Actions avec le classement (.github/workflows/classement.yml). Le résultat,
affluence.json, est publié sur la branche « data » du dépôt, et le site le lit.

Usage : python3 outils/affluence.py <fichier de sortie> [historique précédent]
"""
import datetime
import json
import pathlib
import sys
import urllib.request
from zoneinfo import ZoneInfo

INVITATION = "https://discord.com/api/v10/invites/france?with_counts=true"
PARIS = ZoneInfo("Europe/Paris")
GARDE = 35      # jours d'historique
MOYENNE = 28    # jours pris pour la moyenne


def signaler(texte, niveau="notice"):
    import os
    print(f"::{niveau}::{texte}" if os.environ.get("GITHUB_ACTIONS") else texte)


def compter():
    requete = urllib.request.Request(INVITATION, headers={"User-Agent": "cafe-fr.com (heures d'affluence)", "Accept": "application/json"})
    with urllib.request.urlopen(requete, timeout=15) as r:
        d = json.load(r)
    return int(d["approximate_presence_count"]), int(d["approximate_member_count"])


def grille(echantillons, maintenant):
    """La moyenne des membres en ligne pour chaque jour (lundi = 0) et chaque heure, et le nombre de relevés."""
    somme = [[0] * 24 for _ in range(7)]
    nombre = [[0] * 24 for _ in range(7)]
    limite = maintenant.timestamp() - MOYENNE * 86400
    for t, en_ligne, _ in echantillons:
        if t < limite:
            continue
        d = datetime.datetime.fromtimestamp(t, PARIS)
        somme[d.weekday()][d.hour] += en_ligne
        nombre[d.weekday()][d.hour] += 1
    moyenne = [[round(somme[j][h] / nombre[j][h]) if nombre[j][h] else None for h in range(24)] for j in range(7)]
    return moyenne, nombre


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sortie = pathlib.Path(sys.argv[1])
    precedent = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else sortie
    echantillons = []
    try:
        echantillons = [tuple(x) for x in json.loads(precedent.read_text(encoding="utf-8")).get("echantillons", []) if len(x) == 3]
    except (OSError, ValueError):
        pass
    maintenant = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    try:
        en_ligne, membres = compter()
    except Exception as err:  # Discord injoignable : on garde l'historique tel quel
        signaler(f"Membres en ligne illisibles ({type(err).__name__}) : pas de relevé cette heure-ci.", "warning")
        if not echantillons:
            return 2
    else:
        # Un seul relevé par heure : une relance dans la même heure remplace le précédent
        heure = int(maintenant.timestamp()) // 3600
        echantillons = [x for x in echantillons if x[0] // 3600 != heure]
        echantillons.append((int(maintenant.timestamp()), en_ligne, membres))
    echantillons = sorted(x for x in echantillons if x[0] >= maintenant.timestamp() - GARDE * 86400)
    moyenne, nombre = grille(echantillons, maintenant)
    donnees = {
        "maj": maintenant.isoformat(),
        "debut": datetime.datetime.fromtimestamp(echantillons[0][0], datetime.timezone.utc).isoformat() if echantillons else None,
        "releves": len(echantillons),
        "moyenne": moyenne,
        "nombre": nombre,
        "echantillons": [list(x) for x in echantillons],
    }
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps(donnees, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    dernier = echantillons[-1] if echantillons else None
    signaler(f"Affluence : {len(echantillons)} relevés" + (f", {dernier[1]} en ligne sur {dernier[2]} membres." if dernier else "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
