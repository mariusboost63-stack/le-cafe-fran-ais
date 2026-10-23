#!/usr/bin/env python3
"""Prochains événements du serveur : les événements programmés sur Discord (onglet « Événements »), publiés sans rien de sensible.

Lancé toutes les 30 minutes par GitHub Actions (.github/workflows/evenements.yml). Le résultat, evenements.json,
est publié sur la branche « evenements » du dépôt, et le site le lit. Sans événement à venir, la liste est vide
et la section reste cachée sur le site.

Variables d'environnement (secrets du dépôt) :
  DISCORD_TOKEN_EVENEMENTS  jeton d'un bot présent sur le serveur (facultatif : sinon DISCORD_TOKEN est utilisé)
  DISCORD_TOKEN             le bot doit être membre du serveur pour voir ses événements ; aucune permission en plus

Usage : python3 outils/evenements.py <fichier de sortie>
"""
import datetime
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

SERVEUR = "829698572927762432"
API = "https://discord.com/api/v10"
TAILLE = 6
LIEUX = {1: "Conférence", 2: "Salon vocal", 3: "Ailleurs"}


def signaler(texte, niveau="notice"):
    # Dans GitHub Actions, le message s'affiche aussi dans le résumé de l'exécution
    print(f"::{niveau}::{texte}" if os.environ.get("GITHUB_ACTIONS") else texte)


def appeler(chemin, jeton):
    requete = urllib.request.Request(f"{API}{chemin}", headers={
        "Authorization": f"Bot {jeton}", "User-Agent": "cafe-fr.com (evenements)", "Accept": "application/json"})
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


def nettoyer(texte, salons, roles):
    """La description en texte simple : mentions lisibles, sans emoji personnalisé ni mise en forme Discord."""
    t = str(texte or "")
    t = re.sub(r"<#(\d+)>", lambda m: f"#{salons[m[1]]}" if m[1] in salons else "#salon", t)
    t = re.sub(r"<@&(\d+)>", lambda m: f"@{roles[m[1]]}" if m[1] in roles else "@rôle", t)
    t = re.sub(r"<@!?\d+>", "@membre", t)
    t = re.sub(r"<a?:\w+:\d+>", "", t)
    t = re.sub(r"<t:(\d+)(?::\w)?>", lambda m: datetime.datetime.fromtimestamp(int(m[1]), datetime.timezone.utc).strftime("%d/%m"), t)
    t = re.sub(r"(\*\*|__|~~|\|\||`+|^#+ |^> )", "", t, flags=re.M)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    return t if len(t) <= 280 else t[:279].rsplit(" ", 1)[0].rstrip(" ,;:.") + "…"


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    jeton = os.environ.get("DISCORD_TOKEN_EVENEMENTS") or os.environ.get("DISCORD_TOKEN", "")
    if not jeton:
        signaler("Secret DISCORD_TOKEN (ou DISCORD_TOKEN_EVENEMENTS) à ajouter dans les réglages du dépôt : rien n'est publié.", "warning")
        return 2
    try:
        # Un bot absent du serveur peut recevoir une liste vide : on vérifie d'abord qu'il en est membre
        if SERVEUR not in {g.get("id") for g in appeler("/users/@me/guilds", jeton)}:
            signaler("Le bot du secret n'est pas membre du serveur : il ne voit pas ses événements, rien n'est publié."
                     " Invite-le sans permission (voir README, « Les prochains événements »), ou mets le jeton d'un bot"
                     " présent sur le serveur dans DISCORD_TOKEN_EVENEMENTS.", "warning")
            return 2
        liste = appeler(f"/guilds/{SERVEUR}/scheduled-events?with_user_count=true", jeton)
    except urllib.error.HTTPError as err:
        if err.code in (401, 403, 404):
            signaler(f"Discord refuse l'accès aux événements ({err.code}) : le bot du secret doit être membre du serveur."
                     " Invite-le, ou mets le jeton d'un bot présent sur le serveur dans DISCORD_TOKEN_EVENEMENTS.", "warning")
        else:
            signaler(f"Discord injoignable ({err.code}) : événements non mis à jour.", "warning")
        return 2
    except Exception as err:  # réseau : le site garde la liste précédente
        signaler(f"Discord injoignable ({type(err).__name__}) : événements non mis à jour.", "warning")
        return 2

    # Les noms des salons et des rôles, pour le lieu et les mentions de la description (facultatif)
    salons, roles = {}, {}
    try:
        salons = {c["id"]: c.get("name", "") for c in appeler(f"/guilds/{SERVEUR}/channels", jeton)}
        roles = {r["id"]: r.get("name", "") for r in appeler(f"/guilds/{SERVEUR}/roles", jeton)}
    except Exception as err:
        signaler(f"Noms des salons illisibles ({type(err).__name__} {getattr(err, 'code', '')}) : lieux affichés sans nom.".replace(" )", ")"), "warning")

    evenements = []
    # 1 : programmé, 2 : en cours. Les événements terminés ou annulés ne sont pas publiés
    for e in sorted((e for e in liste if e.get("status") in (1, 2)), key=lambda e: e.get("scheduled_start_time", "")):
        type_lieu = e.get("entity_type")
        if type_lieu == 3:
            lieu = str((e.get("entity_metadata") or {}).get("location") or LIEUX[3])[:80]
        else:
            nom = salons.get(str(e.get("channel_id")), "")
            lieu = f"{LIEUX.get(type_lieu, 'Salon vocal')} · {nom}" if nom else LIEUX.get(type_lieu, "Salon vocal")
        image = e.get("image")
        evenements.append({
            "id": e["id"],
            "nom": str(e.get("name") or "Événement")[:100],
            "description": nettoyer(e.get("description"), salons, roles),
            "debut": e.get("scheduled_start_time"),
            "fin": e.get("scheduled_end_time"),
            "enCours": e.get("status") == 2,
            "lieu": lieu,
            "type": {1: "scene", 2: "vocal", 3: "ailleurs"}.get(type_lieu, "vocal"),
            "interesses": int(e.get("user_count") or 0),
            "recurrent": bool(e.get("recurrence_rule")),
            "image": f"https://cdn.discordapp.com/guild-events/{e['id']}/{image}.png?size=640" if image else None,
            "lien": f"https://discord.com/events/{SERVEUR}/{e['id']}",
        })
        if len(evenements) == TAILLE:
            break

    sortie = pathlib.Path(sys.argv[1])
    sortie.parent.mkdir(parents=True, exist_ok=True)
    maj = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    sortie.write_text(json.dumps({"maj": maj, "evenements": evenements}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    signaler(f"Événements publiés : {len(evenements)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
