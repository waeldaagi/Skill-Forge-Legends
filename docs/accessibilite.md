# Accessibilité

Ce document décrit ce que le socle commun (`templates/base.html`, `static/css/theme.css`, rendu des formulaires) garantit à toutes les pages, et les audits réalisés. L'audit des pages de chaque module (catalogue, réservation, forum, soumission, tableaux de bord) sera ajouté en Phase 5, avec les scores avant et après corrections.

## Audit du 25/10/2026 (fin de la Phase 0)

Outil : Lighthouse 13.5.0 (catégorie accessibilité, moteur axe-core 4.14), Chrome 155 sans interface, profil mobile. Serveur de développement local.

| Page | Score | Audits réussis | Échecs |
|---|---|---|---|
| Accueil, visiteur anonyme | 100 | 22 | 0 |
| Connexion | 100 | 20 | 0 |
| Accueil, administrateur connecté (menu utilisateur, lien Administration) | 100 | 22 | 0 |

Audits réussis notamment : contraste des couleurs, noms accessibles des liens et des boutons, ordre des titres, langue du document, titre de la page, lien d'évitement, attributs ARIA valides, listes et listes de définitions bien formées, taille des cibles tactiles, présence d'un repère `main`. Les 44 autres audits ne s'appliquent pas à ces pages (pas d'image, de tableau ni de vidéo, par exemple).

Lighthouse ne mesure pas le parcours au clavier. Il a donc été vérifié par un script (Chrome piloté par puppeteer, touche Tab) :

| Parcours | Résultat |
|---|---|
| Accueil, 1280 px | Ordre : lien d'évitement, logo, « Se connecter » (en-tête), « Se connecter » (contenu). Contour de focus de 3 px sur chaque élément. |
| Lien d'évitement | Entrée mène à `#contenu` ; la tabulation suivante atteint le premier lien du contenu. |
| Connexion | Le champ « Nom d'utilisateur » a le focus à l'ouverture (`autofocus` posé par Django), puis mot de passe, puis bouton « Se connecter ». |
| Accueil administrateur, 375 px | Le bouton « Afficher le menu » s'ouvre avec Entrée (`aria-expanded` passe à `true`) ; la tabulation suivante atteint « Administration ». |

Limite : Lighthouse refuse d'auditer une page qui répond 404, 403 ou 500. Ces pages utilisent le même gabarit `base.html` et la même structure (un `<h1>`, un paragraphe, un bouton) que les pages auditées.

## Audit du 25/10/2026 (Phase 2 : mentorat et forum)

Même outil et même profil, sur les données de `seed_demo`, avec le compte de l'apprenante Yasmine Trabelsi ou du mentor Skander Jaziri selon la page.

| Page | Compte | Score |
|---|---|---|
| Annuaire des mentors | Apprenante | 100 |
| Détail d'un mentor et ses créneaux libres | Apprenante | 100 |
| Réservation d'un créneau | Apprenante | 100 |
| Mes sessions | Apprenante | 100 |
| Demande de session à traiter | Mentor | 100 |
| Mes créneaux | Mentor | 100 |
| Ajout d'un créneau | Mentor | 100 |
| Liste des sujets du forum | Apprenante | 100 |
| Sujet résolu avec réponse acceptée et votes | Apprenante | 100 |
| Sujet avec une réponse en attente de vérification | Apprenante | 100 |
| Nouveau sujet | Apprenante | 100 |
| Signalement d'une réponse | Apprenante | 100 |
| File de modération | Mentor | 100 |

Contrôles complémentaires :

- aucune de ces pages ne défile horizontalement à 375 px (vérification par script) ;
- publication réelle d'un sujet, avec worker Celery et Gemini : la zone `role="status"` annonce « Vérification automatique de votre message en cours… », puis « Votre message est publié. » ; HTMX cesse d'interroger le serveur dès la réponse 286 ;
- bouton de vote « Utile » : `aria-pressed` indique l'état, un texte masqué nomme l'auteur de la réponse, et l'`id` stable permet à HTMX de rendre le focus au bouton après le remplacement ;
- file de modération : chaque formulaire de rejet a ses propres `id`, pour qu'un libellé reste lié à un seul champ (test `test_each_rejection_form_has_its_own_field_ids`).

## Audit du 25/10/2026 (Phase 1 corrigée : cours et comptes)

