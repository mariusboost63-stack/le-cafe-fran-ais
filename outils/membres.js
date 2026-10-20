#!/usr/bin/env node
/* Met à jour le nombre de membres du serveur là où il est écrit en dur :
   - index.html : le compteur de l'ouverture et la phrase de fin de page (nombre exact),
     la description du lien partagé (arrondi à la centaine : « plus de 9 200 membres ») ;
   - apercu.png : l'image affichée quand le lien du site est partagé (même arrondi).
   Lancé chaque jour par GitHub Actions (.github/workflows/membres.yml). Sur la page, le nombre exact est
   aussi demandé à Discord à chaque visite : les valeurs écrites ici servent quand Discord ne répond pas.

   Usage : node outils/membres.js           relève le nombre sur Discord
           node outils/membres.js 9251      utilise ce nombre
           node outils/membres.js --image   régénère aussi l'image, même si l'arrondi n'a pas changé
   L'image est dessinée par Chrome (Playwright, ou playwright-core avec Google Chrome installé). */
const fs = require('fs');
const path = require('path');
const navigateur = require('./navigateur');

const RACINE = path.join(__dirname, '..');
const PAGE = path.join(RACINE, 'index.html');
const IMAGE = path.join(RACINE, 'apercu.png');
const INVITATION = 'france';

const grouper = (n, sep) => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, sep);
const arrondi = (n) => Math.floor(n / 100) * 100;
const attendre = (ms) => new Promise((r) => setTimeout(r, ms));
// Dans GitHub Actions, le message s'affiche aussi dans le résumé de l'exécution
const signaler = (texte, niveau = 'notice') => console.log(process.env.GITHUB_ACTIONS ? `::${niveau}::${texte}` : texte);

async function relever() {
  const url = `https://discord.com/api/v10/invites/${INVITATION}?with_counts=true`;
  for (let essai = 0; essai < 3; essai++) {
    const res = await fetch(url, { headers: { 'User-Agent': 'cafe-fr.com (membres)', Accept: 'application/json' } });
    if (res.status === 429) { // trop d'appels : Discord dit combien de temps attendre
      const corps = await res.json().catch(() => ({}));
      await attendre(Math.min(Number(corps.retry_after) || 2, 30) * 1000 + 500);
      continue;
    }
    if (!res.ok) throw new Error(`Discord a répondu ${res.status}`);
    const n = Number((await res.json()).approximate_member_count);
    if (!Number.isInteger(n) || n < 1000) throw new Error(`nombre de membres invalide : ${n}`);
    return n;
  }
  throw new Error('Discord limite les appels, réessayer plus tard');
}

// Remplace un passage qui doit apparaître exactement une fois dans la page
function remplacer(html, motif, rempl, nom) {
  const trouves = html.match(new RegExp(motif.source, 'g')) || [];
  if (trouves.length !== 1) throw new Error(`${nom} : ${trouves.length} occurrence(s) dans index.html au lieu d'une`);
  return html.replace(motif, rempl);
}

