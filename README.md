# Le Café Français

Site vitrine animé du serveur Discord francophone **Le Café Français** : [discord.gg/france](https://discord.gg/france).

Tout tient dans un seul fichier, `index.html` (HTML, CSS et JavaScript). Les animations utilisent [GSAP](https://gsap.com) et ScrollTrigger, chargés depuis cdnjs.

## Ce que contient la page

- L'ouverture, avec le logo vectorisé qui se compose (tasse, vapeur tricolore, lettres).
- Un ruban « Bonjour, Salut, Coucou… » dont la vitesse suit le défilement.
- La visite des salles en défilement horizontal bleu, blanc, rouge : le comptoir (Café Français), la terrasse (Centre de Convivialité) et l'arrière-salle (Divertissements).
- L'événement Halloween 2026, avec un compte à rebours jusqu'au 31 octobre.
- Les salons vocaux et leurs limites de places.
- Trois étapes pour rejoindre le serveur, puis une tasse qui se remplit en bas de page.

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
- **Après Halloween** : supprime la section `<section class="halloween">` et le lien « Halloween » de la barre de navigation.
