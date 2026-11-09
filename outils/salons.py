#!/usr/bin/env python3
"""Les salons du serveur, lus sur Discord pour que la visite des salles du site reste à jour toute seule : nom, emoji,
type (textuel, annonces, forum, règles), sujet du salon, et cadenas pour les salons réservés à un rôle.

Lancé toutes les 2 heures avec les événements (.github/workflows/evenements.yml). Le résultat, salons.json, est
publié sur la branche « evenements » du dépôt, et le site le lit. Seules les trois catégories de la visite sont
relevées (Café Français, Centre de Convivialité, Divertissements), et seulement les salons que voit un membre :
les salons du staff n'apparaissent jamais.

Variables d'environnement (secrets du dépôt) :
  DISCORD_TOKEN_EVENEMENTS  jeton d'un bot présent sur le serveur (facultatif : sinon DISCORD_TOKEN est utilisé)
  DISCORD_TOKEN             le bot doit être membre du serveur ; aucune permission en plus
  ROLE_MEMBRE               facultatif : identifiant du rôle donné à tous les membres, si @everyone ne voit rien

Usage : python3 outils/salons.py <fichier de sortie>
"""
import datetime
import json
import os
import pathlib
import re
import sys
import unicodedata

from evenements import SERVEUR, appeler, nettoyer, signaler

# Les catégories de la visite, dans l'ordre du site
CATEGORIES = {"cafefrancais": "Café Français", "centredeconvivialite": "Centre de Convivialité", "divertissements": "Divertissements"}
# Salons réservés à un rôle que le site montre quand même, avec un cadenas (accessibles à tous les membres qui ont le rôle)
PRIVES_AFFICHES = {"couleurs", "discussion-vip"}
TYPES = {0: "texte", 5: "annonce", 15: "forum", 16: "forum"}
VOIR = 1 << 10  # permission « Voir le salon »
SEPARATEURS = "│｜|・┃丨︱•·:"


def cle(texte):
    t = unicodedata.normalize("NFD", str(texte or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", t)


def couper(nom):
    """« 📢│news-casino » → (« 📢 », « news-casino »). Sans emoji : (« », nom)."""
    nom = str(nom or "").strip()
    for i, c in enumerate(nom):
        if c in SEPARATEURS:
            gauche, droite = nom[:i].strip(), nom[i + 1:].strip()
            if gauche and droite and not any(x.isalnum() for x in gauche):
                return gauche, droite
            break
    m = re.match(r"^([^\w\s]+)[\s\-_]*(.+)$", nom)
    if m and not any(x.isalnum() for x in m[1]):
        return m[1].strip().rstrip("-_").strip(), m[2].strip()
    return "", nom


def visible(salon, roles_membre, permissions_base):
    """Ce qu'un simple membre voit : les droits de @everyone (et du rôle des membres), puis les exceptions du salon."""
    perms = permissions_base
    deny = allow = 0
    for o in salon.get("permission_overwrites") or []:
        if o.get("type") == 0 and o.get("id") in roles_membre:
            deny |= int(o.get("deny", 0)); allow |= int(o.get("allow", 0))
    perms = (perms & ~deny) | allow
    return bool(perms & VOIR)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    jeton = os.environ.get("DISCORD_TOKEN_EVENEMENTS") or os.environ.get("DISCORD_TOKEN", "")
    if not jeton:
        signaler("Secret DISCORD_TOKEN à ajouter : salons non relevés.", "warning")
        return 2
    try:
        if SERVEUR not in {g.get("id") for g in appeler("/users/@me/guilds", jeton)}:
            signaler("Le bot du secret n'est pas membre du serveur : les salons ne sont pas relevés (voir README).", "warning")
            return 2
        serveur = appeler(f"/guilds/{SERVEUR}", jeton)
        salons = appeler(f"/guilds/{SERVEUR}/channels", jeton)
        roles = appeler(f"/guilds/{SERVEUR}/roles", jeton)
    except Exception as err:
        signaler(f"Discord injoignable ({type(err).__name__}) : salons non relevés.", "warning")
        return 2
    roles_membre = {SERVEUR} | ({os.environ["ROLE_MEMBRE"].strip()} if os.environ.get("ROLE_MEMBRE", "").strip() else set())
    base = 0
    for r in roles:
        if r.get("id") in roles_membre:
            base |= int(r.get("permissions", 0))
    noms_salons = {c["id"]: couper(c.get("name"))[1] for c in salons}
    noms_roles = {r["id"]: r.get("name", "") for r in roles}
    regles = serveur.get("rules_channel_id")
    categories = {c["id"]: c for c in salons if c.get("type") == 4}
    sortie = []
    for code, titre in CATEGORIES.items():
        categorie = next((c for c in categories.values() if cle(c.get("name")).endswith(code) or code in cle(c.get("name"))), None)
        if not categorie:
            signaler(f"Catégorie « {titre} » introuvable sur le serveur.", "warning")
            continue
        liste = []
        for s in sorted((s for s in salons if s.get("parent_id") == categorie["id"] and s.get("type") in TYPES),
                        key=lambda s: (s.get("position", 0), s.get("id"))):
            emoji, nom = couper(s.get("name"))
            ouvert = visible(s, roles_membre, base)
            if not ouvert and nom not in PRIVES_AFFICHES:
                continue  # salon du staff, ou réservé : jamais publié
            sujet = nettoyer(s.get("topic"), noms_salons, noms_roles).replace("\n", " ")
            if len(sujet) > 120:
                sujet = sujet[:119].rsplit(" ", 1)[0].rstrip(" ,;:.") + "…"
            liste.append({"nom": nom, "emoji": emoji, "type": "regles" if s["id"] == regles else TYPES[s["type"]],
                          "prive": not ouvert, "sujet": sujet})
        sortie.append({"nom": titre, "cle": code, "salons": liste})
    if not any(c["salons"] for c in sortie):
        signaler("Aucun salon visible par un membre : rien n'est publié (voir ROLE_MEMBRE dans le README).", "warning")
        return 2
    fichier = pathlib.Path(sys.argv[1])
    fichier.parent.mkdir(parents=True, exist_ok=True)
    maj = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    fichier.write_text(json.dumps({"maj": maj, "categories": sortie}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    signaler("Salons publiés : " + ", ".join(f"{c['nom']} ({len(c['salons'])})" for c in sortie) + ".")
    return 0


if __name__ == "__main__":
    sys.exit(main())
