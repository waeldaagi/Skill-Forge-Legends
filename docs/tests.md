# Tests et couverture

## Lancer la suite

```
python manage.py test                 # ou : pytest
pytest --cov --cov-report=term --cov-report=html
```

Les deux commandes utilisent `config.settings.test` : Celery exécute les tâches dans le processus de test, le fournisseur d'IA est `mock` et aucun appel réseau n'est fait. Le rapport HTML est écrit dans `htmlcov/index.html`.

La CI GitHub Actions lance la même suite sur PostgreSQL 16 et Redis 7, refuse une couverture inférieure à 75 % et publie `htmlcov` comme artefact de chaque exécution.

Sont exclus de la mesure : migrations, settings, `manage.py`, `asgi.py`, `wsgi.py` et les dossiers `tests/` eux-mêmes.

## Résultats au 25/10/2026 (Phases 0, 1 et 2 intégrées, bugs de la Phase 1 corrigés)

Commande : `pytest --cov`, sur SQLite, branche `integration/phases-0-1-2`. Couverture des instructions et des branches.

| App | Responsable | Tests | Instructions | Non couvertes | Couverture |
|---|---|---|---|---|---|
| `core` | Wael | 87 | 478 | 2 | 99,4 % |
| `mentoring` | Wael | 110 | 602 | 4 | 99,0 % |
| `community` | Wael | 82 | 658 | 5 | 98,9 % |
| `accounts` | Taha | 32 | 213 | 1 | 98,7 % |
| `courses` | Taha | 82 | 876 | 16 | 97,4 % |
| `config` | — | — | 18 | 1 | 90,0 % |
| `assessment`, `payments`, `analytics` | Hamdi, Ismail | 0 | 22 | 3 | stubs |
| **Total** | | **393** | **2 867** | **32** | **98,4 %** |

Avant la correction des bugs relevés dans `docs/audit/integration-2026-10-25.md`, `courses/views.py` n'était couvert qu'à 65 % : les bugs se trouvaient précisément dans les parties non testées. Il l'est maintenant à 99 %. La suite tourne sans aucun avertissement de dépréciation (`pytest -W error::DeprecationWarning`). `assessment`, `payments` et `analytics` ne contiennent encore que les stubs des contrats entre modules (Phases 3 et 4).

## Ce que les tests prouvent

