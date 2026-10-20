#!/usr/bin/env node
/* Pages de partage des scores du mini-jeu « Attrape les grains » : score/<n>/index.html et score/<n>/partage.jpg.
   Quand un joueur partage son score sur Discord, le lien cafe-fr.com/score/<n>/ affiche l'image de son score ;
   un visiteur qui clique arrive sur le jeu.

   Usage : node outils/partage.js            toutes les pages, de 1 à SCORE_MAX
           node outils/partage.js 57 123     seulement ces scores
   À relancer si le style des images ou les titres changent. Nécessite Playwright (voir outils/navigateur.js). */
const fs = require('fs');
const path = require('path');
const navigateur = require('./navigateur');

const RACINE = path.join(__dirname, '..');
const PAGE = path.join(RACINE, 'index.html');
const SITE = 'https://cafe-fr.com';
const SCORE_MAX = 200; // le jeu ne dépasse pas 180 environ ; les scores plus hauts utilisent la page 200

// Titre gagné selon le score (affiché sur l'image et dans la description du lien)
const TITRES = [[160, 'Légende du café'], [140, 'Maître torréfacteur'], [110, 'Chef de comptoir'], [80, 'Barista confirmé'],
  [50, 'Serveur du comptoir'], [25, 'Apprenti barista'], [1, 'Premier café']];
const titre = (n) => TITRES.find(([min]) => n >= min)[1];
const grains = (n) => `${n} grain${n > 1 ? 's' : ''} de café`;
const echapper = (s) => s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');

function pageHtml(n) {
  const url = `${SITE}/score/${n}/`;
  const titreLien = `J'ai attrapé ${grains(n)}\u00a0!`;
  const description = `${titre(n)} au mini-jeu du Café Français. 45 secondes pour remplir ta tasse\u00a0: à toi de battre ce score\u00a0!`;
  return `<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${echapper(titreLien)} · Le Café Français</title>
<meta name="description" content="${echapper(description)}">
<meta name="robots" content="noindex">
<meta name="theme-color" content="#c99263">
<link rel="canonical" href="${url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Le Café Français">
<meta property="og:locale" content="fr_FR">
<meta property="og:title" content="${echapper(titreLien)}">
<meta property="og:description" content="${echapper(description)}">
<meta property="og:url" content="${url}">
<meta property="og:image" content="${url}partage.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="${echapper(`${grains(n)} attrapés au mini-jeu du Café Français, titre\u00a0: ${titre(n)}.`)}">
<meta name="twitter:card" content="summary_large_image">
<style>body { margin: 0; min-height: 100vh; display: grid; place-items: center; padding: 24px; background: #131a28; color: #f2f1f9; font: 17px/1.5 system-ui, sans-serif; text-align: center; } a { color: #c99263; }</style>
<script>location.replace('/#pause');</script>
</head>
<body>
<p><a href="/#pause">${echapper(grains(n))} au mini-jeu du Café Français. À toi de jouer&nbsp;!</a></p>
</body>
</html>
`;
}

