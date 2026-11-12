#!/usr/bin/env python3
"""Le récap du dimanche, « Le Café du dimanche » : chaque dimanche à 18 h (heure de Paris), le résumé de la semaine
(lundi 0 h → dimanche 18 h). À la une, les chiffres (boosters ouverts, cartes tirées, nouveaux membres, grains échangés
au marché), le membre de la semaine, les grands tirages, la vente record, l'idée qui monte, les trésors trouvés, le pic
d'affluence et les records battus. Publié sur le site (recap.json, branche « data », page Info du jour) et posté sur
Discord par le webhook du secret DISCORD_WEBHOOK_RECAP (s'il est là).

Lancé toutes les heures avec le classement (.github/workflows/classement.yml) : il ne fait l'édition qu'une fois, le
dimanche à partir de 18 h. Il lit la base du bot en lecture seule, et les fichiers déjà relevés dans le dossier DONNEES
(classement.json, deckfr.json, records.json, idees.json, affluence.json).

Usage : python3 outils/recap.py <fichier de sortie> [--test]
  --test : fait l'édition tout de suite, sans la poster sur Discord (pour vérifier).
Nécessite PyMySQL (pip install pymysql).
"""
import datetime
import json
import os
import pathlib
import re
import sys
import time
import urllib.request
from zoneinfo import ZoneInfo

from classement import lire_adresse, profil, signaler
from deckfr import OUVERTURE
from bourse import DON

PARIS = ZoneInfo("Europe/Paris")
SITE = "https://cafe-fr.com"
COULEUR = 0xC99263
EDITIONS = 8   # éditions gardées
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
RECORDS = {  # les records du livre d'or suivis d'une semaine à l'autre
    "plus_de_boosters": "Le plus de boosters ouverts", "plus_de_mythiques": "Le plus de Mythiques",
    "grosse_ouverture": "La plus grosse ouverture", "vente_record": "La vente la plus chère",
}


def nombre(n):
    return f"{int(n):,}".replace(",", " ")


def court(n):
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".").replace(".", ",") + " M"
    if n >= 10_000:
        return f"{round(n / 1000)} k"
    return nombre(n)


