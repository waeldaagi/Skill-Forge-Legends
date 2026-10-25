---
name: ui-identity
description: Identité visuelle et rédaction d'interface de SkillForge (templates Django, CSS, Bootstrap, textes affichés). À charger avant de créer ou modifier un template, du CSS ou un texte d'interface, pour une interface cohérente, accessible et crédible qui n'a pas l'air d'un template généré.
---

# Interface SkillForge

## 1. Direction

SkillForge est un **atelier** : on y apprend, on y travaille avec un mentor, on y prouve ce qu'on sait faire. L'interface ressemble à un outil de travail soigné, pas à une landing page marketing.

- Information utile d'abord : ce que l'utilisateur doit faire maintenant (prochaine session, chapitre en cours, soumission en attente).
- Densité modérée, alignement à gauche, hiérarchie par la taille et la graisse, pas par la couleur.
- Cohérence avec la présentation vue par le jury : bleu nuit, violet, orange en accent, Montserrat pour les titres.

## 2. Jetons de design (`static/css/theme.css`)

Couleurs :

| Jeton | Valeur | Usage |
|---|---|---|
| `--sf-navy` | `#0B1026` | En-tête, pied de page, titres de bandeau |
| `--sf-violet` | `#6D28D9` | Action principale, liens, focus |
| `--sf-orange` | `#F97316` | Accent rare : badge « Certifié », marque. Un seul usage par écran |
| `--sf-text` | `#1F2937` | Texte courant |
| `--sf-muted` | `#475569` | Texte secondaire |
| `--sf-bg` | `#F8FAFC` | Fond de page |
| `--sf-surface` | `#FFFFFF` | Cartes, tableaux, formulaires |
| `--sf-border` | `#E2E8F0` | Bordures |
| `--sf-success` | `#15803D` | Succès |
| `--sf-danger` | `#B91C1C` | Erreur, action destructive |
| `--sf-warning-text` | `#92400E` | Avertissement (texte) |

Règles :
- Remplace les variables Bootstrap (`--bs-primary`, `--bs-link-color`, `--bs-border-radius`…). Le bleu Bootstrap par défaut ne doit apparaître nulle part.
- Orange : jamais en petit texte sur fond clair. Un bouton orange porte un texte bleu nuit.
- Toute nouvelle paire texte/fond est vérifiée (≥ 4,5:1, ou ≥ 3:1 pour un texte de 24 px et plus) et ajoutée au tableau de `docs/accessibilite.md`.

Typographie (polices auto-hébergées dans `static/fonts/`, pas de Google Fonts en prod) :
- Titres : Montserrat 600–700.
- Texte : Open Sans 400/600, 16 px minimum, interligne 1,5.
- Échelle : 14 / 16 / 18 / 22 / 28 / 36 px.

Formes :
- Espacements : 4, 8, 12, 16, 24, 32, 48 px uniquement.
- Rayon : 6 px partout.
- Les cartes ont une bordure, pas d'ombre. Une seule ombre légère, réservée aux éléments flottants (menu déroulant, modale).
- Icônes : un seul jeu (Bootstrap Icons, fichiers locaux), taille constante, `aria-hidden="true"` plus un libellé texte ou `aria-label`.

## 3. Interdits (aspect « généré »)

- Dégradés violet→rose ou violet→bleu en fond, glassmorphism, halos lumineux, blobs flous, texte en dégradé. Les visuels lumineux de la présentation restent dans la présentation.
- Hero géant centré avec slogan et deux boutons ailleurs que sur l'accueil.
- Grilles de trois cartes identiques « icône + titre + deux lignes » répétées sur chaque page.
- Emojis utilisés comme icônes.
- Icône « étincelles » ou badge « IA ✨ » partout. L'IA est présentée sobrement : « Évaluation automatique, validée ensuite par un mentor ».
- Fausses statistiques (« 10 000+ apprenants »), faux témoignages, faux logos partenaires. On affiche des chiffres réels de la base, ou rien.
- Animations décoratives au défilement. Toute transition respecte `prefers-reduced-motion`.
- Styles en ligne dans les templates.

## 4. Ce qui rend l'interface crédible

- **Listes d'enregistrements en tableau** (sessions, soumissions, paiements, utilisateurs) avec en-têtes `<th scope="col">`. Les cartes servent au catalogue de cours et à l'annuaire des mentors.
- **États vides utiles** : dire pourquoi c'est vide et proposer l'action. Ex. « Aucun créneau publié. Ajoutez votre premier créneau pour apparaître dans l'annuaire des mentors. » + bouton.
- **Chargement IA précis** et annoncé aux lecteurs d'écran (`aria-live="polite"`) : « Analyse de votre soumission selon 4 critères… ». Jamais un spinner seul.
- **Erreurs** : ce qui s'est passé + ce qu'on peut faire.
- **Confirmation des actions destructives** avec la conséquence : « Annuler la session du 12 nov. à 14 h ? Le mentor sera prévenu par e-mail. »
- **Formats français** : `12 nov. 2026 à 14 h`, `49,000 TND`, `0,81`. Active la localisation Django (`USE_L10N` / filtres `date`, `floatformat`).
- **Données de démo réalistes** : vrais intitulés de cours, prénoms et noms tunisiens variés, dates proches de la date de démo.

## 5. Textes d'interface

- Vouvoiement partout.
- Boutons = verbe + objet : « Réserver ce créneau », « Soumettre ma preuve », « Publier le cours ». Pas « Valider », « Envoyer », « Cliquez ici ».
- Majuscule au premier mot seulement : « Mes sessions », pas « Mes Sessions ».
- Typographie française : espace insécable avant `: ; ! ?` (`&nbsp;`), guillemets « ».
- Expressions interdites : « Libérez votre potentiel », « Boostez », « Révolutionnez », « Propulsez », « Plongez dans », « en toute simplicité », « sans effort », « expérience immersive », « IA de pointe », « Bienvenue dans l'avenir de… », « votre aventure commence ici ».

## 6. Vérification avant de terminer un template

- [ ] Hérite de `base.html` ; un seul `<h1>` ; pas de saut de niveau de titre.
- [ ] Chaque champ a son `<label>` ; erreurs reliées par `aria-describedby`.
- [ ] Aucun style en ligne ; uniquement les classes et jetons du thème.
- [ ] Affichage vérifié à 375 px et à 1280 px de large.
- [ ] Parcours au clavier complet (Tab, Maj+Tab, Entrée, Échap) avec focus visible.
- [ ] Aucun élément de la section 3.