// Prépare, dans la page du site, la scène de l'image (1200 × 630) : logo, tasse, grains et lettres du fond
async function preparerScene(page) {
  await page.evaluate(async () => {
    const lettre = (id, cx, cy, h, r) => {
      const el = document.getElementById(id);
      const b = el.getBBox();
      const s = h / b.height;
      return `<path d="${el.getAttribute('d')}" transform="translate(${cx} ${cy}) rotate(${r}) scale(${s}) translate(${-(b.x + b.width / 2)} ${-(b.y + b.height / 2)})"/>`;
    };
    const d = (id) => document.getElementById(id).getAttribute('d');
    // Un grain comme dans le jeu : ellipse et sillon ; « dore » pour les grains à 5 points
    const grain = (x, y, a, t, dore) => `<g transform="translate(${x} ${y}) rotate(${a}) scale(${t})"${dore ? ' filter="url(#ap-lueur)"' : ''}>
      <ellipse rx="6" ry="8.5" fill="${dore ? '#f0b232' : '#8a5a34'}"/><path d="M0 -6.5C-2.6 -2 2.6 2 0 6.5" fill="none" stroke="#3f2414" stroke-width="1.6" stroke-linecap="round"/></g>`;
    // Le nom seul (sans la tasse) pour l'en-tête
    const nom = document.getElementById('logo').cloneNode(true);
    nom.removeAttribute('id');
    nom.querySelectorAll('.tasse, .vapeur, [clip-path]').forEach((n) => n.remove());
    nom.setAttribute('viewBox', '272 46 790 244');
    const scene = document.createElement('div');
    scene.id = 'partage-image';
    scene.innerHTML = `
      <svg class="pi-fond" viewBox="0 0 1200 630">${[
        lettre('p-F', 1080, 120, 420, 14), lettre('p-a2', 120, 560, 260, -16), lettre('p-s', 560, 40, 180, 10),
      ].join('')}</svg>
      <div class="pi-halo"></div>
      <div class="pi-nom">${nom.outerHTML}</div>
      <div class="pi-score">
        <p class="pi-avant">J'ai attrapé</p>
        <p class="pi-nombre" id="pi-nombre"></p>
        <p class="pi-unite" id="pi-unite"></p>
        <p class="pi-titre"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3.8 2.5 5.2 5.6.8-4.1 3.9 1 5.6-5-2.7-5 2.7 1-5.6-4.1-3.9 5.6-.8Z"/></svg><span id="pi-titre"></span></p>
      </div>
      <svg class="pi-tasse" viewBox="0 0 250 245">
        <defs>
          <filter id="ap-lueur" x="-1" y="-1" width="3" height="3"><feGaussianBlur stdDeviation="3.5" result="flou"/><feMerge><feMergeNode in="flou"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
          <clipPath id="pi-dedans"><path d="${document.querySelector('#clip-interieur path').getAttribute('d')}"/></clipPath>
        </defs>
        <g clip-path="url(#pi-dedans)"><rect id="pi-cafe" x="90" width="140" height="130" fill="#3b2214"/><rect id="pi-creme" x="90" width="140" height="4" fill="#c99263"/></g>
        <path d="${d('p-tasse')}" fill="#f2f1f9"/>
        <path d="${d('p-v1')}" fill="#0c3b83"/><path d="${d('p-v2')}" fill="#f2f1f9"/><path d="${d('p-v3')}" fill="#f94443"/>
      </svg>
      <svg class="pi-grains" viewBox="0 0 520 630">${[
        grain(80, 70, 20, 3.1), grain(205, 32, -35, 2.6), grain(450, 84, 50, 3.4, true), grain(488, 232, -15, 2.4),
        grain(42, 262, 70, 2.2), grain(170, 182, -60, 2.0), grain(486, 392, 10, 2.3),
      ].join('')}</svg>
      <div class="pi-bas"><p>Mini-jeu du Café Français · cafe-fr.com</p><span class="pi-defi">À toi de jouer&nbsp;!</span></div>
      <div class="pi-barre"><i></i><i></i><i></i></div>`;
    const style = document.createElement('style');
    style.textContent = `
      html, body { overflow: hidden !important; }
      body > *:not(#partage-image) { visibility: hidden !important; }
      #partage-image { position: fixed; inset: 0; width: 1200px; height: 630px; z-index: 2147483647; overflow: hidden; background: #131a28; color: #f2f1f9; }
      #partage-image p { margin: 0; }
      .pi-fond { position: absolute; inset: 0; width: 100%; height: 100%; fill: none; stroke: #26334d; stroke-width: 1.6px; }
      .pi-fond path { vector-effect: non-scaling-stroke; }
      .pi-halo { position: absolute; left: 650px; top: 110px; width: 540px; height: 500px; background: radial-gradient(closest-side, rgba(201, 146, 99, .24), rgba(201, 146, 99, 0)); }
      .pi-nom { position: absolute; left: 76px; top: 58px; }
      .pi-nom svg { display: block; width: 250px; height: auto; }
      .pi-score { position: absolute; left: 76px; top: 168px; display: grid; justify-items: start; }
      .pi-avant { font: 500 22px/1 "DM Mono", monospace; letter-spacing: .2em; text-transform: uppercase; color: #a6aec3; }
      .pi-nombre { margin-top: 4px !important; font: 800 230px/.9 "Bricolage Grotesque", sans-serif; font-stretch: 85%; letter-spacing: -.03em; font-variant-numeric: tabular-nums; }
      .pi-unite { margin-top: 6px !important; font: 700 40px/1.1 "Bricolage Grotesque", sans-serif; font-stretch: 90%; color: #c99263; }
      .pi-titre { margin-top: 26px !important; display: flex; align-items: center; gap: 10px; padding: 10px 18px 10px 14px; border-radius: 999px; border: 1.5px solid #f0b232; color: #f0b232; font: 700 24px/1 "Instrument Sans", sans-serif; }
      .pi-titre svg { width: 22px; height: 22px; fill: #f0b232; }
      .pi-tasse { position: absolute; left: 720px; top: 110px; width: 400px; height: auto; }
      .pi-grains { position: absolute; left: 660px; top: 0; width: 520px; height: 630px; }
      .pi-bas { position: absolute; left: 76px; right: 76px; top: 540px; display: flex; align-items: center; justify-content: space-between; }
      .pi-bas p { font: 500 18px/1 "DM Mono", monospace; letter-spacing: .14em; text-transform: uppercase; color: #a6aec3; }
      .pi-defi { display: flex; align-items: center; height: 46px; padding: 0 22px; border-radius: 23px; background: #f2f1f9; color: #131a28; font: 700 23px/1 "Instrument Sans", sans-serif; }
      .pi-barre { position: absolute; left: 0; right: 0; bottom: 0; height: 10px; display: flex; }
      .pi-barre i { flex: 1; } .pi-barre i:nth-child(1) { background: #0c3b83; } .pi-barre i:nth-child(2) { background: #f2f1f9; } .pi-barre i:nth-child(3) { background: #c3242f; }`;
    document.head.append(style);
    document.body.append(scene);
    await document.fonts.ready;
  });
}

