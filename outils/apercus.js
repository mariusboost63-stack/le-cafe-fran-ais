// Dessine l'image d'aperçu de chaque page (apercus/<page>.jpg, 1200 × 630) : ce que montrent Discord et les réseaux
// quand on partage un lien vers cafe-fr.com/deckfr/, /classement/… L'accueil garde apercu.png (outils/membres.js).
// À gauche, le nom de la page et son résumé ; à droite, l'objet de la page (la caisse des grains, les jetons de DeckFR…),
// photographié sur le site.
//
// Utilisation, depuis la racine du dépôt, avec le site servi en local et Playwright installé :
//   python3 -m http.server 8765 &
//   node outils/apercus.js [adresse du site local, par défaut http://localhost:8765]
// Les blocs qui dépendent des relevés du bot (le livre d'or du classement…) ont besoin des fichiers de la branche data :
//   git show origin/data:classement.json > /tmp/data/classement.json (idem deckfr.json, records.json), puis DONNEES=/tmp/data
// À relancer quand une page change d'allure ou de résumé. Nécessite Python 3 (pour la conversion en JPEG, Pillow).
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const SITE = process.argv[2] || 'http://localhost:8765';
const DOSSIER = path.join(__dirname, '..', 'apercus');
// L'objet photographié pour chaque page
const OBJETS = {
  niveaux: '.compteur-niveau', evenements: '.liege', grains: '.caisse', deckfr: '.dk-main',
  classement: '.livre-couverture', 'info-du-jour': '.journal', equipe: '.badges', 'premiers-pas': '.devanture',
};

(async () => {
  const source = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
  const pages = JSON.parse(source.match(/<script type="application\/json" id="pages-du-site">([\s\S]*?)<\/script>/)[1]);
  fs.mkdirSync(DOSSIER, { recursive: true });
  const b = await chromium.launch();
  for (const p of pages.filter((x) => OBJETS[x.id])) {
    // 1. La photo de l'objet, sur la page du site
    const page = await b.newPage({ viewport: { width: 1400, height: 1000 }, deviceScaleFactor: 2 });
    await page.addInitScript(() => { localStorage.setItem('cafe-porte', '1'); localStorage.setItem('cafe-animations', 'reduites'); });
    if (process.env.DONNEES) {
      for (const f of fs.readdirSync(process.env.DONNEES).filter((x) => x.endsWith('.json'))) {
        const corps = fs.readFileSync(path.join(process.env.DONNEES, f), 'utf8');
        await page.route(`**/${f}`, (r) => r.fulfill({ status: 200, contentType: 'application/json', body: corps }));
      }
    }
    await page.goto(`${SITE}/?page=${p.id}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2500);
    await page.addStyleTag({ content: '#barre, .saut { visibility: hidden !important; }' });
    // la gazette : un titre qui ne se périme pas, plutôt que l'info du jour
    if (p.id === 'info-du-jour') await page.evaluate(() => {
      document.querySelector('#info-titre').textContent = 'Une petite info sur la France, chaque jour à midi';
      document.querySelector('#info-texte').textContent = '';
      document.querySelector('#info-date').textContent = 'Édition du jour';
      ['#info-source', '#info-theme'].forEach((s) => { const e = document.querySelector(s); if (e) e.hidden = true; });
    });
    const objet = await page.$(OBJETS[p.id]);
    await objet.scrollIntoViewIfNeeded();
    await page.waitForTimeout(600);
    const photo = (await objet.screenshot({ type: 'png' })).toString('base64');
    await page.close();
    // 2. L'image d'aperçu
    const carte = await b.newPage({ viewport: { width: 1200, height: 630 } });
    await carte.goto(`${SITE}/404.html`);
    await carte.evaluate(([site, nom, resume, chemin, photo]) => {
      document.head.innerHTML = `<link rel="stylesheet" href="${site}/polices/polices.css"><style>
        * { box-sizing: border-box; margin: 0; }
        body { width: 1200px; height: 630px; overflow: hidden; background: #131a28; color: #f2f1f9; font-family: "Instrument Sans", sans-serif; position: relative; }
        .fond { position: absolute; inset: 0; background: radial-gradient(60% 80% at 80% 50%, rgba(201,146,99,.18), transparent 70%); }
        .texte { position: absolute; left: 64px; top: 0; bottom: 64px; width: 520px; display: flex; flex-direction: column; justify-content: center; gap: 22px; }
        .marque { display: flex; align-items: center; gap: 14px; font: 700 26px/1 "Bricolage Grotesque", sans-serif; }
        .marque svg { width: 58px; height: auto; }
        h1 { font: 800 104px/.9 "Bricolage Grotesque", sans-serif; font-stretch: 84%; letter-spacing: -.035em; }
        p { font-size: 28px; line-height: 1.3; color: #a6aec3; }
        .lien { align-self: flex-start; padding: 12px 22px; border-radius: 999px; background: #f2f1f9; color: #131a28; font: 700 26px/1 "Bricolage Grotesque", sans-serif; }
        .objet { position: absolute; right: 48px; top: 50%; width: 500px; height: 480px; transform: translateY(calc(-50% - 22px)) rotate(-2deg); display: grid; place-items: center; }
        .objet img { max-width: 100%; max-height: 100%; filter: drop-shadow(0 30px 40px rgba(0,0,0,.6)); }
        .drapeau { position: absolute; left: 0; right: 0; bottom: 0; height: 10px; background: linear-gradient(90deg, #0c3b83 33.3%, #f2f1f9 33.3% 66.6%, #c3242f 66.6%); }
      </style>`;
      document.body.innerHTML = `<div class="fond"></div><div class="texte">
        <div class="marque"><svg viewBox="6 40 240 198"><use href="#tasse"/></svg>Le Café Français</div>
        <h1>${nom}</h1><p>${resume}</p><span class="lien">cafe-fr.com${chemin}</span></div>
        <div class="objet"><img src="data:image/png;base64,${photo}"></div><div class="drapeau"></div>`;
    }, [SITE, p.nom, p.resume, p.chemin, photo]);
    // le logo : la tasse et sa vapeur, reprises du site
    const logo = (source.match(/<path id="p-tasse" d="([^"]+)"/) || [])[1];
    const vapeurs = ['p-v1', 'p-v2', 'p-v3'].map((id) => (source.match(new RegExp(`<path id="${id}" d="([^"]+)"`)) || [])[1]);
    await carte.evaluate(([logo, v]) => {
      document.querySelector('.marque svg').innerHTML = `<path d="${logo}" fill="#f2f1f9"/><path d="${v[0]}" fill="#6b95ff"/><path d="${v[1]}" fill="#f2f1f9"/><path d="${v[2]}" fill="#f94443"/>`;
    }, [logo, vapeurs]);
    await carte.evaluate(() => document.fonts.ready);
    await carte.waitForTimeout(400);
    const png = path.join(DOSSIER, `${p.id}.png`);
    await carte.screenshot({ path: png });
    await carte.close();
    // 3. En JPEG, plus léger
    execFileSync('python3', ['-c', `from PIL import Image; Image.open(${JSON.stringify(png)}).convert('RGB').save(${JSON.stringify(png.replace(/\.png$/, '.jpg'))}, quality=86, optimize=True)`]);
    fs.unlinkSync(png);
    console.log('aperçu', p.chemin);
  }
  await b.close();
})();
