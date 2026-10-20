/* Lance Chrome pour dessiner l'image d'aperçu (outils/membres.js) :
   Playwright avec son propre Chromium, ou playwright-core avec le Google Chrome de la machine.
   La variable CHROME peut donner le chemin d'un autre exécutable. */
module.exports = async function navigateur() {
  let pw;
  try { pw = require('playwright'); } catch (e) { pw = require('playwright-core'); }
  if (process.env.CHROME) return pw.chromium.launch({ executablePath: process.env.CHROME });
  try { return await pw.chromium.launch(); } catch (e) { return pw.chromium.launch({ channel: 'chrome' }); }
};
