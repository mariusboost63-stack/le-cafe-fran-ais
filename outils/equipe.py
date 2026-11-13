#!/usr/bin/env python3
"""Les photos de profil de l'équipe (page Équipe), tenues à jour toutes les heures : quand un membre du staff change
de photo sur Discord, le site suit tout seul.

Les membres de l'équipe sont ceux de la page (index.html, leur @pseudo sur chaque badge). Chacun est retrouvé sur
Discord par son pseudo :
  1. ceux déjà retrouvés à un relevé précédent : leur photo est relue directement ;
  2. sur le serveur, si le bot du jeton DISCORD_TOKEN en fait partie (la photo propre au serveur passe en premier) ;
  3. sinon, parmi les membres connus de la base du bot : d'abord le staff (tickets, candidatures, absences, quêtes),
     puis les joueurs du casino. Chaque membre n'est demandé qu'une fois à Discord : le relevé garde une empreinte
     de ceux déjà vus (jamais leur identifiant ni leur pseudo en clair).
Un membre introuvable garde la photo enregistrée dans la page. Pour ajouter ou retirer quelqu'un, il suffit de
modifier son badge dans index.html (le @pseudo doit être son nom d'utilisateur Discord).

Lancé toutes les heures par GitHub Actions avec le classement (.github/workflows/classement.yml). Le résultat,
equipe.json (pseudo → adresse de la photo sur Discord), est publié sur la branche « data », et le site le lit.
La mémoire des recherches (equipe-cache.json, variable CACHE_EQUIPE) reste sur la branche data, hors du site.
Lecture seule, mêmes secrets que le classement (CAFE_DB_URL et DISCORD_TOKEN).

Usage : python3 outils/equipe.py <fichier de sortie>
Nécessite PyMySQL (pip install pymysql) pour la recherche dans la base.
"""
import datetime
import hashlib
import hmac
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
# Où chercher des membres de l'équipe dans la base, dans l'ordre : le staff d'abord, puis les joueurs du casino
REQUETES = [
    "SELECT DISTINCT `staff` FROM `tickets_stats`",
    "SELECT DISTINCT `fermePar` FROM `tickets_stats`",
    "SELECT DISTINCT `staff` FROM `tickets`",
    "SELECT DISTINCT `staff` FROM `candidatures`",
    "SELECT DISTINCT `user` FROM `candidatures`",
    "SELECT DISTINCT `user_id` FROM `staff_absences`",
    "SELECT DISTINCT `staff` FROM `halloween_soumissions`",
    "SELECT DISTINCT `staff` FROM `halloween_ajustements`",
    "SELECT `id` FROM `users` WHERE `casino` IS NOT NULL AND `casino` <> 0 ORDER BY `casino` DESC",
]
DEMANDES_MAX = 250  # nouveaux membres demandés à Discord au plus, par relevé (la suite au relevé suivant)


def pseudos():
    """Les @pseudos de l'équipe, tels qu'écrits sur les badges de la page, en minuscules et sans @."""
    texte = SOURCE.read_text(encoding="utf-8")
    return sorted({p.strip().lower() for p in re.findall(r'class="profil-pseudo">@([^<]+)<', texte) if p.strip()})


class Memoire:
    """Ce que le relevé retient d'une heure à l'autre : l'identifiant des membres de l'équipe déjà retrouvés, et une
    empreinte (non réversible, liée au secret de la base) de chaque membre déjà vu avec celle de son pseudo."""

    def __init__(self, chemin):
        self.chemin = pathlib.Path(chemin) if chemin else None
        self.cle = hashlib.sha256(("cafe-fr/equipe|" + os.environ.get("CAFE_DB_URL", "")).encode()).digest()
        d = {}
        if self.chemin and self.chemin.exists():
            try:
                d = json.loads(self.chemin.read_text(encoding="utf-8"))
            except ValueError:
                d = {}
        self.ids = {str(k): str(v) for k, v in (d.get("ids") or {}).items()}
        self.vus = {str(k): str(v) for k, v in (d.get("vus") or {}).items()}

    def empreinte(self, texte):
        return hmac.new(self.cle, str(texte).encode(), hashlib.sha256).hexdigest()[:16]

    def ecrire(self):
        if self.chemin:
            self.chemin.write_text(json.dumps({"ids": dict(sorted(self.ids.items())), "vus": dict(sorted(self.vus.items()))},
                                              indent=0) + "\n", encoding="utf-8")


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


def nom(utilisateur):
    return str((utilisateur or {}).get("username", "")).lower()