async function dessiner(page, n, fichier) {
  await page.evaluate(({ n, unite, titre }) => {
    document.getElementById('pi-nombre').textContent = n;
    document.getElementById('pi-unite').textContent = unite;
    document.getElementById('pi-titre').textContent = titre;
    // La tasse se remplit avec le score
    const y = 202 - 61 * Math.min(1, Math.max(.15, n / 160));
    document.getElementById('pi-cafe').setAttribute('y', y);
    document.getElementById('pi-creme').setAttribute('y', y);
  }, { n, unite: `${n > 1 ? 'grains' : 'grain'} de café en 45 secondes`, titre: titre(n) });
  await page.screenshot({ path: fichier, type: 'jpeg', quality: 88 });
}

(async () => {
  const demandes = process.argv.slice(2).filter((a) => /^\d+$/.test(a)).map(Number);
  const scores = demandes.length ? demandes : Array.from({ length: SCORE_MAX }, (_, i) => i + 1);
  if (scores.some((n) => n < 1 || n > SCORE_MAX)) throw new Error(`les scores vont de 1 à ${SCORE_MAX}`);
  const nav = await navigateur();
  try {
    const page = await nav.newPage({ viewport: { width: 1200, height: 630 } });
    // Seules les polices sont chargées : sans GSAP, la page reste immobile
    await page.route(/^https?:\/\/(?!fonts\.(googleapis|gstatic)\.com)/, (r) => r.abort());
    await page.goto('file://' + PAGE);
    await preparerScene(page);
    for (const n of scores) {
      const dossier = path.join(RACINE, 'score', String(n));
      fs.mkdirSync(dossier, { recursive: true });
      fs.writeFileSync(path.join(dossier, 'index.html'), pageHtml(n));
      await dessiner(page, n, path.join(dossier, 'partage.jpg'));
    }
  } finally {
    await nav.close();
  }
  console.log(`${scores.length} page(s) de partage générée(s) dans score/.`);
})().catch((e) => { console.error(e.message); process.exit(1); });