| Fichier | Règles vérifiées |
|---|---|
| `accounts/tests/test_models.py` | Le groupe suit le rôle à la création et au changement de rôle ; seul le rôle ADMIN ouvre l'admin Django ; `createsuperuser` crée un administrateur. |
| `accounts/tests/test_commands.py` | `setup_roles` crée un groupe par rôle, donne les permissions déclarées, peut être relancée, refuse une permission ou un rôle inconnus. |
| `accounts/tests/test_views.py` | Connexion, mot de passe faux, déconnexion ; lien « Mot de passe oublié » et envoi du lien ; e-mail obligatoire à l'inscription ; modification du profil, avatar trop lourd refusé ; profil public visible seulement s'il est activé ; établissement rejoint par un apprenant, code faux refusé, autres rôles refusés (403). |
| `courses/tests/test_permissions.py` | 26 URL × 6 rôles et l'anonyme ; pages du formateur sur le cours d'un autre : 404 ; inscription, chapitre terminé et réponse à un quiz réservés à l'apprenant. |
| `courses/tests/test_views.py` | Quiz premium refusé sans abonnement ; réponse forgée comptée fausse sans erreur ; progression affichée ; vidéo intégrée ou proposée en lien ; formateur non vérifié qui ne publie rien ; « Mes cours », brouillon visible de son seul formateur ; slug stable et unique ; CRUD des chapitres, ressources, quiz et questions ; ordre déjà pris et choix identiques refusés sans erreur ; fichier de plus de 5 Mo refusé ; chaque page du formateur s'ouvre. |
| `courses/tests/test_models.py` | Slug numéroté pour un titre déjà pris, conservé au renommage ; lien d'intégration YouTube et Vimeo, refus des autres sites. |
| `courses/tests/test_ai.py` | Schéma de génération : choix identiques, choix trop long et énoncés en double refusés ; une erreur d'écriture laisse les anciennes questions intactes. |
| `core/tests/test_validators.py` | Limite de 5 Mo (exactement 5 Mo accepté, au-delà refusé, fichier déjà stocké jamais relu) ; URL sans protocole complétée en https. |
| `core/tests/test_permissions.py` | Chaque mixin, pour chaque rôle autorisé et refusé ; l'objet d'un autre utilisateur donne 404. |
| `core/tests/test_ai_client.py` | Sortie validée par pydantic ; journalisation sans donnée personnelle ; timeout, erreurs HTTP et service injoignable ; une seule relance sur réponse invalide ; consigne anti-injection. |
| `core/tests/test_ai_gemini.py` | Clé dans l'en-tête, JSON imposé, modèle configurable, erreur 503, réponse bloquée, clé absente (réponses HTTP simulées). |
| `core/tests/test_ai_jobs.py` | Tâche lancée après la validation de la transaction ; succès ; échec avec repli ; deux relances sur erreur passagère ; aucune relance sur clé refusée ; erreur inattendue. |
| `core/tests/test_ai_status.py` | Statut réservé au propriétaire ; code 286 en fin de traitement ; zone `role="status"` qui interroge le serveur toutes les 2 s tant que le job tourne. |
| `core/tests/test_admin.py` | Journal des appels IA en lecture seule dans l'admin ; lisible par un administrateur grâce aux permissions de son groupe. |
| `core/tests/test_errors.py` | Handlers 403, 404 et 500 branchés ; page d'échec CSRF avec consigne. |
| `core/tests/test_forms.py` | Libellé, mention « (obligatoire) », classes Bootstrap, erreur reliée au champ par `aria-describedby`. |
| `core/tests/test_views.py` | Accueil, repères accessibles, un seul `<h1>`, navigation selon le rôle, `aria-current`. |
| `core/tests/test_health.py` | `/health/` : 200 si la base et Redis répondent, 503 sinon, jamais en cache. |
| `core/tests/test_emails.py` | Adresse d'expédition ; e-mail envoyé seulement après la validation de la transaction. |
| `core/tests/test_seed_demo.py` | Un compte par rôle avec le mot de passe de démo ; relançable sans doublon ; refus sans `DEMO_PASSWORD`. |
| `mentoring/tests/test_models.py` | Règles d'un créneau (futur, 30 à 120 min, sans chevauchement, bornes incluses) ; deux sessions actives sur un créneau refusées par la base. |
| `mentoring/tests/test_services.py` | Réservation verrouillée ; créneau déjà pris ; annulation à 2 h 01 acceptée et à 1 h 59 refusée ; transitions de statut ; avis ; fenêtre de la salle ; e-mails et rappel. |
| `mentoring/tests/test_views.py` | Chaque page : statut, gabarit, contexte, effet ; nombre de requêtes de l'annuaire constant. |
| `mentoring/tests/test_permissions.py` | 16 URL × 6 rôles et l'anonyme ; objet d'un autre participant : 404. |
| `community/tests/test_moderation_ai.py` | Message propre publié, spam masqué, message masqué pendant la vérification, échec de l'IA sans publication, seuil de confiance de 0,6, injection de prompt. |
| `community/tests/test_services.py` | Visibilité et ordre des messages, votes, réponse acceptée, signalements, décisions des modérateurs. |
| `community/tests/test_views.py` | Pages du forum, vote HTMX, file de modération (un formulaire de rejet par élément, id uniques) ; nombre de requêtes de la liste constant. |
| `community/tests/test_permissions.py` | 19 URL × 6 rôles et l'anonyme ; message d'un autre auteur : 404. |
| `community/tests/test_evaluate_moderation.py` | Rapport complet ; le fournisseur mock reproduit la baseline ; échecs d'appel comptés. |

## Lignes non couvertes

Les vues et la pagination sont entièrement couvertes. Restent, d'après `htmlcov/` :

- les `__str__` des modèles, utilisés par l'admin ;
- le retour anticipé de `AvailabilitySlot.clean()` quand un champ est déjà invalide ;
- la branche « widget caché » du rendu des formulaires et la route des médias, active seulement en `DEBUG` ;
- le double clic sur un vote (`IntegrityError` ignorée) et le repli d'un sujet supprimé avant sa vérification ;
- l'attente avant un nouvel essai dans `evaluate_moderation`, non testée pour ne pas ralentir la suite de 10 s ;
- les stubs des modules encore à écrire.