def photo(utilisateur, membre=None):
    """L'adresse de la photo : celle propre au serveur d'abord, puis celle du compte, puis l'avatar par défaut."""
    i = str(utilisateur["id"])
    if membre and membre.get("avatar"):
        return f"https://cdn.discordapp.com/guilds/{SERVEUR}/users/{i}/avatars/{membre['avatar']}.png?size=128"
    if utilisateur.get("avatar"):
        return f"https://cdn.discordapp.com/avatars/{i}/{utilisateur['avatar']}.png?size=128"
    return f"https://cdn.discordapp.com/embed/avatars/{(int(i) >> 22) % 6}.png"


def deja_trouves(cherches, jeton, memoire, trouves):
    for p in cherches:
        i = memoire.ids.get(p)
        if not i:
            continue
        try:
            u = appel(f"/users/{i}", jeton)
        except Exception:
            continue
        if nom(u) == p:
            trouves[p] = photo(u)
        else:
            del memoire.ids[p]  # il a changé de pseudo : on le recherchera
        time.sleep(.3)


def par_le_serveur(cherches, jeton, memoire, trouves):
    """Chaque pseudo cherché parmi les membres du serveur. Rien si le bot n'en fait pas partie."""
    for p in cherches:
        try:
            membres = appel(f"/guilds/{SERVEUR}/members/search?" + urllib.parse.urlencode({"query": p, "limit": 10}), jeton)
        except urllib.error.HTTPError as err:
            signaler(f"Recherche sur le serveur impossible (HTTP {err.code}, le bot n'en fait pas partie) : recherche dans la base.")
            return
        for m in membres if isinstance(membres, list) else []:
            u = m.get("user") or {}
            if nom(u) == p:
                trouves[p] = photo(u, m)
                memoire.ids[p] = str(u["id"])
        time.sleep(.3)


def candidats(adresse):
    """Les identifiants des membres à vérifier, dans l'ordre de REQUETES, sans doublon."""
    import pymysql
    connexion = pymysql.connect(**lire_adresse(adresse), connect_timeout=10, read_timeout=30, charset="utf8mb4")
    ids = {}
    try:
        with connexion.cursor() as c:
            try:
                c.execute("SET SESSION TRANSACTION READ ONLY")
            except pymysql.MySQLError:
                pass
            for requete in REQUETES:
                try:
                    c.execute(requete)
                except pymysql.MySQLError:
                    continue  # table ou colonne absente dans le bot
                for (x,) in c.fetchall():
                    x = str(x or "").strip()
                    if re.fullmatch(r"\d{15,21}", x):
                        ids.setdefault(x, None)
    finally:
        connexion.close()
    return list(ids)


def par_la_base(cherches, adresse, jeton, memoire, trouves):
    try:
        ids = candidats(adresse)
    except Exception as err:  # base injoignable : seulement le type d'erreur, jamais le message (hôte, utilisateur)
        signaler(f"Base de données injoignable ({type(err).__name__}) : photos de l'équipe non cherchées dans la base.", "warning")
        return
    voulus = {memoire.empreinte(p) for p in cherches}
    demandes = 0
    for i in ids:
        if all(p in trouves for p in cherches):
            break
        e = memoire.empreinte(i)
        connu = memoire.vus.get(e)
        if connu is not None and connu not in voulus:
            continue  # déjà vu, et ce n'est pas un membre de l'équipe
        if connu is None and demandes >= DEMANDES_MAX:
            continue
        try:
            u = appel(f"/users/{i}", jeton)
        except urllib.error.HTTPError as err:
            if err.code == 404:
                memoire.vus[e] = ""
            continue
        except Exception:
            continue
        demandes += connu is None
        n = nom(u)
        memoire.vus[e] = memoire.empreinte(n)
        if n in cherches and n not in trouves:
            trouves[n] = photo(u)
            memoire.ids[n] = i
        time.sleep(.25)
    restants = sum(1 for i in ids if memoire.empreinte(i) not in memoire.vus)
    signaler(f"Base du bot : {len(ids)} membres à vérifier, {demandes} demandés à Discord ce relevé"
             + (f", {restants} pour les prochains." if restants else ", tous vus."))


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
    memoire = Memoire(os.environ.get("CACHE_EQUIPE"))
    trouves = {}
    deja_trouves(cherches, jeton, memoire, trouves)
    if any(p not in trouves for p in cherches):
        par_le_serveur([p for p in cherches if p not in trouves], jeton, memoire, trouves)
    if any(p not in trouves for p in cherches) and adresse:
        par_la_base([p for p in cherches if p not in trouves], adresse, jeton, memoire, trouves)
    memoire.ecrire()
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
