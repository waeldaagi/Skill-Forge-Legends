# Module catalogue et cours

Le module `courses` couvre le catalogue public, les cours des formateurs, l’inscription des apprenants, la progression par chapitre et les quiz.

## Règles importantes

- Un formateur ne voit et ne modifie que ses propres cours.
- Un chapitre possède un ordre unique dans son cours.
- Une ressource contient exactement un fichier ou un lien.
- Une inscription et une progression sont uniques par utilisateur et par cours ou chapitre.
- La progression est calculée à partir des chapitres terminés, sans valeur stockée incohérente.
- Un quiz publié contient des questions avec exactement quatre choix et une seule bonne réponse.
- Une génération IA reste en brouillon jusqu’à la validation du formateur.

## Quiz et génération IA

Le formateur peut créer un quiz manuellement, ajouter ou modifier ses questions, puis le publier
après vérification. L’apprenant voit le quiz uniquement quand le cours et le quiz sont publiés,
et reçoit son score ainsi que le corrigé après sa tentative.

La génération utilise le contenu du chapitre et le texte des ressources PDF. Le fournisseur est
configuré par `AI_PROVIDER` dans `.env` (`mock` pour une démonstration hors ligne, `gemini` pour
Gemini). La clé reste dans `AI_API_KEY` et n'est jamais enregistrée dans le dépôt. Le traitement
est lancé par Celery et son état est affiché par le statut IA. Une erreur 401/403, 404, 429,
503 ou un délai dépassé laisse le formateur compléter le quiz manuellement.

La commande suivante mesure la conformité JSON et la latence sur cinq exemples :

```text
python manage.py evaluate_quiz_generation --provider mock
```

Le rapport est écrit dans `docs/ia/quiz_generation.md`. La conformité du schéma ne remplace pas
la relecture pédagogique du formateur.

## Démonstration

La commande `python manage.py seed_demo` crée le cours « Django : du modèle au déploiement » et un quiz de démonstration.

## Questions du jury

- Pourquoi utiliser `select_related` et `prefetch_related` dans le catalogue ?
- Pourquoi le contrôle de propriété est-il réalisé dans le queryset du formateur ?
- Pourquoi la contrainte « exactement une source » est-elle doublée par `clean()` ?
- Pourquoi un quiz généré par l'IA reste-t-il en brouillon ?