function majPage(n) {
  const avant = fs.readFileSync(PAGE, 'utf8');
  const ancien = avant.match(/Rejoins plus de ([\d\u00a0]+) membres/);
  let html = remplacer(avant, /(id="nb-membres" data-valeur=")\d+(">)[\d&#;]+(<\/b>)/, `$1${n}$2${grouper(n, '&#8239;')}$3`, 'compteur de l\'ouverture');
  html = remplacer(html, /(<span id="nb-final">)[\d&#;]+(<\/span>)/, `$1${grouper(n, '&#8239;')}$2`, 'phrase de fin');
  html = remplacer(html, /Rejoins [^"]*? membres sur discord\.gg\/france\./, `Rejoins plus de ${grouper(arrondi(n), '\u00a0')} membres sur discord.gg/france.`, 'description du lien partagé');
  if (html !== avant) fs.writeFileSync(PAGE, html);
  return { modifiee: html !== avant, arrondiChange: !ancien || Number(ancien[1].replace(/\D/g, '')) !== arrondi(n) };
}

// Dessine apercu.png (1200 × 630) avec le logo de la page, les lettres du fond et le nombre de membres
async function dessinerImage(n) {
  const nav = await navigateur();
  try {
    const page = await nav.newPage({ viewport: { width: 1200, height: 630 } });
    // Seules les polices sont chargées : sans GSAP, le logo reste immobile
    await page.route(/^https?:\/\/(?!fonts\.(googleapis|gstatic)\.com)/, (r) => r.abort());
    await page.goto('file://' + PAGE);
    await page.evaluate(async (texte) => {
      const lettre = (id, cx, cy, h, r) => {
        const el = document.getElementById(id);
        const b = el.getBBox();
        const s = h / b.height;
        return `<path d="${el.getAttribute('d')}" transform="translate(${cx} ${cy}) rotate(${r}) scale(${s}) translate(${-(b.x + b.width / 2)} ${-(b.y + b.height / 2)})"/>`;
      };
      const scene = document.createElement('div');
      scene.id = 'apercu';
      scene.innerHTML = `
        <svg class="ap-fond" viewBox="0 0 1200 630">${[
          lettre('p-F', 150, 250, 560, -14), lettre('p-cc', 1110, 170, 430, 12), lettre('p-a2', 330, 590, 300, 18),
          lettre('p-e2', 960, 560, 300, -20), lettre('p-c', 610, 20, 200, 8),
        ].join('')}</svg>
        <div class="ap-logo"></div>
        <div class="ap-bas"><p><span class="ap-drapeau"><i></i><i></i><i></i></span>${texte}</p><span class="ap-lien">discord.gg/france</span></div>
        <div class="ap-barre"><i></i><i></i><i></i></div>`;
      scene.querySelector('.ap-logo').append(document.getElementById('logo'));
      const style = document.createElement('style');
      style.textContent = `
        html, body { overflow: hidden !important; }
        body > *:not(#apercu) { visibility: hidden !important; }
        #apercu { position: fixed; inset: 0; width: 1200px; height: 630px; z-index: 2147483647; background: #131a28; overflow: hidden; }
        .ap-fond { position: absolute; inset: 0; width: 100%; height: 100%; fill: none; stroke: #26334d; stroke-width: 1.6px; }
        .ap-fond path { vector-effect: non-scaling-stroke; }
        .ap-logo { position: absolute; left: 0; right: 0; top: var(--haut, 118px); display: flex; justify-content: center; }
        .ap-logo .logo { width: var(--largeur, 822px); transform: translateX(var(--dx, 0px)); }
        .ap-bas { position: absolute; left: 0; right: 0; top: 452px; display: flex; align-items: center; justify-content: center; gap: 26px; }
        .ap-bas p { margin: 0; display: flex; align-items: center; gap: 15px; font: 500 19px/1 "DM Mono", monospace; letter-spacing: .13em; text-transform: uppercase; color: #969fb3; }
        .ap-drapeau { display: flex; width: 33px; height: 13px; border-radius: 3px; overflow: hidden; }
        .ap-drapeau i { flex: 1; } .ap-drapeau i:nth-child(1) { background: #6b95ff; } .ap-drapeau i:nth-child(2) { background: #f2f1f9; } .ap-drapeau i:nth-child(3) { background: #f94443; }
        .ap-lien { display: flex; align-items: center; height: 51px; padding: 0 22px; border-radius: 26px; background: #f2f1f9; color: #131a28; font: 700 26px/1 "Instrument Sans", sans-serif; letter-spacing: -.01em; }
        .ap-barre { position: absolute; left: 0; right: 0; bottom: 0; height: 10px; display: flex; }
        .ap-barre i { flex: 1; } .ap-barre i:nth-child(1) { background: #0c3b83; } .ap-barre i:nth-child(2) { background: #f2f1f9; } .ap-barre i:nth-child(3) { background: #c3242f; }`;
      document.head.append(style);
      document.body.append(scene);
      await document.fonts.ready;
    }, `Serveur Discord francophone · plus de ${grouper(arrondi(n), '\u202f')} membres`);
    await page.waitForTimeout(300);
    await page.screenshot({ path: IMAGE });
  } finally {
    await nav.close();
  }
}

(async () => {
  const arg = process.argv.slice(2);
  const donne = arg.find((a) => /^\d+$/.test(a));
  let n;
  try {
    n = donne ? Number(donne) : await relever();
  } catch (e) {
    // Discord injoignable : on garde les valeurs actuelles, sans faire échouer la tâche quotidienne
    signaler(`Nombre de membres non relevé (${e.message}) : rien n'est modifié.`, 'warning');
    return;
  }
  const { modifiee, arrondiChange } = majPage(n);
  const image = arrondiChange || arg.includes('--image');
  if (image) await dessinerImage(n);
  signaler(`${n} membres (aperçu : plus de ${arrondi(n)}). index.html ${modifiee ? 'mis à jour' : 'déjà à jour'}${image ? ', apercu.png redessinée' : ''}.`);
})().catch((e) => { console.error(e.message); process.exit(1); });
