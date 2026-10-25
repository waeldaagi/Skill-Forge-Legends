# Module catalogue et cours

Responsable : Taha. État au 25/10/2026 : Phase 1, intégrée avec les Phases 0 et 2 (branche `integration/phases-0-1-2`), bugs de l'audit d'intégration corrigés.

Le module `courses` couvre le catalogue public, les cours des formateurs, l’inscription des apprenants, la progression par chapitre et les quiz.

## Règles importantes

- Un formateur ne voit et ne modifie que ses propres cours ; le cours d'un autre formateur donne 404.
- Un formateur non vérifié (`User.is_verified`) prépare ses cours et ses quiz en brouillon, mais ne publie ni cours ni quiz.
- Le slug d'un cours est calculé une seule fois, à la création, avec un suffixe s'il est déjà pris (`docker`, `docker-2`) : renommer un cours ne casse pas ses liens.
- Un chapitre possède un ordre unique dans son cours, une question un ordre unique dans son quiz : le formulaire le vérifie et propose la première position libre.
- Une ressource contient exactement un fichier ou un lien. Les fichiers (ressources, image du cours) sont limités à 5 Mo, avec une liste blanche d'extensions.
- Une inscription et une progression sont uniques par utilisateur et par cours ou chapitre.
- La progression est calculée à partir des chapitres terminés, sans valeur stockée incohérente. L'apprenant inscrit la voit sur la page du cours.
- Un quiz publié contient des questions avec exactement quatre choix différents et une seule bonne réponse.
- Une génération IA reste en brouillon jusqu’à la validation du formateur ; un quiz publié doit être dépublié avant d'être régénéré.
- Un cours premium, ses chapitres et ses quiz exigent un abonnement actif (`user_can_access_course`). Le formateur relit toujours son propre cours, même en brouillon (`can_read_course`).

## Espace formateur

« Mes cours » (`/cours/formateur/cours/`) liste les cours du formateur, brouillons compris, avec le nombre de chapitres et le statut. Toutes les pages du formateur sont sous `formateur/` : aucun slug de cours ne peut les masquer.

| Objet | Créer | Modifier | Supprimer | Autre |
|---|---|---|---|---|
| Cours | `formateur/cours/nouveau/` | `<slug>/modifier/` | `<slug>/supprimer/` | publier et dépublier par le statut |
| Chapitre | `formateur/cours/<id>/chapitres/nouveau/` | `formateur/chapitres/<id>/modifier/` | `formateur/chapitres/<id>/supprimer/` | |
| Ressource | `formateur/chapitres/<id>/ressources/nouveau/` | `formateur/ressources/<id>/modifier/` | `formateur/ressources/<id>/supprimer/` | |
| Quiz | `formateur/chapitres/<id>/quiz/nouveau/` | `formateur/quiz/<id>/modifier/` | `formateur/quiz/<id>/supprimer/` | gérer, publier, dépublier, générer avec l'IA |
| Question | `formateur/quiz/<id>/questions/nouveau/` | `formateur/questions/<id>/modifier/` | `formateur/questions/<id>/supprimer/` | |

Chaque objet parent (cours, chapitre, quiz) est chargé après le contrôle de rôle, par une `cached_property` filtrée sur le formateur connecté. Une suppression passe toujours par une page de confirmation.

## Matrice d'accès

| URL | Anonyme | Apprenant | Formateur | Autres rôles |
|---|---|---|---|---|
| Catalogue, détail d'un cours publié | 200 | 200 | 200 | 200 |
| Chapitre, quiz d'un cours gratuit publié | connexion | 200 | 200 (aperçu du quiz) | 200 (aperçu du quiz) |
| Inscription, chapitre terminé, réponse à un quiz (POST) | connexion | 302 | 403 | 403 |
| Créer un cours, « Mes cours » | connexion | 403 | 200 | 403 |
| Pages du formateur sur le cours d'un autre | connexion | 403 | 404 | 403 |
| Cours, chapitre ou quiz en brouillon d'un autre | — | 404 | 404 | 404 |
| Quiz premium sans abonnement | connexion | 404 | 404 | 404 |

Vérifié dans `courses/tests/test_permissions.py` (26 URL × 6 rôles et l'anonyme).

## Quiz et génération IA

Le formateur peut créer un quiz manuellement, ajouter, modifier ou supprimer ses questions, puis le publier après vérification. L’apprenant voit le quiz uniquement quand le cours et le quiz sont publiés, et reçoit son score ainsi que le corrigé après sa tentative. Une réponse forgée (valeur non numérique, choix d'une autre question) compte comme fausse, sans erreur.

La génération utilise le contenu du chapitre et le texte des ressources PDF. Le fournisseur est configuré par `AI_PROVIDER` dans `.env` (`mock` pour une démonstration hors ligne, `gemini` pour Gemini). La clé reste dans `AI_API_KEY` et n'est jamais enregistrée dans le dépôt. Le traitement est lancé par Celery et son état est affiché par le statut IA. Une erreur 401/403, 404, 429, 503 ou un délai dépassé laisse le formateur compléter le quiz manuellement.

Le schéma pydantic `GeneratedQuiz` refuse deux choix identiques dans une question, un choix de plus de 300 caractères (taille du champ en base) et deux questions de même énoncé : une telle sortie est redemandée une fois par le socle, puis le job échoue proprement. Les questions générées remplacent les anciennes dans une seule transaction.

La commande suivante mesure la conformité JSON et la latence sur cinq exemples :

```text
python manage.py evaluate_quiz_generation --provider mock [--output chemin/du/rapport.md]
```

Le rapport est écrit par défaut dans `docs/ia/quiz_generation.md` ; les tests l'écrivent dans un dossier temporaire. La conformité du schéma ne remplace pas la relecture pédagogique du formateur.

## Vidéo d'un chapitre

Un lien YouTube (`watch?v=`, `youtu.be`, `shorts`, `embed`) ou Vimeo est converti en lien d'intégration (`Chapter.video_embed_url`) et affiché dans une iframe titrée. L'iframe porte `referrerpolicy="strict-origin-when-cross-origin"` : sans référent, YouTube refuse la lecture (erreur 153). Un autre site est proposé en lien, jamais en iframe. Une URL saisie sans protocole est enregistrée en `https://`.

## Démonstration

La commande `python manage.py seed_demo` crée le cours « Django : du modèle au déploiement », un quiz de démonstration, et marque le formateur de démo comme vérifié.

## Questions du jury

- Pourquoi utiliser `select_related` et `prefetch_related` dans le catalogue ?
- Pourquoi le contrôle de propriété est-il réalisé dans le queryset du formateur ?
- Pourquoi la contrainte « exactement une source » est-elle doublée par `clean()` ?
- Pourquoi un quiz généré par l'IA reste-t-il en brouillon ?
- Pourquoi l'unicité de l'ordre d'un chapitre est-elle vérifiée dans le formulaire alors qu'une contrainte existe en base ? (Le cours n'est pas un champ du formulaire : Django ne valide pas seul une contrainte qui porte sur un champ exclu, et la base lèverait une `IntegrityError`.)
- Pourquoi le slug n'est-il pas recalculé quand le titre change ?
- Pourquoi charger le chapitre parent dans une `cached_property` plutôt que dans `dispatch()` ? (Dans `dispatch()`, il serait chargé avant le contrôle de rôle : un anonyme provoquait une erreur 500.)
