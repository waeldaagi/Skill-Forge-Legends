# Validation des modules accounts et courses

Les tests ciblent les règles métier et les parcours visibles, pas seulement les lignes exécutées.
Ils couvrent notamment les rôles, la propriété des cours, les formulaires de questions, la
publication et l'administration Django.

## Commandes

```text
python -m pytest accounts courses -q
coverage run manage.py test accounts courses
coverage report --include="accounts/*,courses/*"
python -m ruff check .
python -m ruff format --check .
python manage.py makemigrations --check --dry-run
python manage.py check
```

La commande `courses.tests.test_admin` vérifie l'enregistrement des modèles, la liste des cours,
la recherche des quiz et le refus d'un utilisateur non staff. La commande `seed_demo` est testée
pour garantir qu'un quiz de démonstration possède ses quatre choix.
