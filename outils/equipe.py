#!/usr/bin/env python3
"""Les photos de profil de l'équipe (page Équipe), tenues à jour toutes les heures : quand un membre du staff change
de photo sur Discord, le site suit tout seul.

Les membres de l'équipe sont ceux de la page (index.html, leur @pseudo sur chaque badge). Chacun est retrouvé sur
Discord par son pseudo :
  1. sur le serveur, si le bot du jeton DISCORD_TOKEN en fait partie : la photo propre au serveur passe en premier ;
  2. sinon, parmi les membres de l'équipe connus de la base du bot (tickets traités, absences, quêtes validées).
Un membre introuvable garde la photo enregistrée dans la page. Pour ajouter ou retirer quelqu'un, il suffit de
modifier son badge dans index.html.

Lancé toutes les heures par GitHub Actions avec le classement (.github/workflows/classement.yml). Le résultat,
equipe.json (pseudo → adresse de la photo sur Discord), est publié sur la branche « data », et le site le lit.
Lecture seule, mêmes secrets que le classement (CAFE_DB_URL et DISCORD_TOKEN).

Usage : python3 outils/equipe.py <fichier de sortie>
Nécessite PyMySQL (pip install pymysql) pour la recherche dans la base.
"""
import datetime
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from classement import API, lire_adresse, signaler

SERVEUR = "829698572927762432"
SOURCE = pathlib.Path(__file__).resolve().parent.parent / "index.html"
# Les colonnes de la base où apparaissent des membres de l'équipe
COLONNES = [("tickets_stats", "staff"), ("tickets_stats", "fermePar"), ("tickets", "staff"), ("staff_absences", "user_id"),
            ("halloween_soumissions", "staff"), ("halloween_ajustements", "staff")]
CANDIDATS_MAX = 80  # identifiants demandés à Discord au plus, par relevé


def pseudos():
    """Les @pseudos de l'équipe, tels qu'écrits sur les badges de la page, en minuscules et sans @."""
    texte = SOURCE.read_text(encoding="utf-8")
    return sorted({p.strip().lower() for p in re.findall(r'class="profil-pseudo">@([^<]+)<', texte) if p.strip()})


def appel(chemin, jeton):
    requete = urllib.request.Request(f"{API}{chemin}", headers={
        "Authorization": f"Bot {jeton}", "User-Agent": "cafe-fr.com (equipe)", "Accept": "application/json"})
    for essai in range(3):
        try:
            with urllib.request.urlopen(requete, timeout=15) as res:
                return json.load(res)
        except urllib.error.HTTPError as err:
            if err.code == 429 and essai < 2:  # trop d'appels : Discord dit combien de temps attendre
                try:
                    attente = float(json.load(err).get("retry_after", 2))
                except (ValueError, AttributeError):
                    attente = 2
                time.sleep(min(attente, 30) + .5)
                continue
            raise


def photo(utilisateur, membre=None):
    """L'adresse de la photo : celle propre au serveur d'abord, puis celle du compte, puis l'avatar par défaut."""
    i = str(utilisateur["id"])
    if membre and membre.get("avatar"):
        return f"https://cdn.discordapp.com/guilds/{SERVEUR}/users/{i}/avatars/{membre['avatar']}.png?size=128"
    if utilisateur.get("avatar"):
        return f"https://cdn.discordapp.com/avatars/{i}/{utilisateur['avatar']}.png?size=128"
    return f"https://cdn.discordapp.com/embed/avatars/{(int(i) >> 22) % 6}.png"


def par_le_serveur(cherches, jeton):
    """Chaque pseudo cherché parmi les membres du serveur. Rien si le bot n'en fait pas partie."""
    trouves = {}
    for p in cherches:
        try:
            membres = appel(f"/guilds/{SERVEUR}/members/search?" + urllib.parse.urlencode({"query": p, "limit": 10}), jeton)
        except urllib.error.HTTPError as err:
            signaler(f"Recherche sur le serveur impossible (HTTP {err.code}) : recherche dans la base.")
            return trouves
        for m in membres if isinstance(membres, list) else []:
            u = m.get("user") or {}
            if str(u.get("username", "")).lower() == p:
                trouves[p] = photo(u, m)
        time.sleep(.4)  # Discord limite les appels rapprochés
    return trouves


def candidats(adresse):
    """Les identifiants des membres de l'équipe connus de la base du bot."""
    import pymysql
    connexion = pymysql.connect(**lire_adresse(adresse), connect_timeout=10, read_timeout=30, charset="utf8mb4")
    ids = set()
    try:
        with connexion.cursor() as c:
            try:
                c.execute("SET SESSION TRANSACTION READ ONLY")
            except pymysql.MySQLError:
                pass
            for table, colonne in COLONNES:
                try:
                    c.execute(f"SELECT DISTINCT `{colonne}` FROM `{table}`")
                except pymysql.MySQLError:
                    continue  # table absente ou renommée dans le bot
                ids |= {str(x).strip() for (x,) in c.fetchall() if re.fullmatch(r"\d{15,21}", str(x or "").strip())}
    finally:
        connexion.close()
    return sorted(ids)


def par_la_base(cherches, adresse, jeton):
    trouves = {}
    try:
        ids = candidats(adresse)
    except Exception as err:  # base injoignable : seulement le type d'erreur, jamais le message (hôte, utilisateur)
        signaler(f"Base de données injoignable ({type(err).__name__}) : photos de l'équipe cherchées sur le serveur seulement.", "warning")
        return trouves
    for i in ids[:CANDIDATS_MAX]:
        if set(cherches) <= set(trouves):
            break
        try:
            u = appel(f"/users/{i}", jeton)
        except Exception:
            continue
        p = str(u.get("username", "")).lower()
        if p in cherches and p not in trouves:
            trouves[p] = photo(u)
        time.sleep(.4)
    return trouves


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    adresse, jeton = os.environ.get("CAFE_DB_URL", ""), os.environ.get("DISCORD_TOKEN", "")
    if not jeton:
        signaler("Secret DISCORD_TOKEN à ajouter dans les réglages du dépôt : photos de l'équipe non mises à jour.", "warning")
        return 2
    cherches = pseudos()
    if not cherches:
        signaler("Aucun @pseudo trouvé sur les badges de l'équipe (index.html).", "warning")
        return 2
    trouves = par_le_serveur(cherches, jeton)
    reste = [p for p in cherches if p not in trouves]
    if reste and adresse:
        trouves.update(par_la_base(reste, adresse, jeton))
    manquants = [p for p in cherches if p not in trouves]
    signaler(f"Photos de l'équipe : {len(trouves)} sur {len(cherches)}"
             + (f" (introuvables : {', '.join('@' + p for p in manquants)})" if manquants else "") + ".")
    if not trouves:
        return 2  # le site garde les photos précédentes
    maj = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    sortie = pathlib.Path(sys.argv[1])
    sortie.write_text(json.dumps({"maj": maj, "avatars": dict(sorted(trouves.items()))}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
