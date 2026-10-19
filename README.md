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
- « Attrape les grains » : un mini-jeu de 45 secondes, avec un record gardé sur l'appareil et un classement de la semaine (voir plus bas). Avant de jouer, le visiteur entre son pseudo Discord ; chaque dimanche à minuit, le n°1 gagne 250 000 grains et le classement repart à zéro.
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

## Classement du mini-jeu

Les scores sont enregistrés dans **Firebase Firestore** (Google, gratuit), projet `cafe-fr`. Chaque joueur reçoit une **identité anonyme** (Firebase Authentication), gardée sur son appareil : son score est rangé sous cette identité et personne d'autre ne peut le modifier.

**Mise en place (une seule fois)**

1. Sur [console.firebase.google.com](https://console.firebase.google.com), crée un projet (Google Analytics n'est pas nécessaire).
2. **Authentication → Commencer → Méthode de connexion → Anonyme** : active-la.
3. **Firestore Database → Créer une base de données**, emplacement européen, mode **production**.
4. Onglet **Règles** de Firestore : remplace tout par les règles ci-dessous, puis **Publier**.
5. **Paramètres du projet → Vos applications → Web (`</>`)** : enregistre une application, puis copie `projectId` et `apiKey`, à renseigner dans `index.html` : `const CLASSEMENT = { projet: '…', cle: '…' };`

La clé `apiKey` d'une application web Firebase n'est pas secrète : ce sont les règles qui protègent les données.

```
rules_version = '2';
service cloud.firestore {
  match /databases/{base}/documents {

    // Partie en cours de chaque joueur : identifiant de la partie et heure de début (fixée par le serveur)
    match /parties/{uid} {
      allow create, update: if request.auth != null && request.auth.uid == uid
        && request.resource.data.keys().hasOnly(['id', 'debut'])
        && request.resource.data.id is string
        && request.resource.data.id.size() >= 8 && request.resource.data.id.size() <= 40
        && request.resource.data.debut == request.time;
    }

    // Joueurs bannis du classement : un document par identité (ID du document de score) ou par pseudo en minuscules.
    // Géré seulement depuis la console Firebase : le site ne peut ni le lire ni l'écrire.
    match /bannis/{id} {
      allow read, write: if false;
    }

    // Classement : une collection par semaine (scores-AAAA-MM-JJ, date du lundi), un document par joueur
    match /{semaine}/{uid} {
      function semaineValide() {
        return semaine.matches('scores-[0-9]{4}-[0-9]{2}-[0-9]{2}');
      }
      // On n'écrit que dans la semaine en cours (du lundi au dimanche, heure de Paris)
      function semaineEnCours() {
        let p = semaine.split('-');
        let lundi = timestamp.date(int(p[1]), int(p[2]), int(p[3]));
        return request.time > lundi - duration.value(2, 'h') && request.time < lundi + duration.value(168, 'h');
      }
      // Ni l'identité ni le pseudo ne doivent être bannis
      function nonBanni(pseudo) {
        return !exists(/databases/$(base)/documents/bannis/$(uid))
          && !exists(/databases/$(base)/documents/bannis/$(pseudo.lower()));
      }
      // Chacun n'écrit que son propre score, après une vraie partie (au moins 40 s, au plus 10 min)
      function scoreValide() {
        let d = request.resource.data;
        let partie = get(/databases/$(base)/documents/parties/$(uid)).data;
        return request.auth != null && request.auth.uid == uid
          && d.keys().hasOnly(['pseudo', 'score', 'maj', 'partie'])
          && d.pseudo is string && d.pseudo.size() >= 2 && d.pseudo.size() <= 24
          && !d.pseudo.matches('.*/.*') && nonBanni(d.pseudo)
          && d.score is int && d.score >= 1 && d.score <= 200
          && d.maj == request.time
          && d.partie == partie.id
          && request.time > partie.debut + duration.value(40, 's')
          && request.time < partie.debut + duration.value(10, 'm');
      }
      allow read: if semaineValide();
      allow create: if semaineValide() && semaineEnCours() && scoreValide();
      allow update: if semaineValide() && semaineEnCours() && scoreValide()
        && request.resource.data.score > resource.data.score
        && request.resource.data.partie != resource.data.partie;
      allow delete: if false;
    }
  }
}
```

**Ce que les règles garantissent**

- Chacun ne peut écrire **que son propre score** (document nommé d'après son identité anonyme).
- Un score n'est accepté qu'**après une vraie partie** : le début de chaque partie est noté par le serveur (collection `parties`), et le score n'est accepté qu'entre 40 secondes et 10 minutes plus tard, une seule fois par partie.
- Le score doit battre le précédent du joueur, et ne pas dépasser **200** : c'est impossible en 45 secondes (en attrapant absolument tout, une partie rapporte au plus 180 environ). Si la durée du jeu change, adapte `SCORE_MAX` dans `index.html` et la limite dans les règles.
- On n'écrit que dans la **semaine en cours** ; personne ne peut supprimer un score depuis le site.
- Un joueur **banni** (par son identité ou son pseudo) ne peut plus enregistrer de score.

**Fonctionnement**

- La semaine va du lundi 0 h au dimanche minuit, heure de Paris. Chaque semaine a sa collection, `scores-2026-10-19` par exemple (date du lundi).
- Le site affiche le top 10 (une ligne par pseudo), la place du joueur s'il est plus loin, et le gagnant de la semaine précédente.
- **Avant de donner les 250 000 grains**, vérifie le gagnant : un tricheur peut encore gonfler *son propre* score (jusqu'à 200), et n'importe qui peut choisir le pseudo d'un autre. Les scores se consultent dans la console Firebase (Firestore → la collection de la semaine) ; un score suspect se supprime depuis la console.

**Bannir un joueur du classement**

Dans la console Firebase, **Firestore Database** :

1. Ouvre la collection de la semaine (`scores-…`) et repère le score du tricheur : l'**ID du document** est son identité, le champ `pseudo` son pseudo.
2. Crée la collection **`bannis`** (la première fois, « Commencer une collection ») et ajoute-y un document dont l'**ID** est :
   - l'**identité** du joueur (l'ID du document copié à l'étape 1) : bloque cet appareil, quel que soit le pseudo utilisé ;
   - et/ou son **pseudo en minuscules** (`toto` pour « Toto ») : bloque ce pseudo sur tous les appareils.
   Mets un champ au choix, par exemple `raison` = `triche`.
3. Supprime son document de score dans la collection de la semaine (les trois points ⋮ → Supprimer le document) : il disparaît du classement.

Pour débannir, supprime le document dans `bannis`. Le site ne peut ni lire ni modifier cette liste.

Limite : l'identité est liée au navigateur. En effaçant les données du site ou en changeant d'appareil **et** de pseudo, un tricheur revient comme un nouveau joueur ; il devra alors refaire de vraies parties, plafonnées à 200. D'où la vérification du gagnant avant de verser les grains.

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
