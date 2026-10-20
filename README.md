# Le Café Français

Site vitrine animé du serveur Discord francophone **Le Café Français** : [discord.gg/france](https://discord.gg/france).

En ligne sur **[cafe-fr.com](https://cafe-fr.com)**, hébergé sur GitHub Pages avec le domaine `cafe-fr.com` (fichier `CNAME`). Chaque modification poussée sur la branche `main` est publiée automatiquement.

Tout tient dans un seul fichier, `index.html` (HTML, CSS et JavaScript). Les animations utilisent [GSAP](https://gsap.com) et ScrollTrigger, chargés depuis cdnjs.

## Ce que contient la page

- L'ouverture, avec le logo vectorisé qui se compose (tasse, vapeur tricolore, lettres).
- Un ruban « Bonjour, Salut, Coucou… » dont la vitesse suit le défilement.
- La visite des salles en défilement horizontal bleu, blanc, rouge : le comptoir (Café Français), la terrasse (Centre de Convivialité) et l'arrière-salle (Divertissements), avec la description de chaque salon.
- Le système de niveaux : un compteur grimpe de palier en palier, de @Curieux (niveau 2) à @Légende (niveau 100), et affiche les avantages débloqués (couleurs de pseudo, bonus de grains, virements).
- L'événement Halloween 2026 : compte à rebours en direct jusqu'à la prochaine quête, lien vers le salon #les-quêtes (`https://discord.com/channels/829698572927762432/1560700305631481959`, s'ouvre pour les membres du serveur), calendrier des 7 quêtes, barème des citrouilles, récompenses et rôles à gagner.
- Les grains : toutes les façons d'en gagner (vocal, messages, /journalier, /hebdomadaire, casino, /voler), un calculateur de gains en vocal et la boutique, avec le temps de vocal nécessaire pour chaque article.
- Les salons vocaux et leurs limites de places.
- L'équipe, présentée sur des badges suspendus avec les profils de chacun : Gérants, Administrateurs, Responsables, et le reste de l'équipe sur le Discord.
- Trois étapes pour rejoindre le serveur, une FAQ, une tasse qui se remplit en bas de page et les moyens de soutenir le café.
- À la première visite, l'entrée « Pousser la porte » : la devanture du café s'ouvre avec un tintement de clochette. Le bouton « Repasser la porte », dans le pied de page, la fait revenir.
- « Commande ton café » : quatre questions qui révèlent la boisson et la table du café faites pour le visiteur, avec ses salons conseillés.
- Un bouton « Ambiance » qui joue un fond sonore de café, créé directement dans la page (aucun fichier audio).
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

Pour corriger ou retirer une info : modifie ou supprime son bloc dans `infos.json` (en gardant un JSON valide), puis publie.

## Saisons

Le site change de tenue selon la saison, réglée tout en haut de `index.html` :

```js
var SAISON = 'auto';
```

- `'auto'` : version Halloween en octobre, version normale le reste de l'année. Le changement se fait tout seul le 1er novembre.
- `'halloween'` ou `'normal'` : force une version.

En version normale, la section Halloween est remplacée par une section « Événements », le lien du menu change, le compteur passe à 28 salons et les emojis d'Halloween des salons sont masqués.

Pour voir une version sans rien changer, ajoute `#saison-halloween` ou `#saison-normale` à la fin de l'adresse du site.

## Aperçu des liens partagés

Quand le lien du site est posté sur Discord ou ailleurs, l'image `apercu.png` s'affiche avec le titre et la description. L'image est dessinée par `outils/membres.js` (logo de la page, lettres du fond, nombre de membres) : pour changer sa mise en page, modifie ce script puis lance `node outils/membres.js --image`. Les balises `og:` et `canonical` en haut de `index.html` utilisent l'adresse `https://cafe-fr.com/`. Si le domaine change, remplace-la à ces endroits et dans le fichier `CNAME`.

## Mise en ligne : GitHub Pages et le domaine cafe-fr.com

Le domaine est chez Hostinger, le site est servi par GitHub Pages.

**Dans hPanel** (Domaines → cafe-fr.com → DNS / Serveurs de noms → Gérer les enregistrements DNS), on garde les serveurs de noms de Hostinger et on remplace les enregistrements A et AAAA de `@` par ceux de GitHub Pages :

| Type | Nom | Pointe vers |
|---|---|---|
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| AAAA | @ | 2606:50c0:8000::153 |
| AAAA | @ | 2606:50c0:8001::153 |
| AAAA | @ | 2606:50c0:8002::153 |
| AAAA | @ | 2606:50c0:8003::153 |
| CNAME | www | mariusboost63-stack.github.io |

**Dans GitHub** (Settings → Pages du dépôt) : source « Deploy from a branch », branche `main`, dossier `/ (root)`, domaine personnalisé `cafe-fr.com`, puis « Enforce HTTPS » une fois le certificat prêt.

## Modifier le contenu

Tout se modifie dans `index.html` :

- **Nombre de membres** : mis à jour tout seul chaque jour (voir « Nombre de membres à jour »), rien à modifier à la main.
- **Salons et emojis** : chaque salon est une ligne `<li class="salon">`. Les emojis actuels sont ceux de la saison d'Halloween.
- **Salons vocaux** : chaque ligne `<li class="vocal">` porte le nom exact du salon dans `data-vocal` (il sert à retrouver le salon dans le widget) et sa limite de places dans `data-max`.
- **Équipe** : chaque profil est une ligne `<li class="profil">` dans la liste du badge (`<ul class="profils">`). Pour ajouter quelqu'un, copie une ligne et change le nom, le pseudo et l'image (`src`, une adresse d'image ou une image intégrée).
- **Quêtes d'Halloween** : chaque quête est une ligne `<li class="quete">`. Sa date d'ouverture est dans `data-ouverture` (heure de Paris). Jusqu'à cette heure, la carte affiche `???` ; à l'ouverture, la page affiche toute seule le nom et la consigne de la quête, même si le visiteur est déjà sur le site. Ces textes sont rangés, encodés, dans `data-q` pour ne pas être lisibles dans le code de la page. Pour en changer un, ouvre la console du navigateur sur le site et tape :

  ```js
  btoa(String.fromCharCode(...new TextEncoder().encode(JSON.stringify({ nom: "Mots croisés", consigne: "Remplis la grille de **mots croisés**." }))))
  ```

  puis colle le résultat dans `data-q`. Les mots entre `**` s'affichent en gras.
- **Niveaux et grains** : les paliers sont les lignes `<li class="palier">`, leurs avantages sont dans `<ul class="p-avantages">`. Les bonus de grains du calculateur sont dans le formulaire `#calcul`.
- **Boutique** : chaque article est une ligne `<li class="article">`. Son prix est à la fois dans `data-prix` (sans espaces, il sert au calcul du temps de vocal) et dans le texte affiché.
- **Après Halloween** : supprime la section `<section class="halloween">` et le lien « Halloween » de la barre de navigation.