Même outil et même profil, sur les données de `seed_demo`, avec le compte de l'apprenante Yasmine Trabelsi ou de la formatrice Mariem Gharbi.

| Page | Compte | Score |
|---|---|---|
| Mes cours | Formatrice | 100 |
| Détail d'un cours, boutons de gestion | Formatrice | 100 |
| Détail d'un cours, progression (`<progress>` natif) | Apprenante | 100 |
| Chapitre avec vidéo YouTube intégrée | Apprenante | 100 |
| Chapitre, boutons de gestion des ressources | Formatrice | 100 |
| Modification d'un chapitre | Formatrice | 100 |
| Gestion d'un quiz | Formatrice | 100 |
| Suppression d'un quiz (confirmation) | Formatrice | 100 |
| Modification d'une question | Formatrice | 100 |
| Quiz, aperçu sans bouton d'envoi | Formatrice | 100 |
| Quiz à passer | Apprenante | 100 |
| Connexion, avec « Mot de passe oublié ? » | Anonyme | 100 |
| Profil | Apprenante | 100 |
| Rejoindre un établissement | Apprenante | 100 |

Contrôles complémentaires :

- « Mes cours » défilait horizontalement à 375 px : les textes `visually-hidden` des cellules, en position absolue, sortaient de la zone défilante du tableau. `.sf-table-wrapper` porte maintenant `position: relative` ; plus aucun défilement horizontal, mesuré par script ;
- l'iframe vidéo porte un titre (« Vidéo du chapitre … ») et `referrerpolicy="strict-origin-when-cross-origin"`, sans quoi YouTube refuse la lecture (erreur 153, constatée sur capture) ;
- chaque bouton « Modifier » ou « Supprimer » d'une liste complète son nom par un texte masqué (« Supprimer le chapitre Modéliser une fonctionnalité »).

## Audit du 26/10/2026 (Phase 5 : intégration, tableaux de bord, paiements)

Même outil et même profil, sur les données de `seed_demo`, avec le compte de chaque rôle.

| Page | Compte | Score |
|---|---|---|
| Accueil, présentation | Anonyme | 100 |
| Tableau de bord | Apprenante, mentor, formatrice, administratrice, recruteur | 100 chacun |
| Catalogue des cours (filtres, cartes, pagination) | Anonyme | 100 |
| Chapitre, avec liens vers le chapitre précédent et le suivant | Apprenante | 100 |
| Quiz | Apprenante | 100 |
| Profil | Apprenante | 100 |
| Création d'un cours | Formatrice | 100 |
| Offres, mes abonnements, mes paiements | Apprenante | 100 chacune |
| Tableau de pilotage, avec graphique Chart.js et tableau des valeurs | Apprenante, établissement, administratrice | 100 chacun |
| Analytics IA | Administratrice | 100 |
| Certifications : catalogue, mes soumissions, détail d'une soumission | Apprenante | 100 chacune |
| Revue d'une soumission, file des revues | Mentor | 100 chacune |
| Certifications et critères (liste, formulaires) | Formatrice | 100 chacun |
| Talents certifiés, profil d'un talent, contact | Recruteur | 100 chacun |
| Vérification publique d'un certificat | Anonyme | 100 |

Avant correction, les trois pages des paiements ouvraient un second `<main id="contenu">` dans celui de `base.html` : deux repères principaux et un identifiant en double. Lighthouse ne le signalait pas ; le contrôle automatique ci-dessous l'a trouvé.

Contrôle automatique de toutes les pages (script puppeteer, 375 px de large) : pour chaque profil, chaque lien interne est suivi, et chaque page est vérifiée (défilement horizontal, un seul `<h1>`, un seul `<main>`, aucun style en ligne, images avec `alt`, boutons nommés). Résultat : 199 pages parcourues pour les six rôles et l'anonyme, aucune anomalie.

Parcours au clavier seul (Tab, Entrée et saisie, sans souris), script puppeteer :

| Parcours | Résultat |
|---|---|
| Réserver un créneau : annuaire, « Voir les créneaux », « Réserver ce créneau », champs Sujet et Description, « Envoyer la demande » | Demande enregistrée, message « Demande envoyée. Le mentor doit maintenant la confirmer. » |
| Répondre à un sujet du forum : champ de réponse, « Publier ma réponse » | Réponse enregistrée, en attente de la vérification automatique |
| Lien d'évitement | Premier élément atteint par Tab ; Entrée mène à `#contenu` |

