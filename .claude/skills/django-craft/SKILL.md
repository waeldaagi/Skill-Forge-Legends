---
name: django-craft
description: Règles d'écriture du code Python/Django de SkillForge pour un code sobre, cohérent et défendable à l'oral. À charger avant d'écrire ou de modifier models, views, forms, services, tasks ou commandes, et pour relire un diff avant chaque commit.
---

# Code Django sobre et défendable

But : un code qu'un étudiant de 5e année peut expliquer ligne par ligne devant le jury. Si personne ne saurait dire pourquoi une ligne existe, elle ne doit pas exister.

## 1. Avant d'écrire

1. Lis deux fichiers existants de la même app (ou de `core/` si l'app est vide) et reprends leurs conventions : ordre des imports, style des vues, noms.
2. Vérifie si Django fournit déjà la solution : `get_object_or_404`, `UniqueConstraint`, `CheckConstraint`, validators, `messages`, `Paginator`, mixins d'authentification, `transaction.atomic`, `F()`, `select_related` / `prefetch_related`.
3. Écris la plus petite version qui satisfait le besoin. On généralise au troisième usage réel, pas avant.

## 2. Ce qu'on écrit

- **Noms du domaine**, précis : `book_slot`, `AvailabilitySlot`, `is_course_completed`, `CANCELLATION_DEADLINE`. Jamais `data`, `info`, `result`, `obj2`, `handle_stuff`, `process_data`, ni de `utils.py` fourre-tout.
- **Rôles** : les valeurs restent celles de `User.Role` (`APPRENANT`, `MENTOR`…). Les variables Python sont en anglais : `learner`, `mentor`, `trainer`, `recruiter`, `institution`. Un seul mot par concept dans tout le projet.
- **Fonctions courtes à un seul rôle.** Si le nom contient « and », découpe.
- **Services** (`services.py`) : prennent des objets métier, renvoient des objets métier, lèvent des exceptions métier (`SlotAlreadyBooked`, `CancellationTooLate`). Ils ne connaissent ni `request` ni `HttpResponse`.
- **Vues fines** : récupérer l'objet, appeler un service, afficher un message, rediriger ou rendre. Aucune règle métier dans les vues ni dans les templates.
- **Exceptions précises** : `except SlotAlreadyBooked:`, `except httpx.TimeoutException:`. Un `except Exception` n'est permis qu'au bord du système (tâche Celery, client IA) et il journalise puis réagit.
- **Constantes nommées** pour les règles métier : `CANCELLATION_DEADLINE = timedelta(hours=2)`, `MAX_UPLOAD_SIZE = 5 * 1024 * 1024`.
- **Requêtes** : pas de N+1 sur les listes. Ajoute `select_related` / `prefetch_related` et un `assertNumQueries` sur la vue de liste.
- **Messages d'erreur** qui disent ce qui s'est passé et quoi faire : « Ce créneau vient d'être réservé. Choisissez-en un autre. »

## 3. Commentaires et docstrings

- Un commentaire explique **pourquoi**, jamais **quoi**.
  - Oui : `# select_for_update : deux apprenants peuvent valider le même créneau à la même seconde.`
  - Non : `# On récupère le créneau`.
- Docstring seulement pour les services publics (contrats entre modules) et les règles non évidentes, en 1 à 3 lignes. Pas de docstring qui répète le nom de la fonction.
- Aucun `# TODO: implement`, `# Add more validation here`, `# Example usage`, `# Step 1:`.
- Aucun emoji dans le code, les logs ou les messages.

## 4. Signes de code généré à éliminer

| Symptôme | Correction |
|---|---|
| Classe de base, factory ou registry pour un seul cas | Code direct |
| Vérifications impossibles (`if request.user is None` derrière `LoginRequiredMixin`, `isinstance` sur un champ typé) | Supprimer |
| `try/except` qui avale tout et renvoie `None` | Attraper l'exception précise ou laisser remonter |
| Logs à chaque ligne (`logger.info("Entering...")`) | Un log aux décisions et aux erreurs |
| `result = x` puis `return result` | `return x` |
| Paramètres jamais utilisés, `**kwargs` « au cas où » | Supprimer |
| Code mort, imports inutilisés | Supprimer (`ruff` les signale) |
| Données factices génériques : `John Doe`, `test@example.com`, `Lorem ipsum`, `Acme` | Données plausibles : prénoms et noms tunisiens variés, cours réels (« Django : du modèle au déploiement », « Docker pour développeurs »), villes (Tunis, Sfax, Sousse, Bizerte) |
| Messages vagues (« Une erreur est survenue ») | Message précis et actionnable |
| Un fichier de 600 lignes produit d'un coup | Construire par petites étapes, un commit par fonctionnalité |
| Styles différents d'une app à l'autre | Même structure dans chaque app |

## 5. Relecture avant chaque commit

Lance :

```
ruff check . && ruff format --check .
python manage.py makemigrations --check --dry-run
git diff --staged
git diff --staged | grep -nE "except Exception: *pass|except: *$|TODO|FIXME|print\(|Lorem|John Doe|example\.com|\.raw\(|cursor\(\)"
```

Puis réponds honnêtement à deux questions :
1. Puis-je supprimer 20 % de ce diff sans changer le comportement ? Si oui, supprime.
2. L'étudiant responsable saurait-il expliquer chaque bloc ? Si non, simplifie ou ajoute le commentaire « pourquoi » qui manque.

## 6. Commits

- Une intention par commit. Format et exemples : voir le skill `redaction-fr`.
- Jamais de commit fourre-tout (« update », « fix stuff », « implémentation complète du module »).
