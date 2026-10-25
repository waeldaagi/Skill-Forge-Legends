# Prédiction du risque d'abandon

Ce résultat est basé sur un jeu de données **synthétique** généré avec des règles réalistes, du bruit et une graine reproductible. Il ne représente pas des apprenants réels.

## Variables

Jours depuis la dernière activité, progression, score moyen aux quiz, sessions de mentorat, messages du forum et ancienneté du compte.

## Évaluation

Jeu de données : 200 observations ; test : 50 observations.

Modèle retenu : **logistic_regression**.

| Modèle | Accuracy | Précision | Rappel | F1 | ROC-AUC | Matrice |
|---|---:|---:|---:|---:|---:|---|
| logistic_regression | 0.96 | 0.75 | 0.75 | 0.75 | 0.8804 | `[[45, 1], [1, 3]]` |
| random_forest | 0.94 | 0.6 | 0.75 | 0.6667 | 0.8587 | `[[44, 2], [1, 3]]` |

Les seuils d'affichage sont : faible (< 0,34), moyen (0,34 à 0,66) et élevé (≥ 0,67).
