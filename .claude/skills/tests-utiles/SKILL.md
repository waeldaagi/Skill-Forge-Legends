---
name: tests-utiles
description: Méthode pour écrire des tests Django qui prouvent un comportement de SkillForge (règles métier, permissions, IA, erreurs) au lieu de gonfler la couverture. À charger quand on écrit, complète ou relit des tests, et avant de présenter le rapport de couverture au jury.
---

# Des tests qui prouvent quelque chose

Chaque test protège une règle que le jury pourrait demander. Le nom du test énonce cette règle en clair :
`test_learner_cannot_book_an_already_booked_slot`, `test_post_stays_hidden_when_moderation_fails`.

## 1. Organisation

```
<app>/tests/
├── __init__.py
├── factories.py          # factory_boy, valeurs par défaut réalistes
├── test_models.py        # contraintes, clean(), propriétés
├── test_services.py      # règles métier et cas limites
├── test_forms.py         # erreurs de saisie et messages
├── test_views.py         # statut + template + contexte + effet de bord
├── test_permissions.py   # matrice d'accès et objets d'autrui
└── test_tasks.py         # tâches Celery et IA (fournisseur mock)
```

- Classes `django.test.TestCase` : elles tournent avec `python manage.py test` **et** avec `pytest`.
- Données partagées dans `setUpTestData` (plus rapide que `setUp`).
- Un comportement par test, structure Préparer / Agir / Vérifier.
- `UserFactory(role=User.Role.MENTOR)` pour chaque rôle.

## 2. Quoi tester, couche par couche

**Modèles**
- Contraintes : `IntegrityError` sur une inscription en double ; `Resource` refusée si elle a à la fois un fichier et un lien.
- `clean()` : chevauchement de créneaux, fin avant début, somme des poids des critères ≠ 100.

**Services** (le cœur de la note)
- Cas nominal **et** cas limites. Exemple pour l'annulation à 2 h : 2 h 01 avant → accepté, 1 h 59 avant → refusé.
- Exceptions métier levées au bon moment (`SlotAlreadyBooked`).
- Règles transverses : pas de certificat sans revue humaine ; abonnement expiré → cours premium refusé.

**Formulaires**
- Une saisie invalide produit une erreur sur le bon champ, avec un message en français.

**Vues**
- Jamais seulement `status_code == 200`. Vérifie aussi le template utilisé, une donnée du contexte, et l'effet de bord : objet créé ou modifié, message affiché, redirection.
- `assertNumQueries` sur les vues de liste (protège contre le N+1).

**Permissions**
- Matrice d'accès (section 3).
- Objet d'autrui : un mentor qui modifie le créneau d'un autre mentor reçoit 404 ou 403.

**Tâches et IA** (fournisseur `mock` uniquement)
- Succès : `AIJob` passe à `SUCCEEDED` et l'objet cible est mis à jour.
- Échec (patch du fournisseur pour lever `AIServiceError`) : `AIJob` passe à `FAILED`, le repli métier s'applique (ex. message de forum en `EN_ATTENTE`), et le message affiché est compréhensible.
- JSON invalide : une seule relance, puis échec propre.

**Erreurs**
- Les templates 404 et 403 personnalisés sont bien utilisés.

## 3. Matrice d'accès (modèle à adapter)

```python
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounts.tests.factories import UserFactory

ANONYMOUS = None


class SlotCreateAccessTests(TestCase):
    url = reverse("mentoring:slot_create")
    expected = {
        ANONYMOUS: 302,
        User.Role.APPRENANT: 403,
        User.Role.MENTOR: 200,
        User.Role.FORMATEUR: 403,
        User.Role.RECRUTEUR: 403,
        User.Role.ETABLISSEMENT: 403,
        User.Role.ADMIN: 403,
    }

    def test_access_by_role(self):
        for role, status in self.expected.items():
            with self.subTest(role=role):
                self.client.logout()
                if role is not ANONYMOUS:
                    self.client.force_login(UserFactory(role=role))
                self.assertEqual(self.client.get(self.url).status_code, status)
```

Les statuts ci-dessus sont un exemple : la matrice réelle vient du tableau « URL → rôles autorisés » de `docs/modules/<app>.md`. Les deux doivent rester identiques.

## 4. Concurrence (`select_for_update`)

Un `TestCase` ne peut pas reproduire deux transactions simultanées. On teste donc la garantie au niveau du service : une seconde réservation sur un créneau déjà réservé lève `SlotAlreadyBooked`. À l'oral, on explique que `select_for_update` verrouille la ligne sous PostgreSQL pour le cas réellement simultané.

## 5. Le temps

Ne dépends pas de l'heure réelle. Construis les dates à partir de `timezone.now()` avec des marges nettes (`now + timedelta(days=2)`), ou fige l'heure avec `unittest.mock.patch("django.utils.timezone.now")`.

## 6. Anti-patterns à refuser

- `assertTrue(True)` ou un test sans assertion.
- Une boucle sur toutes les pages qui vérifie seulement le code 200.
- Un test qui recalcule le résultat avec la même logique que le code testé.
- Un mock de la fonction qu'on teste.
- Un test géant qui vérifie dix choses.
- Un appel réel à l'API d'IA dans les tests. Le fournisseur réel ne sert que dans les commandes `evaluate_*`.

## 7. Couverture

```
coverage run manage.py test
coverage report --skip-covered
coverage html
```

- Objectif : ≥ 75 % au global et ≥ 70 % par app. Migrations, settings, `manage.py`, `asgi.py` et `wsgi.py` sont exclus.
- Lis le rapport pour trouver les **branches de règles métier** non testées, pas pour courir après les lignes de l'admin.
- Résumé chiffré par app dans `docs/tests.md`, avec la date et la commande utilisée.