def lire(dossier, nom):
    try:
        return json.loads((pathlib.Path(dossier) / nom).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def depuis(colonne, debut):
    """Condition SQL : l'horodatage `colonne` (en millisecondes ou en secondes) est après `debut`."""
    s = int(debut.timestamp())
    return f"({colonne} >= {s * 1000} OR ({colonne} < 100000000000 AND {colonne} >= {s}))"


def lire_base(adresse, debut):
    import pymysql
    connexion = pymysql.connect(**lire_adresse(adresse), connect_timeout=10, read_timeout=30, charset="utf8mb4")
    r = {}
    try:
        with connexion.cursor() as c:
            try:
                c.execute("SET SESSION TRANSACTION READ ONLY")
            except pymysql.MySQLError:
                pass

            def tous(sql, args=None):
                try:
                    c.execute(sql, args)
                    return c.fetchall()
                except pymysql.MySQLError as err:
                    code = err.args[0] if err.args and isinstance(err.args[0], int) else ""
                    signaler(f"Récap : lecture impossible ({type(err).__name__} {code}).".replace(" )", ")"), "warning")
                    return []

            exclus = {str(i) for (i,) in tous("SELECT id FROM users WHERE blacklistCartes = 1")}
            ligne = tous(f"SELECT COUNT(DISTINCT user_id), COALESCE(SUM(nb_boosters), 0) FROM cartes_ouvertures WHERE {depuis('cree_le', debut)}")
            r["joueurs"], r["boosters"] = (int(ligne[0][0]), int(ligne[0][1])) if ligne else (0, 0)
            par_rarete = dict(tous("SELECT oc.rarete, COUNT(*) FROM cartes_ouvertures_cartes oc JOIN cartes_ouvertures o ON o.id = oc.ouverture_id"
                                   f" WHERE {depuis('o.cree_le', debut)} GROUP BY oc.rarete"))
            r["tirees"] = sum(int(n) for n in par_rarete.values())
            r["mythiques"] = int(par_rarete.get(5, 0))
            grands = tous("SELECT o.user_id, k.nom, oc.rarete FROM cartes_ouvertures_cartes oc JOIN cartes_ouvertures o ON o.id = oc.ouverture_id"
                          " JOIN cartes_catalogue k ON k.id = oc.carte_id"
                          f" WHERE oc.rarete >= 4 AND oc.rarete <= 5 AND {depuis('o.cree_le', debut)} ORDER BY oc.rarete DESC, o.cree_le DESC LIMIT 40")
            r["grands"] = [(str(u), str(n), int(x)) for u, n, x in grands if str(u) not in exclus][:4]
            nouvelles = tous(f"SELECT nom, rarete FROM cartes_catalogue WHERE actif = 1 AND {depuis('cree_le', debut)} ORDER BY rarete DESC, id ASC")
            r["nouvelles"] = [(str(n), int(x)) for n, x in nouvelles]
            total = tous("SELECT COUNT(*) FROM cartes_catalogue WHERE actif = 1")
            r["cartes"] = int(total[0][0]) if total else 0
            ventes = tous("SELECT vendeur, acheteur, carte_id, quantite, prix FROM cartes_marches"
                          f" WHERE acheteur IS NOT NULL AND acheteur <> '' AND prix > 0 AND {depuis('maj_le', debut)}")
            noms = dict((int(i), (str(n), int(x))) for i, n, x in tous("SELECT id, nom, rarete FROM cartes_catalogue"))
            propres = []
            for v, a, carte, q, prix in ventes:
                q = max(1, int(q or 1))
                if str(v) in exclus or str(a) in exclus or int(prix) / q < DON or int(carte) not in noms:
                    continue
                propres.append((noms[int(carte)][0], noms[int(carte)][1], round(int(prix) / q), q))
            r["ventes"] = propres
            return r
    finally:
        connexion.close()


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sortie = pathlib.Path(sys.argv[1])
    test = "--test" in sys.argv[2:]
    maintenant = datetime.datetime.now(PARIS).replace(microsecond=0)
    archive = lire(sortie.parent, sortie.name) if sortie.exists() else {}
    editions = archive.get("editions", []) if isinstance(archive.get("editions"), list) else []
    if not test:
        if maintenant.weekday() != 6 or maintenant.hour < 18:
            return 2  # pas encore l'heure : rien à faire, sans bruit
        if editions and editions[0].get("date") == maintenant.date().isoformat():
            return 2  # l'édition de la semaine est déjà faite
    adresse, jeton = os.environ.get("CAFE_DB_URL", ""), os.environ.get("DISCORD_TOKEN", "")
    if not adresse or not jeton:
        signaler("Secrets CAFE_DB_URL et DISCORD_TOKEN à ajouter : récap non publié.", "warning")
        return 2
    lundi = (maintenant - datetime.timedelta(days=maintenant.weekday())).replace(hour=0, minute=0, second=0)
    debut = max(lundi, OUVERTURE.astimezone(PARIS))
    try:
        b = lire_base(adresse, debut)
    except Exception as err:
        code = err.args[0] if getattr(err, "args", None) and isinstance(err.args[0], int) else ""
        signaler(f"Récap : base injoignable ({type(err).__name__} {code}).".replace(" )", ")"), "warning")
        return 2
    dossier = os.environ.get("DONNEES", str(sortie.parent))
    classement, deckfr, records, idees, affluence = (lire(dossier, f) for f in ("classement.json", "deckfr.json", "records.json", "idees.json", "affluence.json"))
    profils = {}

    def membre(identifiant):
        if identifiant not in profils:
            try:
                profils[identifiant] = profil(identifiant, jeton)
            except Exception:
                profils[identifiant] = {"nom": "Membre", "avatar": None}
            time.sleep(.4)
        return profils[identifiant]

    def dans_la_semaine(iso):
        try:
            return datetime.datetime.fromisoformat(iso) >= debut
        except (TypeError, ValueError):
            return False

    e = {"numero": (max((int(x.get("numero", 0)) for x in editions), default=0) + 1) if not test else 0,
         "date": maintenant.date().isoformat(), "publication": maintenant.isoformat(),
         "semaine": {"debut": lundi.date().isoformat(), "fin": maintenant.date().isoformat()}}
    # Les chiffres de la semaine
    chiffres = [{"valeur": b["boosters"], "texte": "boosters ouverts"}, {"valeur": b["tirees"], "texte": "cartes tirées"}]
    ech = [x for x in affluence.get("echantillons", []) if len(x) == 3]
    if ech:
        cible = lundi.timestamp()
        proche = min(ech, key=lambda x: abs(x[0] - cible))
        if abs(proche[0] - cible) < 12 * 3600:
            chiffres.append({"valeur": ech[-1][2] - proche[2], "texte": "nouveaux membres", "signe": True})
        semaine = [x for x in ech if x[0] >= debut.timestamp()]
        if semaine:
            pic = max(semaine, key=lambda x: x[1])
            d = datetime.datetime.fromtimestamp(pic[0], PARIS)
            e["pic"] = {"nombre": pic[1], "texte": f"{JOURS[d.weekday()]} vers {d.hour} h"}
    if b["ventes"]:
        chiffres.append({"valeur": sum(p * q for _, _, p, q in b["ventes"]), "texte": "grains échangés au marché", "court": True})
    nouvelles_idees = [x for x in idees.get("idees", []) if dans_la_semaine(x.get("date"))]
    chiffres.append({"valeur": len(nouvelles_idees), "texte": "nouvelles idées" if len(nouvelles_idees) != 1 else "nouvelle idée"})
    e["chiffres"] = chiffres[:4]
    # Le membre de la semaine : la plus forte hausse de fortune
    ch = classement.get("champion_semaine") or {}
    if ch.get("gain", 0) > 0:
        e["membre"] = {"nom": ch.get("nom", "Membre"), "avatar": ch.get("avatar"), "gain": ch["gain"], "jours": ch.get("jours", 7)}
    # Les grands tirages de la semaine
    e["tirages"] = [{"carte": n, "rarete": x, "nom": membre(u)["nom"]} for u, n, x in b["grands"]]
    # La vente record de la semaine
    if b["ventes"]:
        carte, rarete, prix, q = max(b["ventes"], key=lambda v: v[2])
        e["bourse"] = {"carte": carte, "rarete": rarete, "prix": prix, "ventes": sum(q for *_, q in b["ventes"])}
    # Les trésors trouvés cette semaine (cartes bonus tirées pour la première fois)
    e["tresors"] = [{"carte": t["carte"], "nom": t.get("nom") or "un membre"} for t in deckfr.get("tresors", []) if dans_la_semaine(t.get("date"))]
    # L'idée qui monte : la plus soutenue des idées des deux dernières semaines
    recentes = [x for x in idees.get("idees", []) if x.get("date") and datetime.datetime.fromisoformat(x["date"]) >= debut - datetime.timedelta(days=7)]
    if recentes:
        x = max(recentes, key=lambda i: (i.get("pour", 0) - i.get("contre", 0), i.get("pour", 0)))
        if x.get("pour", 0) > 0:
            texte = x["texte"] if len(x["texte"]) <= 140 else x["texte"][:139].rsplit(" ", 1)[0] + "…"
            e["idee"] = {"texte": texte, "pour": x.get("pour", 0), "contre": x.get("contre", 0)}
    # Les records battus depuis l'édition précédente
    photo = {}
    for cle in RECORDS:
        r = (records.get("records") or {}).get(cle)
        if r:
            qui = (r.get("membre") or r.get("acheteur") or {}).get("nom") if isinstance(r.get("membre") or r.get("acheteur"), dict) else None
            photo[cle] = [qui, r.get("valeur")]
    avant = archive.get("photo") or {}
    e["records"] = [{"titre": RECORDS[c], "nom": v[0], "valeur": v[1]} for c, v in photo.items() if c in avant and avant[c] != v]
    # À la une
    if len(b["nouvelles"]) >= 3:
        mythiques = [n for n, x in b["nouvelles"] if x == 5][:3]
        e["une"] = {"titre": f"{len(b['nouvelles'])} nouvelles cartes débarquent dans DeckFR",
                    "texte": f"La plus grosse arrivée de la semaine{', avec ' + ', '.join(mythiques) + ' en Mythique' if mythiques else ''}. Le jeu compte maintenant {nombre(b['cartes'])} cartes, de quoi relancer la chasse."}
    elif e["tresors"]:
        t = e["tresors"][0]
        e["une"] = {"titre": f"{t['nom']} a trouvé {t['carte']}", "texte": "Une carte bonus est sortie d'un booster pour la première fois cette semaine."}
    elif b["mythiques"]:
        noms = ", ".join(x["carte"] for x in e["tirages"] if x["rarete"] == 5) or "des Mythiques"
        e["une"] = {"titre": f"{b['mythiques']} Mythique{'s' if b['mythiques'] > 1 else ''} tirée{'s' if b['mythiques'] > 1 else ''} cette semaine",
                    "texte": f"Au programme : {noms}. Les boosters n'ont pas chômé, avec {nombre(b['boosters'])} ouvertures."}
    else:
        e["une"] = {"titre": f"{nombre(b['boosters'])} boosters ouverts cette semaine", "texte": "Une semaine tranquille au café. Les cartes, elles, continuent de tourner."}

    if test:
        donnees = {"maj": maintenant.isoformat(), "editions": [e]}
    else:
        donnees = {"maj": maintenant.isoformat(), "photo": photo, "editions": ([e] + editions)[:EDITIONS]}
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    signaler(f"Récap {'de test ' if test else ''}publié : n° {e['numero']}, « {e['une']['titre']} ».")
    if not test:
        poster(e)
    return 0


def poster(e):
    webhook = os.environ.get("DISCORD_WEBHOOK_RECAP", "").strip()
    if not webhook:
        signaler("Secret DISCORD_WEBHOOK_RECAP absent : le récap est sur le site, pas sur Discord.")
        return
    if not re.match(r"^https://(discord|discordapp)\.com/api/webhooks/\d+/[\w-]+", webhook):
        signaler("DISCORD_WEBHOOK_RECAP n'est pas une adresse de webhook Discord : récap non posté.", "warning")
        return
    d, f = datetime.date.fromisoformat(e["semaine"]["debut"]), datetime.date.fromisoformat(e["semaine"]["fin"])
    champs = [{"name": c["texte"][:1].upper() + c["texte"][1:], "value": ("+" if c.get("signe") and c["valeur"] > 0 else "") + (court(c["valeur"]) if c.get("court") else nombre(c["valeur"])), "inline": True}
              for c in e["chiffres"]]
    if e.get("membre"):
        champs.append({"name": "Membre de la semaine", "value": f"{e['membre']['nom']} · +{court(e['membre']['gain'])} grains", "inline": True})
    if e.get("bourse"):
        champs.append({"name": "Record du marché", "value": f"{e['bourse']['carte']} · {court(e['bourse']['prix'])} grains", "inline": True})
    carte = {
        "author": {"name": f"☕ Le récap de la semaine · du {d.day} au {f.day} {MOIS[f.month - 1]}"},
        "title": e["une"]["titre"][:256], "url": f"{SITE}/info-du-jour/#recap",
        "description": e["une"]["texte"][:3000] + f"\n\n[Lire le récap complet sur cafe-fr.com]({SITE}/info-du-jour/#recap)",
        "color": COULEUR, "fields": champs[:6], "footer": {"text": "Le Café du dimanche · chaque dimanche à 18 h"},
        "timestamp": datetime.datetime.fromisoformat(e["publication"]).astimezone(datetime.timezone.utc).isoformat(),
    }
    requete = urllib.request.Request(webhook + ("&" if "?" in webhook else "?") + "wait=true",
                                     data=json.dumps({"username": "Le Café du dimanche", "embeds": [carte]}).encode("utf-8"),
                                     headers={"Content-Type": "application/json", "User-Agent": "cafe-fr.com (récap du dimanche)"}, method="POST")
    try:
        with urllib.request.urlopen(requete, timeout=20):
            signaler("Récap posté sur Discord.")
    except Exception as err:
        signaler(f"Récap non posté sur Discord ({type(err).__name__}).", "warning")


if __name__ == "__main__":
    sys.exit(main())
