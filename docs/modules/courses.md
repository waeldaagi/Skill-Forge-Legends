# Module catalogue et cours

Le module `courses` couvre le catalogue public, les cours des formateurs, l’inscription des apprenants et la progression par chapitre.

## Règles importantes

- Un formateur ne voit et ne modifie que ses propres cours.
- Un chapitre possède un ordre unique dans son cours.
- Une ressource contient exactement un fichier ou un lien.
- Une inscription et une progression sont uniques par utilisateur et par cours ou chapitre.
- La progression est calculée à partir des chapitres terminés, sans valeur stockée incohérente.

## Démonstration

La commande `python manage.py seed_demo` crée le cours « Django : du modèle au déploiement » et un quiz de démonstration.

## Questions du jury

- Pourquoi utiliser `select_related` et `prefetch_related` dans le catalogue ?
- Pourquoi le contrôle de propriété est-il réalisé dans le queryset du formateur ?
- Pourquoi la contrainte « exactement une source » est-elle doublée par `clean()` ?
