// Annonce de la petite info du jour sur le serveur Discord, pile à midi (heure de Paris).
// Tâche Cloudflare (Worker) lancée par deux horaires, 10 h et 11 h UTC (voir wrangler.toml) : seul celui qui tombe à
// midi à Paris envoie l'annonce, en été comme en hiver. L'info est lue dans infos.json sur le site, puis postée sous
// forme d'embed par le webhook du salon (secret DISCORD_WEBHOOK_INFO). Même présentation que outils/annonce_info.py.

const PARIS = 'Europe/Paris';
const COULEUR = 0x6b95ff; // le bleu du site
const JOURS = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche'];
const MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];

// Comme sur le site : espaces insécables avant ? ! : ; %, dans les guillemets et dans les nombres (161 000)
const fr = (t) => String(t || '').replace(/ ([?!:;»%])/g, ' $1').replace(/« /g, '« ').replace(/(\d) (?=\d{3}\b)/g, '$1 ');

// Date (AAAA-MM-JJ) et heure à Paris
function paris(maintenant) {
  const p = Object.fromEntries(new Intl.DateTimeFormat('en-CA', { timeZone: PARIS, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', hourCycle: 'h23' })
    .formatToParts(maintenant).map((x) => [x.type, x.value]));
  return { jour: `${p.year}-${p.month}-${p.day}`, heure: Number(p.hour) };
}

export function embed(info) {
  const source = info.source || {};
  const champs = [];
  if (info.theme) champs.push({ name: 'Thème', value: info.theme, inline: true });
  if (/^https:\/\//.test(source.url || '')) champs.push({ name: 'Source', value: `[${source.nom || 'Lire l’article'}](${source.url})`, inline: true });
  const [a, m, j] = info.date.split('-').map(Number);
  const jourSemaine = JOURS[(new Date(Date.UTC(a, m - 1, j)).getUTCDay() + 6) % 7];
  return {
    author: { name: `☕ La petite info du jour · ${jourSemaine} ${j} ${MOIS[m - 1]}` },
    title: fr(info.titre).slice(0, 256),
    url: 'https://cafe-fr.com/#info',
    description: fr(info.texte).slice(0, 3800) + '\n\n[Toutes les infos sur cafe-fr.com](https://cafe-fr.com/infos/)',
    color: COULEUR,
    fields: champs,
    footer: { text: 'La Gazette du Café · une info chaque jour à midi' },
    timestamp: new Date(info.publication).toISOString(),
  };
}

export async function annoncer(env, maintenant = new Date()) {
  const { jour, heure } = paris(maintenant);
  if (heure !== 12) return `Pas encore midi à Paris (${heure} h) : rien à faire.`;
  const webhook = String(env.DISCORD_WEBHOOK_INFO || '').trim();
  if (!/^https:\/\/(discord|discordapp)\.com\/api\/webhooks\/\d+\/[\w-]+/.test(webhook)) return 'Webhook Discord absent ou invalide : rien n’est envoyé.';
  const r = await fetch(`${env.SITE}/infos.json`, { cf: { cacheTtl: 0 }, headers: { 'Cache-Control': 'no-cache' } });
  if (!r.ok) throw new Error(`infos.json illisible (HTTP ${r.status})`);
  const info = ((await r.json()).infos || []).find((x) => x && x.date === jour && x.titre);
  if (!info) return `Pas d'info datée du ${jour} : rien à annoncer.`;
  const reponse = await fetch(webhook + (webhook.includes('?') ? '&' : '?') + 'wait=true', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'La Gazette du Café', embeds: [embed(info)], allowed_mentions: { parse: [] } }),
  });
  // Seulement le code : l'adresse du webhook est secrète et ne doit pas apparaître dans les journaux
  if (!reponse.ok) throw new Error(`Discord a refusé l'annonce (HTTP ${reponse.status})`);
  return `Info du ${jour} annoncée : ${info.titre}`;
}

export default {
  async scheduled(evenement, env, ctx) {
    ctx.waitUntil(annoncer(env, new Date(evenement.scheduledTime)).then(console.log));
  },
};
