# Le Café Français

Site vitrine animé du serveur Discord francophone **Le Café Français** : [discord.gg/france](https://discord.gg/france).

Tout tient dans un seul fichier, `index.html` (HTML, CSS et JavaScript). Les animations utilisent [GSAP](https://gsap.com) et ScrollTrigger, chargés depuis cdnjs.

## Ce que contient la page

- L'ouverture, avec le logo vectorisé qui se compose (tasse, vapeur tricolore, lettres).
- Un ruban « Bonjour, Salut, Coucou… » dont la vitesse suit le défilement.
- La visite des salles en défilement horizontal bleu, blanc, rouge : le comptoir (Café Français), la terrasse (Centre de Convivialité) et l'arrière-salle (Divertissements), avec la description de chaque salon.
- Le système de niveaux : un compteur grimpe de palier en palier, de @Curieux (niveau 2) à @Légende (niveau 100), et affiche les avantages débloqués (couleurs de pseudo, bonus de grains, virements).
- L'événement Halloween 2026 : compte à rebours en direct jusqu'à la prochaine quête, calendrier des 7 quêtes, barème des citrouilles, récompenses et rôles à gagner.
- Les grains : toutes les façons d'en gagner (vocal, /journalier, /hebdomadaire, casino, /voler), un calculateur de gains en vocal et la boutique, avec le temps de vocal nécessaire pour chaque article.
- Les salons vocaux et leurs limites de places.
- L'équipe, présentée sur des badges suspendus avec les profils de chacun : Gérants, Administrateurs, Responsables, et le reste de l'équipe sur le Discord.
- Trois étapes pour rejoindre le serveur, une FAQ, une tasse qui se remplit en bas de page et les moyens de soutenir le café.
- À la première visite, l'entrée « Pousser la porte » : la devanture du café s'ouvre avec un tintement de clochette. Le bouton « Repasser la porte », dans le pied de page, la fait revenir.
- « Commande ton café » : quatre questions qui révèlent la boisson et la table du café faites pour le visiteur, avec ses salons conseillés.
- « Attrape les grains » : un mini-jeu de 45 secondes, avec un record gardé sur l'appareil.
- Un bouton « Ambiance » qui joue un fond sonore de café, créé directement dans la page (aucun fichier audio).
- Des surprises : cliquer sur la tasse du logo la remplit, taper « café » au clavier fait pleuvoir des grains, taper « boo » lâche des chauves-souris.

## Données en direct

La page lit le widget public du serveur :

```
https://discord.com/api/guilds/829698572927762432/widget.json
```

Une fois le site en ligne, elle affiche le nombre de membres connectés, l'occupation de chaque salon vocal et les avatars des personnes en ligne. Le widget doit rester activé dans les paramètres du serveur (Paramètres du serveur → Widget). Si le widget ne répond pas, la page garde les valeurs écrites dans le HTML.

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

Quand le lien du site est posté sur Discord ou ailleurs, l'image `apercu.png` s'affiche avec le titre et la description. Les adresses utilisées sont celles de GitHub Pages (`https://mariusboost63-stack.github.io/le-cafe-fran-ais/`). Si tu passes à un nom de domaine, remplace cette adresse dans les balises `og:` et `canonical` en haut de `index.html`.

## Mettre en ligne avec GitHub Pages

1. Dans le dépôt, ouvre **Settings → Pages**.
2. Dans **Source**, choisis **Deploy from a branch**, puis la branche `main` et le dossier `/ (root)`.
3. Enregistre. Le site est publié en une minute environ, à l'adresse `https://<ton-pseudo>.github.io/<nom-du-depot>/`.

## Modifier le contenu

Tout se modifie dans `index.html` :

- **Nombre de membres** : cherche `9212` (il apparaît dans l'ouverture, dans `data-valeur` et dans le compteur JavaScript) et `9&#8239;212` (le texte affiché).
- **Salons et emojis** : chaque salon est une ligne `<li class="salon">`. Les emojis actuels sont ceux de la saison d'Halloween.
- **Salons vocaux** : chaque ligne `<li class="vocal">` porte le nom exact du salon dans `data-vocal` (il sert à retrouver le salon dans le widget) et sa limite de places dans `data-max`.
- **Équipe** : chaque profil est une ligne `<li class="profil">` dans la liste du badge (`<ul class="profils">`). Pour ajouter quelqu'un, copie une ligne et change le nom, le pseudo et l'image (`src`, une adresse d'image ou une image intégrée).
- **Quêtes d'Halloween** : chaque quête est une ligne `<li class="quete">`. Sa date d'ouverture est dans `data-ouverture` (heure de Paris). Quand une quête est révélée, remplace `???` par son titre.
- **Niveaux et grains** : les paliers sont les lignes `<li class="palier">`, leurs avantages sont dans `<ul class="p-avantages">`. Les bonus de grains du calculateur sont dans le formulaire `#calcul`.
- **Boutique** : chaque article est une ligne `<li class="article">`. Son prix est à la fois dans `data-prix` (sans espaces, il sert au calcul du temps de vocal) et dans le texte affiché.
- **Après Halloween** : supprime la section `<section class="halloween">` et le lien « Halloween » de la barre de navigation.
