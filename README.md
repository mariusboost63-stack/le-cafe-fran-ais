# Le Café Français

Site vitrine animé du serveur Discord francophone **Le Café Français** : [discord.gg/france](https://discord.gg/france).

Tout tient dans un seul fichier, `index.html` (HTML, CSS et JavaScript). Les animations utilisent [GSAP](https://gsap.com) et ScrollTrigger, chargés depuis cdnjs.

## Ce que contient la page

- L'ouverture, avec le logo vectorisé qui se compose (tasse, vapeur tricolore, lettres).
- Un ruban « Bonjour, Salut, Coucou… » dont la vitesse suit le défilement.
- La visite des salles en défilement horizontal bleu, blanc, rouge : le comptoir (Café Français), la terrasse (Centre de Convivialité) et l'arrière-salle (Divertissements), avec la description des salons.
- Le système de niveaux : un compteur grimpe de palier en palier, de @Curieux (niveau 2) à @Légende (niveau 100).
- L'événement Halloween 2026 : compte à rebours en direct jusqu'à la prochaine quête, calendrier des 7 quêtes et barème des citrouilles.
- Les salons vocaux, puis le calculateur de grains (5 000 grains toutes les 10 minutes, avec les bonus de rôle).
- L'équipe, présentée sur des badges suspendus : Gérants, Administrateurs, Responsables, et le reste de l'équipe sur le Discord.
- Trois étapes pour rejoindre le serveur, une tasse qui se remplit en bas de page et les moyens de soutenir le café.

## Données en direct

La page lit le widget public du serveur :

```
https://discord.com/api/guilds/829698572927762432/widget.json
```

Une fois le site en ligne, elle affiche le nombre de membres connectés, l'occupation de chaque salon vocal et les avatars des personnes en ligne. Le widget doit rester activé dans les paramètres du serveur (Paramètres du serveur → Widget). Si le widget ne répond pas, la page garde les valeurs écrites dans le HTML.

## Mettre en ligne avec GitHub Pages

1. Dans le dépôt, ouvre **Settings → Pages**.
2. Dans **Source**, choisis **Deploy from a branch**, puis la branche `main` et le dossier `/ (root)`.
3. Enregistre. Le site est publié en une minute environ, à l'adresse `https://<ton-pseudo>.github.io/<nom-du-depot>/`.

## Modifier le contenu

Tout se modifie dans `index.html` :

- **Nombre de membres** : cherche `9212` (il apparaît dans l'ouverture, dans `data-valeur` et dans le compteur JavaScript) et `9&#8239;212` (le texte affiché).
- **Salons et emojis** : chaque salon est une ligne `<li class="salon">`. Les emojis actuels sont ceux de la saison d'Halloween.
- **Salons vocaux** : chaque ligne `<li class="vocal">` porte le nom exact du salon dans `data-vocal` (il sert à retrouver le salon dans le widget) et sa limite de places dans `data-max`.
- **Équipe** : au début du script, remplis l'objet `EQUIPE`. Un membre par ligne, par exemple `{ pseudo: 'Pseudo', avatar: 'https://cdn.discordapp.com/avatars/…' }`. L'avatar est facultatif. Les noms apparaissent sur le badge du poste.
- **Quêtes d'Halloween** : chaque quête est une ligne `<li class="quete">`. Sa date d'ouverture est dans `data-ouverture` (heure de Paris). Quand une quête est révélée, remplace `???` par son titre.
- **Niveaux et grains** : les paliers sont les lignes `<li class="palier">`, les bonus de grains sont dans le formulaire `#calcul`.
- **Après Halloween** : supprime la section `<section class="halloween">` et le lien « Halloween » de la barre de navigation.
