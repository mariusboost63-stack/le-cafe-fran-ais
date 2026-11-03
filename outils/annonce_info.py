#!/usr/bin/env python3
"""Annonce la petite info du jour sur le serveur Discord, sous forme d'embed, dès qu'elle est publiée sur le site (midi).

Lancé par GitHub Actions (.github/workflows/annonce-info.yml) peu après midi, heure de Paris. L'info du jour est lue
dans infos.json ; elle n'est annoncée qu'une fois : la date de la dernière annonce est gardée dans un petit fichier
(branche « annonces » du dépôt).

Variable d'environnement (secret du dépôt) :
  DISCORD_WEBHOOK_INFO   adresse du webhook du salon où poster (Paramètres du salon → Intégrations → Webhooks)

Usage : python3 outils/annonce_info.py <infos.json> <fichier de la dernière annonce>
Codes de sortie : 0 info annoncée, 2 rien à annoncer (déjà fait, pas encore midi, ou secret absent), 1 erreur.
"""
import datetime
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request
import zoneinfo

PARIS = zoneinfo.ZoneInfo("Europe/Paris")
SITE = "https://cafe-fr.com"
COULEUR = 0x6B95FF  # le bleu du site


def signaler(texte, niveau="notice"):
    print(f"::{niveau}::{texte}" if os.environ.get("GITHUB_ACTIONS") else texte)


def fr(texte):
    # Comme sur le site : espaces insécables avant ? ! : ; %, dans les guillemets et dans les nombres (161 000)
    t = re.sub(r" ([?!:;»%])", "\u00a0\\1", str(texte or ""))
    t = t.replace("« ", "«\u00a0")
    return re.sub(r"(\d) (?=\d{3}\b)", "\\1\u00a0", t)


def info_du_jour(chemin, maintenant):
    """L'info datée d'aujourd'hui (heure de Paris) si son heure de publication est passée, sinon None."""
    aujourdhui = maintenant.astimezone(PARIS).date().isoformat()
    for info in json.loads(pathlib.Path(chemin).read_text(encoding="utf-8")).get("infos", []):
        if info.get("date") != aujourdhui or not info.get("titre"):
            continue
        publication = datetime.datetime.fromisoformat(info["publication"])
        return info if publication <= maintenant else None
    return None


def embed(info):
    source = info.get("source") or {}
    url = source.get("url", "")
    champs = []
    if info.get("theme"):
        champs.append({"name": "Thème", "value": info["theme"], "inline": True})
    if url.startswith("https://"):
        champs.append({"name": "Source", "value": f"[{source.get('nom') or 'Lire l’article'}]({url})", "inline": True})
    jour = datetime.date.fromisoformat(info["date"])
    jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    return {
        "author": {"name": f"☕ La petite info du jour · {jours[jour.weekday()]} {jour.day} {mois[jour.month - 1]}"},
        "title": fr(info["titre"])[:256],
        "url": f"{SITE}/#info",
        "description": fr(info.get("texte", ""))[:3800] + f"\n\n[Toutes les infos sur cafe-fr.com]({SITE}/infos/)",
        "color": COULEUR,
        "fields": champs,
        "footer": {"text": "La Gazette du Café · une info chaque jour à midi"},
        "timestamp": datetime.datetime.fromisoformat(info["publication"]).astimezone(datetime.timezone.utc).isoformat(),
    }


def envoyer(webhook, contenu):
    requete = urllib.request.Request(
        webhook + ("&" if "?" in webhook else "?") + "wait=true",
        data=json.dumps(contenu).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "cafe-fr.com (annonce de l'info du jour)"},
        method="POST")
    with urllib.request.urlopen(requete, timeout=20) as reponse:
        return reponse.status


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    infos, etat = sys.argv[1], pathlib.Path(sys.argv[2])
    webhook = os.environ.get("DISCORD_WEBHOOK_INFO", "").strip()
    if not webhook:
        signaler("Secret DISCORD_WEBHOOK_INFO à ajouter dans les réglages du dépôt : rien n'est annoncé.", "warning")
        return 2
    if not re.match(r"^https://(discord|discordapp)\.com/api/webhooks/\d+/[\w-]+", webhook):
        signaler("DISCORD_WEBHOOK_INFO n'est pas une adresse de webhook Discord : rien n'est annoncé.", "warning")
        return 2
    maintenant = datetime.datetime.now(datetime.timezone.utc)
    info = info_du_jour(infos, maintenant)
    if not info:
        signaler("Pas d'info du jour publiée pour l'instant : rien à annoncer.")
        return 2
    if etat.exists() and etat.read_text(encoding="utf-8").strip() == info["date"]:
        signaler(f"L'info du {info['date']} a déjà été annoncée.")
        return 2
    contenu = {
        "username": "La Gazette du Café",
        "embeds": [embed(info)],
        "allowed_mentions": {"parse": []},  # jamais de mention @everyone ni de rôle par erreur
    }
    try:
        envoyer(webhook, contenu)
    except urllib.error.HTTPError as err:
        # Seulement le code : l'adresse du webhook est secrète et ne doit pas apparaître dans les journaux
        signaler(f"Discord a refusé l'annonce (HTTP {err.code}).", "error")
        return 1
    except urllib.error.URLError as err:
        signaler(f"Discord injoignable ({type(err.reason).__name__}).", "error")
        return 1
    etat.parent.mkdir(parents=True, exist_ok=True)
    etat.write_text(info["date"] + "\n", encoding="utf-8")
    signaler(f"Info du {info['date']} annoncée sur Discord : {info['titre']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
