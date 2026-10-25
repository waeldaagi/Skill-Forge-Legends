---
name: redaction-fr
description: Style d'écriture de tous les textes du projet SkillForge — README, docs/, fiches de module, rapports IA, messages de commit et descriptions de PR. À charger avant de rédiger ou de relire un texte en français, pour un ton d'ingénieur clair et précis, sans les tournures typiques des textes générés.
---

# Rédaction SkillForge

## 1. Ton

Un ingénieur qui écrit à un collègue : factuel, précis, court. On décrit ce qui existe et ce qui a été mesuré, pas ce qui serait « puissant » ou « robuste ».

## 2. Règles

- Une idée par phrase, 25 mots au maximum.
- Commencer par l'information. Pas d'introduction ni de conclusion qui reformulent le reste.
- Des chiffres plutôt que des adjectifs : « F1 macro = 0,81 sur 80 messages » plutôt que « excellentes performances ».
- Dire les limites : jeu de données petit ou synthétique, fournisseur `mock` en démo, cas non couverts.
- Titres informatifs : « Empêcher la double réservation d'un créneau » plutôt que « Fonctionnalités clés ».
- Listes seulement pour des éléments parallèles ; le raisonnement s'écrit en phrases.
- Gras rare : une fois par section au maximum. Aucun emoji. Pas de badge décoratif dans le README (seuls les badges CI et couverture réels sont permis).
- Typographie française : espace insécable avant `: ; ! ?`, guillemets « », virgule décimale (0,81), unités `Mo`, `ms`.
- Glossaire fixe, sans synonymes alternés : apprenant, mentor, formateur, recruteur, administrateur, établissement ; créneau, session, preuve, soumission, grille de critères, certificat.

## 3. Expressions à bannir

Clichés de textes générés :
« Il est important de noter que », « Il convient de souligner », « Dans un monde en constante évolution », « À l'ère du numérique », « En conclusion », « En somme », « Plongeons dans », « Que vous soyez… ou… », « véritable », « incontournable », « révolutionnaire », « de pointe », « robuste et évolutif », « solution complète », « fluide », « sans couture », « tirer parti de », « exploiter la puissance de », « jouer un rôle crucial », « un atout majeur », « au cœur de », « n'hésitez pas à », « afin de garantir une expérience optimale ».

Tics de construction :
- triplets systématiques (« simple, rapide et efficace ») ;
- « non seulement… mais aussi » en série ;
- tiret cadratin (—) dans chaque phrase ;
- « permet de » répété dans chaque paragraphe ;
- questions rhétoriques en ouverture.

Anglicismes à corriger : « adresser un problème » → traiter ; « supporter » → prendre en charge ; « performant » sans mesure → donner la mesure.

Test final : supprime toute phrase qui pourrait figurer telle quelle dans n'importe quel autre projet.

## 4. Messages de commit

Format : `type(app): verbe au présent + objet`, 72 caractères au maximum, sans point final.

Types : `feat`, `fix`, `test`, `docs`, `refactor`, `style`, `chore`, `ci`.

Corps optionnel : le **pourquoi**, quand il n'est pas évident.

Bons exemples :
```
feat(mentoring): ajoute la réservation d'un créneau
fix(mentoring): refuse l'annulation à moins de 2 h du début
test(community): couvre le repli en file humaine si l'IA échoue
docs(assessment): ajoute les métriques de l'évaluation IA
```

Mauvais exemples : `update`, `fix bug`, `WIP`, `implémentation complète du module mentoring`, `Amélioration significative de la robustesse du système`.

## 5. README

Ordre :
1. Une phrase sur ce que fait SkillForge.
2. Une capture d'écran réelle.
3. Lancer le projet : commandes exactes, testées sur une machine propre.
4. Comptes de démo.
5. Modules et responsables.
6. Tests et couverture, avec le vrai chiffre.
7. Déploiement : l'URL publique.
8. Liens vers `docs/`.

Pas de section « Features ✨ », pas de « Contributing » ni de licence de façade.

## 6. Rapports IA (`docs/ia/*.md`)

1. Cas d'usage et décision qu'il aide à prendre.
2. Construction du jeu de données : taille, source, qui a étiqueté, répartition des classes.
3. Résultats en tableau : métriques, matrice de confusion, latence moyenne et p95, fournisseur et modèle utilisés, date.
4. Lecture des résultats : où le modèle se trompe, avec deux ou trois exemples.
5. Limites et améliorations possibles.

N'annonce jamais un résultat qui n'a pas été produit par la commande d'évaluation.
