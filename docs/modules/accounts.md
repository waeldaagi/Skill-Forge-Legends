# Module comptes

Le module `accounts` gère les utilisateurs, les rôles, les profils publics et le rattachement à un établissement.

## Règles importantes

- Les rôles `APPRENANT`, `MENTOR`, `FORMATEUR` et `RECRUTEUR` peuvent s’inscrire.
- Les rôles `ADMIN` et `ETABLISSEMENT` sont créés depuis l’administration.
- Le groupe Django est synchronisé avec le rôle lors de la sauvegarde.
- Un profil public n’est visible que si l’utilisateur l’a activé.
- Le code d’invitation d’un établissement est unique et généré côté serveur.

## Démonstration

1. Créer un compte depuis `/comptes/inscription/`.
2. Modifier le profil depuis `/comptes/profil/modifier/`.
3. Activer le profil public.
4. Rejoindre un établissement avec son code d’invitation.

## Questions du jury

- Pourquoi utiliser un utilisateur personnalisé avant la première migration ?
- Pourquoi retirer l’utilisateur des anciens groupes lors d’un changement de rôle ?
- Pourquoi filtrer les profils publics dans le queryset plutôt que dans le template ?
