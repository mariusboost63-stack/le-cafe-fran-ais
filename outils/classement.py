#!/usr/bin/env python3
"""Classements du serveur, lus dans la base du bot et publiés sans rien de sensible : le top 10 des grains (poche et
banque), de #infini (nombres postés), du temps en vocal et de la série de /journalier, avec la progression depuis
hier (historique.py), le champion de la semaine, les chiffres de l'économie et les postes ouverts au recrutement.

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

from historique import Historique

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
    """Tout ce que publient les classements, lu en une connexion. Chaque partie est lue à part : un souci sur l'une
    (table absente, colonne renommée) n'empêche pas de publier les autres. Aucune jointure de texte entre tables :
    les collations de la base diffèrent (erreur 1267), les filtres se font ici."""
    import pymysql
    connexion = pymysql.connect(**lire_adresse(adresse), connect_timeout=10, read_timeout=20, charset="utf8mb4")
    d = {}
    try:
        with connexion.cursor() as c:
            # Lecture seule, par précaution : cette session ne peut rien modifier
            try:
                c.execute("SET SESSION TRANSACTION READ ONLY")
            except pymysql.MySQLError:
                pass

            def partie(nom, sql, defaut, transformer=list):
                try:
                    c.execute(sql)
                    return transformer(c.fetchall())
                except pymysql.MySQLError as err:
                    code = err.args[0] if err.args and isinstance(err.args[0], int) else ""
                    signaler(f"{nom} illisible ({type(err).__name__} {code}).".replace(" )", ")"), "warning")
                    return defaut

            # Les fortunes (poche + banque), sans les membres privés de grains (blacklistGrains). Celle-ci est indispensable.
            c.execute("SELECT id, COALESCE(grains, 0) + COALESCE(banque, 0), COALESCE(banque, 0) FROM users WHERE blacklistGrains IS NULL")
            lignes = c.fetchall()
            d["fortunes"] = {str(i): int(t) for i, t, _ in lignes if int(t) > 0}
            d["banque"] = sum(int(b) for _, _, b in lignes)
            d["exclus"] = partie("Membres exclus", "SELECT id FROM users WHERE blacklistGrains IS NOT NULL", set(), lambda l: {str(i) for (i,) in l})
            # Le salon #infini : nombres postés par membre, et le total de la suite
            d["infini"] = partie("Classement #infini", "SELECT id, infiniStats FROM users WHERE infiniStats > 0", {}, lambda l: {str(i): int(n) for i, n in l})
            d["infini_total"] = partie("Compteur #infini", "SELECT COALESCE(SUM(infiniStats), 0) FROM users", None, lambda l: int(l[0][0]))
            # Le temps passé en vocal (minutes), et la série de /journalier
            d["vocal"] = partie("Temps en vocal", "SELECT id, minutes FROM gains_vocal_minutes WHERE minutes > 0", {}, lambda l: {str(i): int(m) for i, m in l})
            d["serie"] = partie("Séries", "SELECT id, streak FROM users WHERE streak > 0 AND blacklistGrains IS NULL", {}, lambda l: {str(i): int(n) for i, n in l})
            # Les postes ouverts au recrutement
            d["recrutement"] = partie("Recrutement", "SELECT poste, vague FROM recrutement WHERE ouvert = 1", [],
                                      lambda l: [{"poste": str(p), "vague": int(v) if v is not None else None} for p, v in l if str(p or "").strip()])
            return d
    finally:
        connexion.close()


def top(valeurs, exclus=(), taille=TAILLE):
    """Les `taille` meilleurs [(identifiant, valeur)], à égalité dans l'ordre des identifiants."""
    return sorted(((i, v) for i, v in valeurs.items() if v > 0 and i not in exclus), key=lambda x: (-x[1], x[0]))[:taille]


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
        d = lire_base(adresse)
    except Exception as err:  # base injoignable : le site garde le classement précédent
        # Seulement le type et le code d'erreur : jamais le message, qui peut contenir l'hôte ou l'utilisateur
        code = err.args[0] if getattr(err, "args", None) and isinstance(err.args[0], int) else ""
        signaler(f"Base de données injoignable ({type(err).__name__} {code}) : classement non mis à jour.".replace(" )", ")"), "warning")
        return 2
    historique = Historique(os.environ.get("HISTORIQUE"))
    profils = {}  # un membre présent dans plusieurs classements n'est demandé qu'une fois à Discord

    def membre(identifiant):
        if identifiant not in profils:
            try:
                profils[identifiant] = profil(identifiant, jeton)
            except Exception as err:
                signaler(f"Profil Discord illisible ({type(err).__name__}).", "warning")
                profils[identifiant] = {"nom": "Membre", "avatar": None}
            time.sleep(.4)  # Discord limite les appels rapprochés
        return profils[identifiant]

    def classer(metrique, valeurs, cle, exclus=()):
        """Le top 10 d'un classement, avec la progression depuis hier ; la photo du jour est prise au passage."""
        meilleurs = top(valeurs, exclus)
        evolutions = historique.evolutions(metrique, meilleurs)
        historique.photo(metrique, {i: v for i, v in valeurs.items() if i not in exclus})
        liste = []
        for rang, ((identifiant, valeur), evo) in enumerate(zip(meilleurs, evolutions), 1):
            ligne = {"rang": rang, **membre(identifiant), cle: valeur}
            if evo is not None:
                ligne["evolution"] = evo
            liste.append(ligne)
        return liste

    fortunes = d["fortunes"]
    # Le champion de la semaine : la plus forte hausse de fortune sur 7 jours (avant la photo du jour)
    champion = historique.plus_forte_hausse("grains", fortunes, 7)
    classement = classer("grains", fortunes, "grains")
    classement_infini = classer("infini", d["infini"], "nombres")
    classement_vocal = classer("vocal", d["vocal"], "minutes", d["exclus"])
    classement_serie = classer("serie", d["serie"], "jours")
    # L'économie du café : les grains en circulation, la part en banque, et l'évolution sur 7 jours
    total = sum(fortunes.values())
    ecart = historique.ecart("total", total, 7)
    historique.photo_valeur("total", total)
    economie = {"total": total, "banque": d["banque"], "detenteurs": len(fortunes)}
    if ecart:
        economie["evolution"], economie["jours"] = ecart

    sortie = pathlib.Path(sys.argv[1])
    sortie.parent.mkdir(parents=True, exist_ok=True)
    maj = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    donnees = {"maj": maj, "classement": classement, "economie": economie}
    if d["infini_total"] is not None:
        donnees["infini"] = d["infini_total"]
    for cle, liste in (("infini_classement", classement_infini), ("vocal_classement", classement_vocal), ("serie_classement", classement_serie)):
        if liste:
            donnees[cle] = liste
    if champion:
        identifiant, hausse, jours = champion
        donnees["champion_semaine"] = {**membre(identifiant), "gain": hausse, "jours": jours}
    donnees["recrutement"] = d["recrutement"]
    sortie.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    historique.enregistrer()
    signaler(f"Classements publiés : {len(classement)} (grains), {len(classement_infini)} (#infini), {len(classement_vocal)} (vocal), "
             f"{len(classement_serie)} (série) ; champion de la semaine : {'oui' if champion else 'pas encore'} ; postes ouverts : {len(d['recrutement'])}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
