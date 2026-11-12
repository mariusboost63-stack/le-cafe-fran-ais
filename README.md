# Le Café Français

Site vitrine animé du serveur Discord francophone **Le Café Français** : [discord.gg/france](https://discord.gg/france).

En ligne sur **[cafe-fr.com](https://cafe-fr.com)**, publié sur Cloudflare Pages par GitHub Actions (voir « Mise en ligne »). Chaque modification poussée sur la branche `main` est publiée automatiquement.

Tout tient dans un seul fichier, `index.html` (HTML, CSS et JavaScript), qui affiche une page par sujet (voir « Le site en pages »). Les animations utilisent [GSAP](https://gsap.com) et ScrollTrigger (dossier `js/`), et les polices sont dans `polices/` : la page ne demande rien à Google Fonts ni à un CDN.

## Le site en pages

Le site est découpé en pages courtes, chacune avec son adresse :

| Page | Adresse | Sections |
| --- | --- | --- |
| Accueil | `/` | ouverture, ruban, la visite du propriétaire (`#carte`), les salons vocaux (`#vocaux`), en direct (`#direct`), « Au menu » (`#au-menu`) |
| Niveaux | `/niveaux/` | `#niveaux` |
| Événements (Halloween, Noël en saison) | `/evenements/` | `#evenements`, `#noel`, `#halloween`, `#prochains` |
| Grains | `/grains/` | `#grains` (avec la boutique) |
| DeckFR | `/deckfr/` | `#deckfr` |
| Classement | `/classement/` | `#classement` |
| Info du jour | `/info-du-jour/` | `#info` |
| Équipe | `/equipe/` | `#equipe` |
| Premiers pas | `/premiers-pas/` | `#entrer`, `#commande`, `#faq`, `#rejoindre` |

- La liste est dans `index.html`, dans le bloc `<script type="application/json" id="pages-du-site">` (nom, titre, description, résumé et sections de chaque page). Pour déplacer une section, change ses `ancres` ; pour une nouvelle page, ajoute une entrée, un lien dans le menu, le pied de page et « Au menu », et son adresse dans `sitemap.xml`.
- On passe d'une page à l'autre sans recharger : l'ambiance sonore continue, les boutons Précédent et Suivant du navigateur ramènent à la page et à l'endroit quittés, le titre de l'onglet change.
- Chaque page a un fil d'Ariane en haut (Accueil / Classement) et, en bas, la page précédente et la page suivante (la dernière ramène à l'accueil). Le menu souligne la page en cours ; sous 1 180 px de large, il passe dans le bouton « menu ».
- L'accueil se termine par « Au menu » : une carte par page avec un aperçu en direct (prochain rendez-vous, n° 1 du classement, titre de l'info du jour, recrutement…).
- Les anciennes adresses avec une ancre (`cafe-fr.com/#classement`, `#faq`…) mènent à la bonne page. Un lien vers une section d'une autre page s'écrit `/premiers-pas/#faq`.
- La porte d'entrée ne s'affiche qu'en arrivant par l'accueil : un lien direct vers une page y mène sans détour.
- Sur un hébergement qui n'a pas ces copies (GitHub Pages), `404.html` renvoie aussitôt une page du site vers l'accueil (`/?page=classement`), qui ouvre la bonne page et remet son adresse : le rechargement marche partout. La liste des pages y est recopiée : ajoute-y toute nouvelle page.
- Pour la publication, `outils/pages.py` copie `index.html` dans le dossier de chaque page (`classement/index.html`…) avec le titre, la description et l'adresse de la page, pour les aperçus de liens et les moteurs de recherche. Les chemins du site sont absolus (`/js/…`, `/polices/…`, `/classement.json`) pour marcher depuis n'importe quelle page.
- Sans JavaScript, tout reste affiché sur une seule page.

## Ce que contient la page

- L'ouverture, avec le logo vectorisé qui se compose (tasse, vapeur tricolore, lettres).
- Un ruban « Bonjour, Salut, Coucou… » dont la vitesse suit le défilement.
- La visite des salles en défilement horizontal bleu, blanc, rouge : le comptoir (Café Français), la terrasse (Centre de Convivialité) et l'arrière-salle (Divertissements), avec la description de chaque salon.
- Le système de niveaux : un compteur grimpe de palier en palier, de @Curieux (niveau 2) à @Légende (niveau 100), et affiche les avantages débloqués (couleurs de pseudo, bonus de grains, virements).
- L'événement Halloween 2026 : compte à rebours en direct jusqu'à la prochaine quête, lien vers le salon #les-quêtes (`https://discord.com/channels/829698572927762432/1560700305631481959`, s'ouvre pour les membres du serveur), calendrier des 7 quêtes, barème des citrouilles, récompenses et rôles à gagner.
- Les grains : toutes les façons d'en gagner (vocal, messages, /journalier, /hebdomadaire, casino, /voler), un calculateur de gains en vocal et la boutique, avec le temps de vocal nécessaire pour chaque article.
- Les salons vocaux et leurs limites de places.
- L'équipe, présentée sur des badges suspendus avec les profils de chacun : Gérants, Administrateurs, Responsables, et le reste de l'équipe sur le Discord.
- La fin du site, comme une sortie de café : « Pousser la porte » dessine la devanture (enseigne dorée, store tricolore, une étape sur chaque vitre et sur la porte, dont la pancarte suit la saison), la FAQ est une conversation au comptoir (les questions en bulles, les réponses de l'équipe), la tasse se remplit sur sa soucoupe, posée sur le zinc, et « Le pot à pourboires » présente les moyens de soutenir le café. Le pied de page reprend le store, le plan du site et les petits plus.
- À la première visite, l'entrée « Pousser la porte » : la devanture du café s'ouvre avec un tintement de clochette. Le bouton « Repasser la porte », dans le pied de page, la fait revenir.
- « Commande ton café » : quatre questions qui révèlent la boisson et la table du café faites pour le visiteur, avec ses salons conseillés.
- Un bouton « Ambiance » qui joue un fond sonore de café parisien, entièrement synthétisé dans la page (aucun fichier audio) : la rumeur de la salle, des tables qui bavardent et rient (voix trop lointaines pour qu'on comprenne les mots), tasses, cuillères, verres et monnaie, la machine à expresso (moulin, coups du porte-filtre, pompe, buse vapeur), la porte et sa clochette, une chaise qu'on recule, et un accordéon au poste : une valse musette composée pour le site, et en décembre « Douce nuit » et « Vive le vent » (airs du domaine public), avec un feu de cheminée et des grelots. Le café vit à l'heure de Paris (calme le matin, plein à midi, radio plus présente le soir, presque vide la nuit), et le nombre de tables qui parlent suit les membres en ligne. Le bouton de réglages, à côté, règle le volume, coupe la musique et choisit si « Pousser la porte » lance l'ambiance (choix gardés sur l'appareil).
- La section « DeckFR » (`#deckfr`) : le jeu de cartes du bot, ses salons, ses sept raretés, ses chiffres en direct et toutes les cartes, recto et verso (voir « DeckFR »).
- Les animations jouent pour tout le monde, même sur les appareils réglés en « mouvement réduit ». L'interrupteur « Animations », en bas du pied de page, permet à chaque visiteur de les couper (choix gardé sur son appareil).
- Des surprises : cliquer sur la tasse du logo la remplit, taper « café » au clavier fait pleuvoir des grains, taper « boo » lâche des chauves-souris.

## Données en direct

La page lit le widget public du serveur :

```
https://discord.com/api/guilds/829698572927762432/widget.json
```

Une fois le site en ligne, elle affiche le nombre de membres connectés, l'occupation de chaque salon vocal et les avatars des personnes en ligne. Le widget doit rester activé dans les paramètres du serveur (Paramètres du serveur → Widget). Si le widget ne répond pas, la page garde les valeurs écrites dans le HTML.

Le nombre total de membres est demandé à Discord à chaque visite, par l'invitation publique :

```
https://discord.com/api/v10/invites/france?with_counts=true
```

## Nombre de membres à jour

Chaque jour vers 6 h, GitHub Actions (`.github/workflows/membres.yml`) lance `outils/membres.js`, qui relève le nombre de membres sur Discord et met à jour :

- dans `index.html`, le compteur de l'ouverture et la phrase de fin de page (nombre exact). Ils servent quand Discord ne répond pas au visiteur ;
- la description du lien partagé et l'image `apercu.png`, arrondies à la centaine (« plus de 9 200 membres ») : elles restent justes même quand Discord garde un ancien aperçu en mémoire. L'image n'est redessinée que quand la centaine change.

Pour lancer la mise à jour tout de suite : onglet **Actions** du dépôt → **Nombre de membres** → **Run workflow**. En local : `node outils/membres.js` (ou `node outils/membres.js 9300` pour un nombre précis, `--image` pour redessiner l'image), avec Playwright installé.

## Le classement des grains

La section « Les plus riches du café » (`#classement`) affiche le top 10 des membres par grains (en poche et en banque), avec leur pseudo et leur avatar Discord. Elle reste cachée tant qu'aucun classement n'a été publié.

**Fonctionnement, sans risque pour l'économie du serveur :**

- Toutes les heures, GitHub Actions (`.github/workflows/classement.yml`) lance `outils/classement.py`. Il lit le top 10 dans la table `users` de la base du bot (cumul des colonnes `grains` et `banque`), **en lecture seule**, sans les membres privés de grains (`blacklistGrains`).
- Il récupère le pseudo et l'avatar de chacun sur Discord, puis publie `classement.json` (rang, pseudo, avatar, grains) sur la branche `data` du dépôt.
- Il relève aussi le **classement de #infini** (top 10 de la colonne `infiniStats`, le nombre de nombres postés par chaque membre) et le total de la suite. Sur le site, un onglet « #infini » apparaît à côté de « Grains » dès que ce classement est publié.
- Un onglet **Série** (colonne `streak` de `users`, la série de `/journalier`, en jours). Un onglet n'apparaît que si son classement est publié. (Pas de classement du temps en vocal : la table `gains_vocal_minutes` ne garde que les minutes en cours avant le prochain gain.)
- **Flèches de progression** (▲ places gagnées, ▼ perdues, « Nouveau ») depuis la veille, et **champion de la semaine** (la plus forte hausse de fortune sur 7 jours). Elles reposent sur `historique.json` (`outils/historique.py`) : une photo par jour de chaque classement, gardée 9 jours sur la branche `data`, jamais publiée sur le site. Comme le dépôt peut être public, les membres n'y figurent que sous un identifiant haché (HMAC dont la clé vient du secret `CAFE_DB_URL`). Les flèches apparaissent le lendemain de la mise en place, le champion dès qu'il y a un jour d'écart (« la plus forte hausse ») et prend son titre de « champion de la semaine » au bout de 7 jours.
- **Chiffres de l'économie** sous le titre : grains en circulation (et leur évolution sur la semaine), part en banque, nombre de membres qui ont des grains.
- **Postes ouverts** : la table `recrutement` (colonne `ouvert`) alimente le bandeau « On recrute » de la section Équipe.
- Le site ne lit que ce fichier. **Les identifiants de la base ne sont jamais dans le site** : ils sont rangés dans les secrets du dépôt, que seul GitHub Actions peut lire.

**Secrets à ajouter** (dépôt → Settings → Secrets and variables → Actions → New repository secret) :

| Nom | Valeur |
|---|---|
| `CAFE_DB_URL` | `jdbc:mysql://utilisateur:motdepasse@hôte:3306/base` (même format que l'adresse donnée par le développeur du bot ; dans le mot de passe, `=` s'écrit `%3D`, `@` s'écrit `%40`) |
| `DISCORD_TOKEN` | le jeton d'un bot Discord créé pour l'occasion, **sans aucune permission** et sans l'inviter sur le serveur (discord.com/developers/applications → New Application → Bot → Reset Token) |

L'idéal est un utilisateur de base de données qui n'a que le droit de lecture (SELECT) sur la table `users`. Ne jamais publier ces valeurs dans le code, sur Discord ou ailleurs : si elles ont circulé, change le mot de passe de la base.

Pour lancer le relevé tout de suite : onglet **Actions** → **Classement des grains** → **Run workflow**. Le résumé de l'exécution indique si le classement est publié, ou pourquoi il ne l'est pas (secrets absents, base injoignable).

### Le livre d'or des records

Sous les classements, un livre d'or à feuilleter (couverture en cuir, pages qui tournent, une page par record ; une seule page à la fois sur téléphone) :

- **Records du moment** : la plus grande fortune, la plus forte hausse, la plus longue série de `/journalier`, le pilier de #infini, la plus belle collection DeckFR et les premiers à trouver les cartes bonus. Ils viennent de `classement.json` et `deckfr.json`.
- **Records de tous les temps** : le tout premier booster, la première Mythique, le plus de boosters, la plus grosse ouverture, le plus de Mythiques, le plus beau booster, la vente la plus chère au marché, les cartes la plus rare et la plus tirée. Chaque heure, avec le classement, `outils/records.py` les lit dans la base du bot (**en lecture seule**, mêmes secrets) et publie `records.json` sur la branche `data`. Les membres privés de cartes (`blacklistCartes`) n'y figurent jamais, et seuls le pseudo et l'avatar sont publiés.
- Un record sans donnée n'a pas de page ; le livre reste caché tant qu'il n'a pas au moins trois records.

## Les prochains événements

La section « Les prochains événements » (`#prochains`) montre les événements programmés dans l'onglet « Événements » du serveur Discord : date, heure, lieu, description, nombre d'intéressés et image de couverture. Elle reste cachée quand aucun événement n'est à venir, et un événement disparaît du site dès qu'il est terminé.

- Toutes les 2 heures, GitHub Actions (`.github/workflows/evenements.yml`) lance `outils/evenements.py`, qui lit les événements sur Discord et publie `evenements.json` sur la branche `evenements` du dépôt. Le site ne lit que ce fichier.
- Il utilise le secret `DISCORD_TOKEN` du classement. Pour voir les événements, **ce bot doit être membre du serveur** : invite-le sans aucune permission avec `https://discord.com/oauth2/authorize?client_id=<ID de l'application>&scope=bot&permissions=0` (l'ID est dans discord.com/developers/applications → l'application → General Information). Pour utiliser un autre bot déjà présent sur le serveur, mets son jeton dans un secret `DISCORD_TOKEN_EVENEMENTS`.

Pour lancer le relevé tout de suite : onglet **Actions** → **Prochains événements** → **Run workflow**. Le résumé indique combien d'événements sont publiés, ou pourquoi rien ne l'est (bot absent du serveur, secret manquant).

## DeckFR

La section « DeckFR » (`#deckfr`) présente le jeu de cartes du bot : ses trois salons, les sept raretés, les étapes du jeu (boosters gratuits et achetés, collection, garantie pour les cartes légendaires et mythiques, échanges et ventes au marché) et, dès qu'elles sont publiées, ses données en direct : nombre de cartes de chaque rareté et part réelle dans les tirages, chiffres du jeu (joueurs, boosters ouverts, cartes tirées, échanges, ventes), derniers grands tirages et dernières cartes sorties. En bas, « Toutes les cartes » montre tout le catalogue, les plus rares d'abord, avec un filtre par rareté, une recherche par nom et 24 cartes à la fois ; un clic retourne une carte pour voir son verso. Les classements gagnent un onglet « DeckFR » (les plus grandes collections, en cartes différentes).

- Toutes les heures, avec le classement, `outils/deckfr.py` lit les tables `cartes_*` de la base du bot, **en lecture seule**, et publie `deckfr.json` sur la branche `data`. Les membres privés de cartes (`users.blacklistCartes`) n'apparaissent dans aucune liste. Mêmes secrets que le classement.
- Les **noms des raretés**, du niveau 1 au niveau 7, sont dans `index.html` (`const RARETES = ['Commun', 'Rare', 'Épique', 'Légendaire', 'Mythique', 'Mystère', 'Spécial']`), comme dans le fichier des cartes du bot ; Mystère et Spécial sont des raretés bonus (`const BONUS`), présentées à part des taux de tirage. Leurs couleurs sont `--rar-1` à `--rar-7`. L'éventail de la section montre une vraie carte par rareté (`cartes/vitrine/`).
- **Faux booster** : sous les raretés, « Ouvre un booster pour de faux » tire 5 cartes avec les vrais taux de tirage (`deckfr.json`) et les vraies cartes (`cartes/catalogue.json`), avec une animation d'ouverture. Rien n'est enregistré. La carte secrète de la chasse au trésor n'en sort jamais.
- **Livraison de nouvelles cartes** : un décompte (caisse en bois et étiquette) annonce la prochaine livraison. Pour la suivante, change la date (`ARRIVEE`, heure de Paris) dans le script `livraison()` et le nombre, le thème et les raretés dans le HTML (`#dk-livraison`) ; le bloc disparaît tout seul une semaine après l'arrivée.
- **Chasse au trésor (« Le One Piece du Café Français »)** : la Mascotte d'Or (rareté Spécial) est cachée dans les boosters, et le premier qui la tire gagne 5 Nitro Boosts. Le site l'annonce avec un avis de recherche sur la page Événements et un bandeau sur la page DeckFR. Tant que la carte n'est pas révélée, seules ses images floutées sont publiées (`cartes/la-mascotte-recto-floue.webp` et `-verso-floue.webp`) et elle ne se retourne pas. Le relevé (`outils/deckfr.py`) donne dans `tresors` le premier membre à avoir tiré chaque carte bonus : dès qu'elle est tirée, le site affiche « Trouvée par … » ; l'avis et le bandeau disparaissent une semaine après. Pour la dévoiler, remets ses images nettes dans `cartes/` (elles sont dans l'historique du dépôt) et passe `revele: true` dans `const TRESOR` (`index.html`).
- **Images des cartes** : elles viennent du fichier des cartes du bot (`cartes.zip`) et sont dans le dossier **`cartes/`**, publié avec le site : `<nom>-recto.webp` et `<nom>-verso.webp`, où `<nom>` est le nom de la carte sans accents ni signes (« Aliénor d'Aquitaine » → `alienor-d-aquitaine`). Le site retrouve l'image d'une carte à partir de son nom. `cartes/catalogue.json` (tiré du `cartes.json` du même fichier) liste toutes les cartes et les raretés pour la galerie. Pour de nouvelles cartes, dépose leurs deux images dans `cartes/` et remets `catalogue.json` à jour depuis le nouveau fichier du bot. Une image absente est remplacée par la tasse du café.
- Couleurs des raretés, reprises des cartes du bot : variables `--rar-1` à `--rar-5` en haut de `index.html` (commun argent, rare bleu, épique violet, légendaire or, mythique rose avec un dégradé arc-en-ciel `--holo`).

## Les salons lus sur Discord

Toutes les 2 heures, avec les événements, `outils/salons.py` lit les salons des trois catégories de la visite (Café Français, Centre de Convivialité, Divertissements) et publie `salons.json` sur la branche `evenements`. Le site met alors à jour tout seul la liste de chaque salle (nom, emoji, type, sujet du salon), les compteurs et le total de l'ouverture. Un salon ajouté, renommé ou supprimé sur Discord l'est aussi sur le site.

- Seuls les salons que voit un simple membre sont publiés (droits de @everyone) : les salons du staff n'apparaissent jamais. `couleurs` et `discussion-vip`, réservés à un rôle, sont montrés avec un cadenas (liste `PRIVES_AFFICHES` du script).
- Si le serveur cache tout à @everyone jusqu'à l'obtention d'un rôle, ajoute une variable de dépôt `ROLE_MEMBRE` (Settings → Secrets and variables → Actions → Variables) avec l'identifiant de ce rôle.
- Comme pour les événements, **le bot du secret `DISCORD_TOKEN` doit être membre du serveur** (invitation sans permission, voir « Les prochains événements »). Tant qu'il ne l'est pas, rien n'est publié et le site garde les salons écrits dans le HTML.

## La petite info du jour

La section « Quoi de neuf en France ? » (`#info`) affiche une info sur l'actualité en France, sous forme de gazette. Une nouvelle info paraît chaque jour à midi, et les quatre précédentes sont listées dessous.

Les infos sont dans **`infos.json`**, de la plus récente à la plus ancienne :

```json
{
  "infos": [
    {
      "date": "2026-10-20",
      "publication": "2026-10-20T12:00:00+02:00",
      "theme": "Société",
      "titre": "Titre court",
      "texte": "Deux ou trois phrases factuelles.",
      "source": { "nom": "franceinfo", "url": "https://www.franceinfo.fr/..." }
    }
  ]
}
```

- Une info ne s'affiche qu'à partir de son heure de `publication` : elle peut être ajoutée le matin et paraître à midi pile.
- La page ne fait que lire ce fichier : il n'y a rien à envoyer, donc rien à pirater depuis le site.
- Les textes sont affichés tels quels, sans HTML ; la typographie française (espaces avant `? ! : ;`) est ajoutée par la page. Les liens de source doivent commencer par `https://`.

**Mise à jour automatique.** Chaque jour vers 11 h 15, une tâche planifiée de Claude Code (session « Info du jour du Café ») cherche l'actualité du jour, vérifie les faits sur plusieurs sources, ajoute l'info en tête de `infos.json` avec une publication à midi, puis la publie sur `main`. Le fichier garde les 30 dernières infos.

**Règles pour les sources** (droit d'auteur et droit voisin des éditeurs de presse) :

- Les faits sont libres, mais pas la façon dont un média les raconte : chaque info est écrite avec nos propres mots, sans recopier de phrase ni d'expression d'un article. Une déclaration peut être citée en quelques mots entre guillemets, avec son auteur.
- Jamais de photo, de vidéo, de logo ou d'extrait long d'un média : seulement le nom de la source et un lien vers l'article (les liens vers des pages en accès libre sont autorisés : arrêt Svensson de la CJUE, article L. 211-3-1 du Code de la propriété intellectuelle).
- Uniquement des articles en accès libre : pas d'article réservé aux abonnés. De préférence, les médias publics (franceinfo, France 24) ou les sites officiels (.gouv.fr, INSEE, Météo-France).

**Annonce sur Discord.** À midi pile (heure de Paris), une tâche Cloudflare (dossier `annonce/`, installée par `.github/workflows/annonce-cloudflare.yml`) poste l'info du jour dans un salon du serveur, sous forme d'embed (titre, texte, thème, source, lien vers le site), sans aucune mention (@everyone, rôles). Elle passe par Cloudflare parce que GitHub lance ses tâches programmées avec parfois une heure de retard. La clé Cloudflare doit avoir l'autorisation « Workers Scripts : Edit ». GitHub garde un lancement manuel (`.github/workflows/annonce-info.yml`, `outils/annonce_info.py`) pour tester ou rattraper une info publiée après midi. Pour l'activer :

1. Dans Discord : Paramètres du salon choisi → Intégrations → Webhooks → Nouveau webhook ; nomme-le « La Gazette du Café », mets-lui l'avatar voulu, puis « Copier l'URL du webhook ».
2. Dans GitHub : Settings → Secrets and variables → Actions → New repository secret, nom `DISCORD_WEBHOOK_INFO`, valeur : l'URL copiée.
3. Pour essayer à tout moment : onglet Actions → « Annonce de l'info du jour » → Run workflow, coche « Test », puis Run workflow. La dernière info publiée est envoyée, marquée « Test », sans changer l'annonce de midi.
4. Si une info est publiée après midi (tâche du jour en retard), lance « Annonce de l'info du jour » sans cocher « Test » pour l'envoyer.

Toutes les infos publiées (jusqu'à 30) sont aussi sur la page **`/infos/`** (fichier `infos/index.html`), classées par mois et filtrables par thème ; le lien « Toutes les éditions » y mène depuis l'accueil.

Pour corriger ou retirer une info : modifie ou supprime son bloc dans `infos.json` (en gardant un JSON valide), puis publie.

## Saisons

Le site change de tenue selon la saison, réglée tout en haut de `index.html` :

```js
var SAISON = 'auto';
```

- `'auto'` : suit l'heure de Paris. Halloween en octobre, **Noël du 1er décembre à 00 h au 6 janvier inclus**, version normale le reste de l'année. La page change de tenue à minuit pile, même si un visiteur l'a déjà ouverte (avec un petit message « Joyeux Noël ! »). Il n'y a rien à publier ce jour-là.
- `'halloween'`, `'noel'` ou `'normal'` : force une version.

En version normale, la section Halloween est remplacée par une section « Événements », le lien du menu change et les salons reprennent leurs emojis habituels.

**Version Noël** : section « Noël au café » (`#noel`) avec un compte à rebours jusqu'au 25 décembre (puis « Joyeux Noël ! » et « Bonne année » en janvier) et un calendrier de l'Avent : une case par jour, ouverte à minuit (heure de Paris), avec une tradition de Noël. Les textes des cases sont encodés dans `data-c`, comme les quêtes d'Halloween (même commande, avec `{ e: "emoji", t: "titre", x: "texte" }`). Il y a aussi de la neige (coupée par l'interrupteur « Animations »), une guirlande sous la barre, une couronne et la pancarte « Joyeux Noël » sur la porte, les emojis de Noël des salons (`<span class="seulement-noel">`), et les chants de Noël dans l'ambiance.

Le site suit la DA de Noël du serveur : un fond qui va du bordeaux au vert sapin (les couleurs `--nuit`, `--nuit-2`, `--trait` changent en Noël), la tasse du logo coiffée d'un bonnet (`#p-bonnet`, ajouté partout où la tasse apparaît avec `<use class="bonnet seulement-noel">`), des bouquets de branches de sapin avec boules rouges, petites lumières dorées et ruban crème dans les coins de l'ouverture, de la section Noël et de la porte d'entrée (`<div class="deco-noel" data-deco="…">`, dessinés par le script « décors de Noël »), des flocons en cristal, une couronne de sapin sur la porte, une guirlande de lumières dorées sous la barre, et l'icône de l'onglet avec le bonnet sur le dégradé de la DA.

Pour voir une version sans rien changer, ajoute `#saison-halloween`, `#saison-noel` ou `#saison-normale` à la fin de l'adresse du site.

## Référencement et page d'erreur

- `robots.txt` autorise tous les robots et indique `sitemap.xml`, la liste des pages du site (accueil, les huit pages, `/infos/`, CGU, mentions légales). Si une page s'ajoute, ajoute-la au sitemap.
- En haut de `index.html`, un bloc `application/ld+json` décrit le site et la communauté pour les moteurs de recherche (nom, description, lien Discord).
- `404.html` s'affiche pour toute adresse inexistante (GitHub Pages comme Cloudflare Pages) ; ses liens sont absolus (`/polices/…`, `/`).

## Aperçu des liens partagés

Quand le lien du site est posté sur Discord ou ailleurs, l'image `apercu.png` s'affiche avec le titre et la description. L'image est dessinée par `outils/membres.js` (logo de la page, lettres du fond, nombre de membres) : pour changer sa mise en page, modifie ce script puis lance `node outils/membres.js --image`. Les balises `og:` et `canonical` en haut de `index.html` utilisent l'adresse `https://cafe-fr.com/` ; `outils/pages.py` les adapte pour chaque page (titre, description, adresse), et la page les met à jour quand on change de page. Si le domaine change, remplace-la à ces endroits et dans le fichier `CNAME`.

## Mise en ligne : Cloudflare Pages (dépôt privé possible)

Le site est publié sur **Cloudflare Pages** (projet `cafe-fr`) par GitHub Actions (`.github/workflows/publier.yml`) : à chaque push sur `main`, et après chaque relevé du classement, des événements et du nombre de membres. Seuls les fichiers du site partent en ligne (`index.html`, `404.html`, `robots.txt`, `sitemap.xml`, `infos.json`, `apercu.png`, `cgu/`, `mentions-legales/`, `infos/`, `polices/`, `js/`, et une copie de `index.html` par page faite par `outils/pages.py`), avec `classement.json` et `evenements.json` pris sur les branches `data` et `evenements`. Le README, `outils/` et `.github/` ne sont jamais publiés, et le site n'a plus besoin que le dépôt soit public : **le dépôt peut passer en privé**.

Le site lit le classement et les événements à sa propre adresse (`classement.json`, `evenements.json`) ; s'ils n'y sont pas (ancien hébergement GitHub Pages), il les lit sur le dépôt.

**Mise en place (une seule fois)**

1. **Compte Cloudflare** : crée un compte gratuit sur [dash.cloudflare.com](https://dash.cloudflare.com). L'identifiant du compte (*Account ID*) s'affiche dans la colonne de droite de la page d'accueil d'un domaine, ou dans l'adresse du tableau de bord (`dash.cloudflare.com/<Account ID>`).
2. **Jeton d'API** : Mon profil → Jetons d'API → Créer un jeton → « Créer un jeton personnalisé », avec la permission **Compte → Cloudflare Pages → Modifier**.
3. **Secrets GitHub** (Settings → Secrets and variables → Actions → New repository secret) : `CLOUDFLARE_API_TOKEN` (le jeton) et `CLOUDFLARE_ACCOUNT_ID` (l'identifiant du compte).
4. **Première publication** : onglet Actions → « Publier le site » → Run workflow. Le projet `cafe-fr` est créé tout seul ; le site est alors visible sur `https://cafe-fr.pages.dev`. Vérifie qu'il s'affiche bien.
5. **Domaine cafe-fr.com** : dans Cloudflare, ajoute le domaine (Ajouter un domaine → `cafe-fr.com` → offre gratuite). Cloudflare donne deux serveurs de noms : dans **hPanel** de Hostinger (Domaines → cafe-fr.com → DNS / Serveurs de noms → Changer les serveurs de noms), remplace ceux de Hostinger par ceux de Cloudflare. Le changement peut prendre de quelques minutes à 24 h ; Cloudflare envoie un e-mail quand le domaine est actif. Recopie d'abord dans Cloudflare les autres enregistrements DNS éventuels (e-mails, MX…) que tu utilises chez Hostinger.
6. **Brancher le domaine sur le site** : Workers & Pages → `cafe-fr` → Domaines personnalisés → ajoute `cafe-fr.com`, puis `www.cafe-fr.com`. Cloudflare crée les enregistrements et le certificat HTTPS tout seul.
7. **Passer le dépôt en privé** : une fois `https://cafe-fr.com` servi par Cloudflare, GitHub → Settings → General → Danger Zone → Change visibility → Private. GitHub Pages s'arrête alors, ce qui n'a plus d'importance. Les tâches planifiées (classement, événements, membres) continuent : sur un dépôt privé, GitHub Actions offre 2 000 minutes par mois, largement assez.

Le fichier `CNAME` ne servait qu'à GitHub Pages ; il peut rester.

## Modifier le contenu

Tout se modifie dans `index.html` :

- **Nombre de membres** : mis à jour tout seul chaque jour (voir « Nombre de membres à jour »), rien à modifier à la main.
- **Salons et emojis** : chaque salon est une ligne `<li class="salon">`, dans l'ordre du serveur. Son emoji habituel est dans `<span class="seulement-normal">`, celui d'Halloween dans `<span class="seulement-halloween">`, celui de Noël dans `<span class="seulement-noel">`. Une fois les salons lus sur Discord (voir « Les salons lus sur Discord »), la liste se met à jour toute seule ; le HTML sert de secours. Les salons privés (cadenas) utilisent l'icône `#i-texte-prive`, les salons d'annonces `#i-annonce` et les forums `#i-forum`. Pense à mettre à jour le nombre de salons de la catégorie (`salle-compte`) et le total de l'ouverture.
- **Salons vocaux** : chaque ligne `<li class="vocal">` porte le nom exact du salon dans `data-vocal` (il sert à retrouver le salon dans le widget) et sa limite de places dans `data-max`.
- **Équipe** : chaque profil est une ligne `<li class="profil">` dans la liste du badge (`<ul class="profils">`). Pour ajouter quelqu'un, copie une ligne et change le nom, le pseudo et l'image (`src`, une adresse d'image ou une image intégrée).
  - **Fiches au dos des badges** : ajoute à un profil `data-mot="Son rôle en une phrase."`, `data-depuis="avril 2021"` (affiché « Depuis avril 2021 ») et/ou `data-boisson="Un petit noir"`. Dès qu'un profil du badge en a, un bouton ↻ apparaît sur le badge et le retourne pour montrer ces fiches.
  - **Présence** : une pastille verte, orange ou rouge s'affiche sur l'avatar quand le widget Discord liste le membre en ligne, absent ou en « ne pas déranger ». Le widget ne liste qu'une partie des connectés : aucune pastille ne veut pas dire hors ligne. La correspondance se fait par le nom affiché et le pseudo du profil.
  - Sur mobile, les badges défilent en carrousel (points sous les badges).
- **Quêtes d'Halloween** : chaque quête est une ligne `<li class="quete">`. Sa date d'ouverture est dans `data-ouverture` (heure de Paris). Jusqu'à cette heure, la carte affiche `???` ; à l'ouverture, la page affiche toute seule le nom et la consigne de la quête, même si le visiteur est déjà sur le site. Ces textes sont rangés, encodés, dans `data-q` pour ne pas être lisibles dans le code de la page. Pour en changer un, ouvre la console du navigateur sur le site et tape :

  ```js
  btoa(String.fromCharCode(...new TextEncoder().encode(JSON.stringify({ nom: "Mots croisés", consigne: "Remplis la grille de **mots croisés**." }))))
  ```

  puis colle le résultat dans `data-q`. Les mots entre `**` s'affichent en gras.
- **Niveaux et grains** : les paliers sont les lignes `<li class="palier">`, leurs avantages sont dans `<ul class="p-avantages">`. Les bonus de grains du calculateur sont dans le formulaire `#calcul`.
- **Boutique** : chaque article est une ligne `<li class="article">`. Son prix est à la fois dans `data-prix` (sans espaces, il sert au calcul du temps de vocal) et dans le texte affiché.
- **Après Halloween** : supprime la section `<section class="halloween">` et le lien « Halloween » de la barre de navigation.
