# Module comptes

Responsable : Taha. État au 25/10/2026 : Phase 1, intégrée avec les Phases 0 et 2 (branche `integration/phases-0-1-2`).

Le module `accounts` gère les utilisateurs, les rôles, les profils publics et le rattachement à un établissement.

## Règles importantes

- Les rôles `APPRENANT`, `MENTOR`, `FORMATEUR` et `RECRUTEUR` peuvent s’inscrire. L'adresse e-mail est obligatoire : sans elle, la réinitialisation du mot de passe serait impossible.
- Les rôles `ADMIN` et `ETABLISSEMENT` sont créés depuis l’administration.
- Le groupe Django est synchronisé avec le rôle lors de la sauvegarde.
- Un mentor ou un formateur est vérifié par un administrateur (`is_verified`, dans l'admin des utilisateurs) ; tant qu'il ne l'est pas, il ne publie rien.
- Un profil public n’est visible que si l’utilisateur l’a activé.
- Le code d’invitation d’un établissement est unique et généré côté serveur. Seul un apprenant rejoint un établissement ; les autres rôles reçoivent 403.
- Avatar et logo : JPG, PNG ou WEBP, 5 Mo au maximum.
- La page de connexion propose « Mot de passe oublié ? », qui envoie un lien de réinitialisation par e-mail.

## Démonstration

1. Créer un compte depuis `/comptes/inscription/`.
2. Modifier le profil depuis `/comptes/profil/modifier/`.
3. Activer le profil public.
4. En tant qu'apprenant, rejoindre un établissement avec son code d’invitation.
5. Depuis la connexion, demander un lien de réinitialisation du mot de passe.

## Questions du jury

- Pourquoi utiliser un utilisateur personnalisé avant la première migration ?
- Pourquoi retirer l’utilisateur des anciens groupes lors d’un changement de rôle ?
- Pourquoi filtrer les profils publics dans le queryset plutôt que dans le template ?
- Pourquoi la limite de 5 Mo ne relit-elle pas un fichier déjà stocké ? (Le contrôle a eu lieu à l'envoi ; relire le stockage ferait échouer la modification d'un profil dont le fichier manque sur le disque.)
