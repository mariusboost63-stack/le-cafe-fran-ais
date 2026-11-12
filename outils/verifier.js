/* Le test avant publication : ouvre chaque page du site, sur ordinateur et sur téléphone, et vérifie qu'elle
   s'affiche sans erreur. Lancé par GitHub Actions avant chaque mise en ligne (.github/workflows/publier.yml) : si une
   page casse, rien n'est publié.

   Pour chaque page : aucune erreur JavaScript, le titre de la page est le bon, sa première section est visible, et
   rien ne déborde sur les côtés. Les données relevées dans le bot (classement.json…) sont lues si elles sont à la
   racine du dépôt ; les services extérieurs (Discord…) sont coupés, pour un test qui ne dépend que du site.

   Utilisation, depuis la racine du dépôt : node outils/verifier.js
   Nécessite Playwright (ou playwright-core et Google Chrome) : voir outils/navigateur.js. */
const http = require('http');
const fs = require('fs');
const path = require('path');
const navigateur = require('./navigateur');

const RACINE = path.join(__dirname, '..');
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.woff2': 'font/woff2', '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.ics': 'text/calendar', '.txt': 'text/plain' };

// Un petit serveur pour le dossier du site
function servir() {
  const serveur = http.createServer((req, res) => {
    let chemin = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    if (chemin.endsWith('/')) chemin += 'index.html';
    const fichier = path.join(RACINE, path.normalize(chemin).replace(/^(\.\.[/\\])+/, ''));
    if (!fichier.startsWith(RACINE) || !fs.existsSync(fichier) || fs.statSync(fichier).isDirectory()) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(fichier)] || 'application/octet-stream' });
    fs.createReadStream(fichier).pipe(res);
  });
  return new Promise((ok) => serveur.listen(0, '127.0.0.1', () => ok(serveur)));
}

(async () => {
  const source = fs.readFileSync(path.join(RACINE, 'index.html'), 'utf8');
  const pages = JSON.parse(source.match(/<script type="application\/json" id="pages-du-site">([\s\S]*?)<\/script>/)[1]);
  const serveur = await servir();
  const base = `http://127.0.0.1:${serveur.address().port}`;
  const b = await navigateur();
  const problemes = [];
  for (const [largeur, hauteur, appareil] of [[1366, 800, 'ordinateur'], [390, 844, 'téléphone']]) {
    for (const p of pages) {
      const contexte = await b.newContext({ viewport: { width: largeur, height: hauteur } });
      const page = await contexte.newPage();
      const erreurs = [];
      page.on('pageerror', (e) => erreurs.push(e.message));
      // les services extérieurs sont coupés : le test ne dépend que du site
      await page.route('**/*', (r) => (r.request().url().startsWith(base) ? r.continue() : r.abort()));
      await page.addInitScript(() => { try { localStorage.setItem('cafe-porte', '1'); } catch (e) { /* rien */ } });
      const ou = `${appareil} ${p.chemin}`;
      try {
        await page.goto(p.id === 'accueil' ? `${base}/` : `${base}/?page=${p.id}`, { waitUntil: 'load', timeout: 30000 });
        await page.waitForTimeout(2000);
        const etat = await page.evaluate((p) => {
          const vis = (e) => !!e && !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          const titre = p.id === 'accueil' ? document.querySelector('h1.logo-titre') : document.querySelector('#fil-page');
          return {
            titre: titre ? titre.textContent.trim() : '',
            titreVisible: vis(titre),
            sections: p.ancres.map((a) => ({ id: a, vue: vis(document.getElementById(a)), cachee: !!document.getElementById(a) && document.getElementById(a).hidden })),
            page: document.documentElement.getAttribute('data-page'),
            largeur: document.documentElement.scrollWidth,
            ecran: innerWidth,
          };
        }, p);
        if (etat.page !== p.id) problemes.push(`${ou} : la page affichée est « ${etat.page} »`);
        if (!etat.titreVisible) problemes.push(`${ou} : titre de la page invisible`);
        if (p.id !== 'accueil' && etat.titre !== p.nom) problemes.push(`${ou} : titre « ${etat.titre} » au lieu de « ${p.nom} »`);
        // une section cachée exprès (pas encore de données) n'est pas une panne ; une page sans rien de visible, si
        const vues = etat.sections.filter((x) => x.vue), absentes = etat.sections.filter((x) => !x.vue && !x.cachee);
        if (!vues.length && absentes.length) problemes.push(`${ou} : aucune section visible (#${absentes.map((x) => x.id).join(', #')})`);
        else if (!vues.length) console.log(`  (${ou} : sections cachées faute de données, #${etat.sections.map((x) => x.id).join(', #')})`);
        if (etat.largeur > etat.ecran + 1) problemes.push(`${ou} : la page déborde sur les côtés (${etat.largeur} px pour ${etat.ecran})`);
      } catch (e) {
        problemes.push(`${ou} : la page ne s'ouvre pas (${e.message.split('\n')[0]})`);
      }
      erreurs.forEach((m) => problemes.push(`${ou} : erreur JavaScript « ${m} »`));
      console.log(`${erreurs.length ? '✗' : '✓'} ${ou}`);
      await contexte.close();
    }
  }
  await b.close();
  serveur.close();
  if (problemes.length) {
    console.log(`\n${problemes.length} problème(s) :\n- ${problemes.join('\n- ')}`);
    if (process.env.GITHUB_ACTIONS) problemes.forEach((m) => console.log(`::error::${m}`));
    process.exitCode = 1;
  } else console.log('\nToutes les pages s\'affichent sans erreur.');
})();
