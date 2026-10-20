#!/usr/bin/env python3
"""Classement des grains du serveur : le top 10 (poche et banque), lu dans la base du bot et publié sans rien de sensible.

Lancé toutes les 15 minutes par GitHub Actions (.github/workflows/classement.yml). Le résultat, classement.json,
est publié sur la branche « data » du dépôt, et le site le lit. Les identifiants de la base ne quittent jamais
GitHub : ils sont rangés dans les secrets du dépôt, jamais dans le site. La lecture se fait en lecture seule.

Variables d'environnement (secrets du dépôt) :
  CAFE_DB_URL     adresse de la base, au format jdbc:mysql://utilisateur:motdepasse@hôte:port/base
  DISCORD_TOKEN   jeton d'un bot Discord sans aucune permission, pour lire le pseudo et l'avatar des membres

Usage : python3 outils/classement.py <fichier de sortie>
Nécessite PyMySQL (pip install pymysql).
"""
import datetime
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

TAILLE = 10
API = "https://discord.com/api/v10"


def signaler(texte, niveau="notice"):
    # Dans GitHub Actions, le message s'affiche aussi dans le résumé de l'exécution
    print(f"::{niveau}::{texte}" if os.environ.get("GITHUB_ACTIONS") else texte)


def lire_adresse(adresse):
    u = urllib.parse.urlsplit(adresse.strip().removeprefix("jdbc:"))
    if u.scheme != "mysql" or not u.hostname or not u.username or not u.path.strip("/"):
        raise ValueError("CAFE_DB_URL doit avoir la forme jdbc:mysql://utilisateur:motdepasse@hôte:port/base")
    return {
        "host": u.hostname, "port": u.port or 3306, "database": u.path.strip("/"),
        "user": urllib.parse.unquote(u.username), "password": urllib.parse.unquote(u.password or ""),
    }


def meilleurs(adresse):
    import pymysql
    connexion = pymysql.connect(**lire_adresse(adresse), connect_timeout=10, read_timeout=20, charset="utf8mb4")
    try:
        with connexion.cursor() as c:
            # Lecture seule, par précaution : cette session ne peut rien modifier
            try:
                c.execute("SET SESSION TRANSACTION READ ONLY")
            except pymysql.MySQLError:
                pass
            # Le cumul : grains en poche et en banque. Les membres privés de grains (blacklistGrains) ne sont pas classés
            c.execute("SELECT id, COALESCE(grains, 0) + COALESCE(banque, 0) AS total FROM users"
                      " WHERE blacklistGrains IS NULL AND COALESCE(grains, 0) + COALESCE(banque, 0) > 0"
                      " ORDER BY total DESC LIMIT %s", (TAILLE,))
            return [(str(i), int(g)) for i, g in c.fetchall()]
    finally:
        connexion.close()


def profil(identifiant, jeton):
    requete = urllib.request.Request(f"{API}/users/{identifiant}", headers={
        "Authorization": f"Bot {jeton}", "User-Agent": "cafe-fr.com (classement)", "Accept": "application/json"})
    for essai in range(3):
        try:
            with urllib.request.urlopen(requete, timeout=15) as res:
                d = json.load(res)
            break
        except urllib.error.HTTPError as err:
            if err.code == 429 and essai < 2:  # trop d'appels : Discord dit combien de temps attendre
                try:
                    attente = float(json.load(err).get("retry_after", 2))
                except (ValueError, AttributeError):
                    attente = 2
                time.sleep(min(attente, 30) + .5)
                continue
            raise
    avatar = (f"https://cdn.discordapp.com/avatars/{identifiant}/{d['avatar']}.png?size=128" if d.get("avatar")
              else f"https://cdn.discordapp.com/embed/avatars/{(int(identifiant) >> 22) % 6}.png")
    return {"nom": d.get("global_name") or d.get("username") or "Membre", "avatar": avatar}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    adresse, jeton = os.environ.get("CAFE_DB_URL", ""), os.environ.get("DISCORD_TOKEN", "")
    if not adresse or not jeton:
        signaler("Secrets CAFE_DB_URL et DISCORD_TOKEN à ajouter dans les réglages du dépôt : rien n'est publié.", "warning")
        return 2
    try:
        top = meilleurs(adresse)
    except Exception as err:  # base injoignable : le site garde le classement précédent
        # Seulement le type et le code d'erreur : jamais le message, qui peut contenir l'hôte ou l'utilisateur
        code = err.args[0] if getattr(err, "args", None) and isinstance(err.args[0], int) else ""
        signaler(f"Base de données injoignable ({type(err).__name__} {code}) : classement non mis à jour.".replace(" )", ")"), "warning")
        return 2
    classement = []
    for rang, (identifiant, grains) in enumerate(top, 1):
        try:
            classement.append({"rang": rang, **profil(identifiant, jeton), "grains": grains})
        except Exception as err:
            signaler(f"Profil Discord du n°{rang} illisible ({type(err).__name__}).", "warning")
            classement.append({"rang": rang, "nom": "Membre", "avatar": None, "grains": grains})
        time.sleep(.4)  # Discord limite les appels rapprochés
    sortie = pathlib.Path(sys.argv[1])
    sortie.parent.mkdir(parents=True, exist_ok=True)
    maj = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    sortie.write_text(json.dumps({"maj": maj, "classement": classement}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    signaler(f"Classement publié : {len(classement)} membres.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
