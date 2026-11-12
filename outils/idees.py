#!/usr/bin/env python3
"""La boîte à idées du café : les suggestions des membres (commande /suggestion du bot), avec leur statut et leurs
votes, lues dans la base du bot pour la page Équipe. Seuls le texte, le statut, les votes et la date sont publiés :
jamais l'auteur, ni les images jointes. Les mentions, les liens et la mise en forme Discord sont retirés du texte.
Les membres privés de suggestions (users.blacklistSuggestions) ne sont pas publiés.

Lancé toutes les heures par GitHub Actions avec le classement (.github/workflows/classement.yml). Le résultat,
idees.json, est publié sur la branche « data » du dépôt, et le site le lit. Lecture seule, mêmes secrets que le
classement (CAFE_DB_URL et DISCORD_TOKEN).

Usage : python3 outils/idees.py <fichier de sortie>
Nécessite PyMySQL (pip install pymysql).
"""
import collections
import datetime
import json
import os
import pathlib
import re
import sys

from classement import lire_adresse, signaler

# Le statut d'une suggestion dans le bot (colonne suggestions.statut). 1 : publiée et soumise au vote des membres.
# 2 et 4 : décidées par l'équipe (lequel est « acceptée », lequel « refusée » reste à confirmer). Un statut absent de la
# liste n'est pas publié. Le résumé de l'exécution donne la répartition (« Statuts des suggestions »).
STATUTS = {1: "vote"}
# Les votes (colonne votessuggestions.vote) : 1 pour, 2 contre
POUR, CONTRE = 1, 2
# Les idées à ne pas publier sur le site (leur numéro, colonne suggestions.id), décidées par l'équipe
MASQUEES = set()
LONGUEUR = 600  # caractères au plus par idée
DISCORD_EPOQUE = 1420070400000


def date_message(identifiant):
    """La date d'un message Discord, tirée de son identifiant."""
    try:
        ms = (int(identifiant) >> 22) + DISCORD_EPOQUE
    except (TypeError, ValueError):
        return None
    if ms <= DISCORD_EPOQUE:
        return None
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).replace(microsecond=0).isoformat()


def nettoyer(texte):
    """Le texte d'une idée, sans mentions, liens ni mise en forme Discord."""
    t = str(texte or "")
    t = re.sub(r"<a?:(\w+):\d+>", r":\1:", t)                  # emojis du serveur
    t = re.sub(r"<@[!&]?\d+>", "@membre", t)                  # mentions de membres et de rôles
    t = re.sub(r"<#\d+>", "#salon", t)                        # mentions de salons
    t = re.sub(r"<t:\d+(:\w)?>", "", t)                       # dates Discord
    t = re.sub(r"https?://\S+", "", t)                        # liens
    t = re.sub(r"@(everyone|here)\b", r"\1", t)
    t = re.sub(r"(\*\*|__|~~|\|\||`+)", "", t)               # gras, souligné, barré, spoiler, code
    t = re.sub(r"^\s*>+\s?", "", t, flags=re.M)               # citations
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > LONGUEUR:
        t = t[:LONGUEUR - 1].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"
    return t


def lire_base(adresse):
    import pymysql
    connexion = pymysql.connect(**lire_adresse(adresse), connect_timeout=10, read_timeout=30, charset="utf8mb4")
    try:
        with connexion.cursor() as c:
            try:
                c.execute("SET SESSION TRANSACTION READ ONLY")
            except pymysql.MySQLError:
                pass
            # Aucune jointure de texte entre tables (collations différentes) : tout est croisé ici
            c.execute("SELECT id FROM users WHERE blacklistSuggestions IS NOT NULL AND blacklistSuggestions <> 0")
            exclus = {str(i) for (i,) in c.fetchall()}
            c.execute("SELECT id, user, suggestion, messageId, statut FROM suggestions")
            suggestions = c.fetchall()
            c.execute("SELECT idSuggestion, vote, COUNT(*) FROM votessuggestions GROUP BY idSuggestion, vote")
            votes = c.fetchall()
            return exclus, suggestions, votes
    finally:
        connexion.close()


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    adresse = os.environ.get("CAFE_DB_URL", "")
    if not adresse:
        signaler("Secret CAFE_DB_URL à ajouter dans les réglages du dépôt : boîte à idées non publiée.", "warning")
        return 2
    try:
        exclus, suggestions, votes = lire_base(adresse)
    except Exception as err:
        code = err.args[0] if getattr(err, "args", None) and isinstance(err.args[0], int) else ""
        signaler(f"Boîte à idées illisible ({type(err).__name__} {code}) : rien n'est publié.".replace(" )", ")"), "warning")
        return 2

    # Les votes, pour et contre, par suggestion
    pour, contre, valeurs = collections.Counter(), collections.Counter(), collections.Counter()
    for ident, vote, n in votes:
        valeurs[int(vote or 0)] += int(n)
        if int(vote or 0) == POUR:
            pour[str(ident)] += int(n)
        elif int(vote or 0) == CONTRE:
            contre[str(ident)] += int(n)

    # Le relevé des statuts et des votes, pour vérifier STATUTS (seulement des comptes, jamais de texte)
    par_statut = collections.defaultdict(list)
    for ident, _, _, _, statut in suggestions:
        par_statut[statut].append(int(ident))
    resume = "; ".join(
        f"{s} : {len(ids)} (n° {min(ids)} à {max(ids)}, {sum(pour[str(i)] for i in ids) / len(ids):.1f} pour et "
        f"{sum(contre[str(i)] for i in ids) / len(ids):.1f} contre en moyenne)" for s, ids in sorted(par_statut.items(), key=lambda x: str(x[0])))
    signaler(f"Statuts des suggestions : {resume}. Valeurs des votes : {dict(sorted(valeurs.items()))}.")

    idees = []
    for ident, auteur, texte, message, statut in suggestions:
        if str(auteur) in exclus or statut not in STATUTS or int(ident) in MASQUEES:
            continue
        propre = nettoyer(texte)
        if len(propre) < 8:
            continue
        idees.append({"id": int(ident), "texte": propre, "statut": STATUTS[statut], "pour": pour[str(ident)],
                      "contre": contre[str(ident)], "date": date_message(message)})
    idees.sort(key=lambda x: -x["id"])
    totaux = dict(collections.Counter(x["statut"] for x in idees))
    sortie = pathlib.Path(sys.argv[1])
    sortie.parent.mkdir(parents=True, exist_ok=True)
    donnees = {"maj": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(), "totaux": totaux, "idees": idees}
    sortie.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    signaler(f"Boîte à idées publiée : {len(idees)} idées ({totaux}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