Sur les 58 éléments atteints par Tab, tous affichent un contour de focus d'au moins 3 px.

## Structure commune des pages

`templates/base.html` fournit à chaque page :

- `<html lang="fr">` et un lien d'évitement « Aller au contenu » vers `#contenu`, visible dès qu'il reçoit le focus ;
- les repères `<header>`, `<nav aria-label="Navigation principale">`, `<main id="contenu">` et `<footer>` ;
- un seul `<h1>`, fourni par la page enfant ; les sections suivent avec `<h2>` puis `<h3>` ;
- un bouton de menu mobile avec `aria-label`, `aria-controls` et `aria-expanded` (Bootstrap met ce dernier à jour) ;
- `aria-current="page"` sur le lien de navigation de la page courante.

Le test `core/tests/test_views.py` vérifie la langue, le lien d'évitement, les repères et l'unicité du `<h1>` sur l'accueil.

## Formulaires

Tous les formulaires passent par `core.forms.SkillForgeFormRenderer` (réglage `FORM_RENDERER`) :

- chaque champ a un `<label for>` ; un groupe de cases ou de boutons radio a un `<fieldset>` et une `<legend>` ;
- le caractère obligatoire est écrit en texte, « (obligatoire) », en plus de l'attribut HTML `required` ;
- un champ en erreur reçoit `aria-invalid="true"` et `aria-describedby` vers le message d'erreur (`id_<champ>_error`) et le texte d'aide (`id_<champ>_helptext`) ;
- les erreurs générales du formulaire s'affichent dans une alerte `role="alert"`.

Django 5.2 pose lui-même `aria-invalid` et `aria-describedby` ; le renderer ajoute les classes Bootstrap et la mention « (obligatoire) ». Le test `core/tests/test_forms.py` couvre ces quatre points.

## Contenu dynamique

- Messages Django : conteneur `aria-live="polite"`, et `role="alert"` pour les messages d'erreur.
- Statut d'un traitement IA (`{% ai_job_status job %}`) : zone `role="status"` qui reste en place pendant que HTMX remplace son contenu toutes les 2 s. Le lecteur d'écran annonce chaque changement d'état. Le spinner est décoratif (`aria-hidden="true"`) et toujours accompagné d'un texte précis (« Classement de votre message en cours… »).
- Un échec IA s'affiche dans la même zone de statut, sans `role="alert"` imbriqué, pour éviter une double annonce.

## Clavier et focus

- Aucun élément cliquable n'est un `div` ou un `span` : liens `<a>` et boutons `<button>` uniquement.
- Focus visible sur tout élément interactif : contour de 3 px, violet `#6D28D9` sur fond clair, orange clair `#FDBA74` sur l'en-tête et le pied de page bleu nuit. Bootstrap remplace habituellement ce contour par une ombre légère ; le thème la retire au profit du contour.
- Les modales Bootstrap se ferment avec Échap (comportement par défaut, à conserver).

## Mouvement

`prefers-reduced-motion: reduce` coupe les animations et les transitions, y compris la rotation du spinner. Le texte de statut reste affiché.

## Contrastes (WCAG AA)

Seuils : 4,5:1 pour le texte courant, 3:1 pour un texte de 24 px et plus et pour les contours de composants. Ratios calculés avec la formule de luminance relative du WCAG 2.1.

