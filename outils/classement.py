#!/usr/bin/env python3
"""Classements du serveur, lus dans la base du bot et publiés sans rien de sensible : le top 10 des grains (poche et
banque), le top 10 du salon #infini (nombres postés) et le compteur total de #infini.

Lancé toutes les heures par GitHub Actions (.github/workflows/classement.yml). Le résultat, classement.json,
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


def lire_base(adresse):
    """Le top 10 des grains, le compteur du salon #infini (None s'il est illisible) et le top 10 de #infini
    (liste vide s'il est illisible). Les tops sont des listes (identifiant, valeur)."""
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
            top = [(str(i), int(g)) for i, g in c.fetchall()]
            # Le salon #infini : le total des nombres postés par tous les membres (infiniStats)
            try:
                c.execute("SELECT COALESCE(SUM(infiniStats), 0) FROM users")
                infini = int(c.fetchone()[0])
            except pymysql.MySQLError:
                infini = None
            # Le classement de #infini : les membres qui y ont posté le plus de nombres
            try:
                c.execute("SELECT id, infiniStats FROM users WHERE infiniStats > 0 ORDER BY infiniStats DESC LIMIT %s", (TAILLE,))
                top_infini = [(str(i), int(n)) for i, n in c.fetchall()]
            except pymysql.MySQLError:
                top_infini = []
            return top, infini, top_infini
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
        top, infini, top_infini = lire_base(adresse)
    except Exception as err:  # base injoignable : le site garde le classement précédent
        # Seulement le type et le code d'erreur : jamais le message, qui peut contenir l'hôte ou l'utilisateur
        code = err.args[0] if getattr(err, "args", None) and isinstance(err.args[0], int) else ""
        signaler(f"Base de données injoignable ({type(err).__name__} {code}) : classement non mis à jour.".replace(" )", ")"), "warning")
        return 2
    profils = {}  # un membre présent dans les deux classements n'est demandé qu'une fois à Discord

    def classer(top, cle, quoi):
        liste = []
        for rang, (identifiant, valeur) in enumerate(top, 1):
            if identifiant not in profils:
                try:
                    profils[identifiant] = profil(identifiant, jeton)
                except Exception as err:
                    signaler(f"Profil Discord du n°{rang} ({quoi}) illisible ({type(err).__name__}).", "warning")
                    profils[identifiant] = {"nom": "Membre", "avatar": None}
                time.sleep(.4)  # Discord limite les appels rapprochés
            liste.append({"rang": rang, **profils[identifiant], cle: valeur})
        return liste

    classement = classer(top, "grains", "grains")
    classement_infini = classer(top_infini, "nombres", "#infini")
    sortie = pathlib.Path(sys.argv[1])
    sortie.parent.mkdir(parents=True, exist_ok=True)
    maj = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    donnees = {"maj": maj, "classement": classement}
    if infini is not None:
        donnees["infini"] = infini
    if classement_infini:
        donnees["infini_classement"] = classement_infini
    sortie.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    signaler(f"Classements publiés : {len(classement)} membres (grains), {len(classement_infini)} (#infini) ; compteur #infini : {infini}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
