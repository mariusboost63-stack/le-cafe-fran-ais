"""Prépare les pages du site pour la publication.

Le site est un seul fichier, index.html, qui affiche la page demandée selon l'adresse (cafe-fr.com/classement/…).
Pour que chaque adresse existe chez Cloudflare Pages, ce script copie index.html dans le dossier de chaque page
(classement/index.html, grains/index.html…) en y mettant le titre, la description et l'adresse de la page : c'est ce
que voient Discord et les moteurs de recherche quand on partage un lien. La liste des pages est dans index.html,
dans le bloc <script type="application/json" id="pages-du-site">.

Utilisation : python3 outils/pages.py <dossier du site>
"""
import html
import json
import pathlib
import re
import sys

SITE = "https://cafe-fr.com"


def pages_du_site(source):
    bloc = re.search(r'<script type="application/json" id="pages-du-site">(.*?)</script>', source, re.S)
    if not bloc:
        raise SystemExit("Liste des pages introuvable dans index.html")
    return json.loads(bloc.group(1))


def remplacer(source, motif, valeur):
    nouveau, n = re.subn(motif, lambda m: m.group(1) + valeur + m.group(2), source, count=1)
    if n != 1:
        raise SystemExit(f"Balise introuvable : {motif}")
    return nouveau


def page(source, p, dossier):
    titre, description, url = html.escape(p["titre"], quote=True), html.escape(p["description"], quote=True), SITE + p["chemin"]
    source = remplacer(source, r"(<title>)[^<]*(</title>)", titre)
    source = remplacer(source, r'(<meta name="description" content=")[^"]*(")', description)
    source = remplacer(source, r'(<meta property="og:title" content=")[^"]*(")', html.escape(p["nom"], quote=True) + " · Le Café Français")
    source = remplacer(source, r'(<meta property="og:description" content=")[^"]*(")', description)
    source = remplacer(source, r'(<meta property="og:url" content=")[^"]*(")', url)
    source = remplacer(source, r'(<link rel="canonical" href=")[^"]*(")', url)
    # L'image d'aperçu propre à la page (apercus/<page>.jpg, dessinée par outils/apercus.js), si elle existe
    if (dossier / "apercus" / f"{p['id']}.jpg").exists():
        source = remplacer(source, r'(<meta property="og:image" content=")[^"]*(")', f"{SITE}/apercus/{p['id']}.jpg")
        source = remplacer(source, r'(<meta property="og:image:alt" content=")[^"]*(")',
                           html.escape(f"{p['nom']}, au Café Français : {p['resume']}", quote=True))
    return source


def main():
    dossier = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    source = (dossier / "index.html").read_text(encoding="utf-8")
    for p in pages_du_site(source):
        if p["chemin"] == "/":
            continue
        cible = dossier / p["chemin"].strip("/") / "index.html"
        if cible.exists():
            raise SystemExit(f"{cible} existe déjà : une page porte le nom d'un dossier du site")
        cible.parent.mkdir(parents=True, exist_ok=True)
        cible.write_text(page(source, p, dossier), encoding="utf-8")
        print("page", p["chemin"])


if __name__ == "__main__":
    main()