| Texte | Fond | Usage | Ratio | Résultat |
|---|---|---|---|---|
| `#1F2937` texte | `#F8FAFC` fond de page | Texte courant | 14,03 | Conforme |
| `#1F2937` texte | `#FFFFFF` surface | Texte dans les cartes et formulaires | 14,68 | Conforme |
| `#475569` secondaire | `#FFFFFF` surface | Texte secondaire, mention « (obligatoire) » | 7,58 | Conforme |
| `#475569` secondaire | `#F8FAFC` fond de page | Texte d'introduction | 7,24 | Conforme |
| `#6D28D9` violet | `#FFFFFF` surface | Liens | 7,10 | Conforme |
| `#6D28D9` violet | `#F8FAFC` fond de page | Liens, numéros des étapes | 6,79 | Conforme |
| `#5B21B6` violet foncé | `#FFFFFF` surface | Lien survolé | 8,98 | Conforme |
| `#FFFFFF` blanc | `#6D28D9` violet | Bouton principal | 7,10 | Conforme |
| `#FFFFFF` blanc | `#5B21B6` violet foncé | Bouton principal survolé | 8,98 | Conforme |
| `#FFFFFF` blanc | `#0B1026` bleu nuit | Marque, lien de l'en-tête actif | 18,81 | Conforme |
| `#E2E8F0` gris clair | `#0B1026` bleu nuit | Liens de l'en-tête, pied de page | 15,26 | Conforme |
| `#F97316` orange | `#0B1026` bleu nuit | « Forge » dans la marque | 6,71 | Conforme |
| `#0B1026` bleu nuit | `#F97316` orange | Bouton d'accent (`.btn-accent`) | 6,71 | Conforme |
| `#0B1026` bleu nuit | `#FDBA74` orange clair | Bouton d'accent survolé | 11,15 | Conforme |
| `#0B1026` bleu nuit | `#FFFFFF` blanc | Bouton de l'en-tête survolé | 18,81 | Conforme |
| `#15803D` succès | `#FFFFFF` surface | Message de succès, statut IA terminé | 5,02 | Conforme |
| `#15803D` succès | `#DCFCE7` fond succès | Alerte de succès | 4,57 | Conforme, marge faible |
| `#B91C1C` erreur | `#FFFFFF` surface | Message d'erreur sous un champ | 6,47 | Conforme |
| `#B91C1C` erreur | `#FEE2E2` fond erreur | Alerte d'erreur | 5,30 | Conforme |
| `#FFFFFF` blanc | `#B91C1C` erreur | Bouton de suppression | 6,47 | Conforme |
| `#B91C1C` erreur | `#FFFFFF` surface | Bouton contour « Supprimer », « Refuser », « Annuler » | 6,47 | Conforme |
| `#475569` secondaire | `#F8FAFC` fond de page | Bouton contour secondaire (`btn-outline-secondary`, au lieu du gris Bootstrap à 4,48) | 7,24 | Conforme |
| `#92400E` avertissement | `#FEF3C7` | Statut « Demandée » | 6,37 | Conforme |
| `#15803D` succès | `#DCFCE7` | Statut « Confirmée » | 4,57 | Conforme, marge faible |
| `#1F2937` texte | `#F1F5F9` | Statut « Terminée » | 13,40 | Conforme |
| `#92400E` avertissement | `#FEF3C7` | Statut « En attente de vérification » (forum) | 6,37 | Conforme |
| `#15803D` succès | `#DCFCE7` | « Publié », « Résolu », « Réponse acceptée » | 4,57 | Conforme, marge faible |
| `#B91C1C` erreur | `#FEE2E2` | « Masqué, à relire », « Rejeté » | 5,30 | Conforme |
| `#5B21B6` violet foncé | `#EDE9FE` | Message d'information (« Votre sujet est enregistré… ») | 7,57 | Conforme |
| `#B91C1C` erreur | `#FEE2E2` | Statuts « Annulée » et « Refusée » | 5,30 | Conforme |
| `#92400E` avertissement | `#FEF3C7` fond avertissement | Alerte d'avertissement | 6,37 | Conforme |
| `#6D28D9` violet | `#EDE9FE` fond violet clair | Alerte d'information | 5,98 | Conforme |

Contours et éléments non textuels (seuil 3:1) :

| Élément | Fond | Ratio | Résultat |
|---|---|---|---|
| Bordure des champs `#64748B` | `#FFFFFF` | 4,76 | Conforme |
| Contour de focus `#6D28D9` | `#FFFFFF` | 7,10 | Conforme |
| Contour de focus `#FDBA74` | `#0B1026` | 11,15 | Conforme |

Paire exclue : l'orange `#F97316` sur blanc donne 2,80. L'orange n'est donc jamais utilisé comme couleur de texte sur fond clair, et un bouton orange porte un texte bleu nuit. Les bordures de cartes (`#E2E8F0`) sont décoratives et ne portent aucune information ; elles ne sont pas soumises au seuil de 3:1.

Toute nouvelle paire texte/fond introduite par un module doit être ajoutée à ce tableau.

## Vérifications visuelles

Accueil et page de connexion vérifiés à 375 px et à 1280 px de large le 25/10/2026 (captures Chrome sans interface) : aucun défilement horizontal, menu replié en bouton sur mobile.
