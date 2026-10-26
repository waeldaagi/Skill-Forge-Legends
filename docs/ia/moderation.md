# Modération automatique du forum

Fonctionnalité IA du module `community` (responsable : Wael Daagi). Code : `community/ai/`. Commande d'évaluation : `python manage.py evaluate_moderation`.

## 1. Cas d'usage

Chaque sujet ou réponse publié sur le forum est classé par l'IA dans l'une de quatre catégories : `OK`, `SPAM`, `TOXIQUE` ou `HORS_SUJET`. La décision aidée est la publication :

- `OK` avec une confiance d'au moins 0,6 : le message est publié sans attendre un modérateur ;
- toute autre étiquette, ou un `OK` hésitant : le message reste masqué et part dans la file de modération, avec l'avis et le motif de l'IA ;
- échec de l'IA : le message reste masqué, en attente d'un humain.

Le besoin est réel : sans filtre, un modérateur doit relire chaque message avant publication, ou le forum publie le spam et les insultes. L'IA trie ; l'humain garde la décision sur tout ce qui n'est pas clairement conforme.

Fournisseur : Gemini (`gemini-3.5-flash-lite`), appelé en tâche Celery par le socle `core/ai/`. Prompt : `community/ai/prompts.py`, version `moderation-v1`. Sortie validée par le schéma pydantic `ModerationOutput` (étiquette, confiance entre 0 et 1, motif).

## 2. Jeu de données

| Élément | Valeur |
|---|---|
| Fichier | `community/fixtures/moderation_dataset.json` |
| Taille | 80 messages en français |
| Répartition | 20 `OK`, 20 `SPAM`, 20 `TOXIQUE`, 20 `HORS_SUJET` |
| Source | Messages écrits pour le projet, dans le contexte du forum (questions Django, Docker, mentorat, vie étudiante à Tunis) |
| Étiquetage | Première version rédigée avec un assistant de génération de code ; à relire et corriger par l'étudiant responsable (relecture non faite au 25/10/2026) |

Le jeu contient des cas choisis pour piéger une approche par mots-clés :

- `OK` qui contiennent des mots trompeurs : l'instruction `match` de Python, « null=True », « valeur nulle », « tutoriel gratuit », une critique polie d'un chapitre ;
- `SPAM` sans lien ni mot-clé : services payants proposés par message privé, vente de comptes, groupe Telegram payant ;
- `TOXIQUE` sans insulte du dictionnaire : mépris (« le développement ce n'est pas pour les gens comme toi »), menace, moquerie (« ton code est aussi lent que ton cerveau ») ;
- `HORS_SUJET` sans mot-clé : nouvel iPhone, concert, voiture, conseils de sommeil avant un examen.

## 3. Résultats

Mesure du 26/10/2026 à 02 h 17, commande `python manage.py evaluate_moderation --provider gemini --pause 2`.

Fournisseur `gemini`, modèle `gemini-3.5-flash-lite`, prompt `moderation-v1`, 80 messages, 0 échec d'appel. Une première mesure, le 25/10/2026 à 18 h 15, avait donné exactement les mêmes étiquettes pour les 80 messages : le classement est stable d'une exécution à l'autre.

| Classe | Précision | Rappel | F1 | Effectif |
|---|---|---|---|---|
| OK | 1,000 | 1,000 | 1,000 | 20 |
| SPAM | 1,000 | 1,000 | 1,000 | 20 |
| TOXIQUE | 1,000 | 1,000 | 1,000 | 20 |
| HORS_SUJET | 1,000 | 1,000 | 1,000 | 20 |
| Moyenne macro | 1,000 | 1,000 | 1,000 | 80 |

Matrice de confusion de l'IA (lignes : étiquette attendue, colonnes : étiquette prédite) :

| | OK | SPAM | TOXIQUE | HORS_SUJET |
|---|---|---|---|---|
| OK | 20 | 0 | 0 | 0 |
| SPAM | 0 | 20 | 0 | 0 |
| TOXIQUE | 0 | 0 | 20 | 0 |
| HORS_SUJET | 0 | 0 | 0 | 20 |

Comparaison avec la baseline par mots-clés (`community/ai/moderation.py`, `keyword_label`) :

| Méthode | Exactitude | F1 macro |
|---|---|---|
| IA (Gemini) | 1,000 | 1,000 |
| Mots-clés | 0,650 | 0,663 |

Décision de publication, avec la règle de production (`is_published_automatically` : étiquette `OK` et confiance d'au moins 0,6) :

| Indicateur | Nombre | Taux |
|---|---|---|
| Publiés sans modérateur | 20 | 25,0 % |
| Envoyés en relecture humaine | 60 | 75,0 % |
| Messages conformes envoyés en relecture | 0 | 0,0 % des 20 messages conformes |
| Messages non conformes publiés à tort | 0 | 0,0 % des 60 messages non conformes |

Avec la baseline par mots-clés (fournisseur `mock`), 27 des 60 messages non conformes seraient publiés à tort, soit 45,0 %.

Latence d'un classement (appel réussi, relance éventuelle pour JSON invalide comprise) :

| Moyenne | Médiane | p95 | Maximum |
|---|---|---|---|
| 1 120 ms | 1 072 ms | 1 434 ms | 1 671 ms |

## 4. Lecture des résultats

La baseline se trompe sur 28 messages sur 80. Elle laisse passer comme `OK` 12 messages hors sujet, 10 messages toxiques et 5 spams qui ne contiennent aucun de ses mots-clés, et elle classe hors sujet la question sur l'instruction `match` de Python. Gemini classe correctement ces 28 messages : le contexte compte plus que le vocabulaire.

Ce score parfait ne doit pas être présenté comme une performance garantie :

- les 80 messages ont été écrits pour le projet, par un seul auteur, avec des intentions nettes ; un forum réel contient de l'ironie, des messages mêlant plusieurs catégories, des fautes et du dialecte tunisien ;
- les messages ont été rédigés avec un assistant de génération de texte, et c'est un autre modèle de langage qui les classe : leur style lui est familier, ce qui peut flatter le résultat ;
- avec 20 messages par classe, une seule erreur ferait déjà perdre 0,05 de rappel sur une classe.

La latence, autour d'une seconde, est acceptable pour une vérification faite en tâche Celery : l'auteur n'attend pas la réponse de l'IA pour continuer, et la zone de statut s'actualise toutes les 2 s.

## 5. Limites et améliorations

- **Relire les étiquettes** (à faire par l'étudiant responsable) et ajouter une quarantaine de messages vraiment ambigus : ironie, critique vive mais polie, auto-promotion légère d'un projet personnel, messages en dialecte ou en franco-arabe.
- **Charge des modérateurs.** Mesurée depuis le 26/10/2026 : aucun message conforme n'est tombé sous le seuil de 0,6. Sur des messages ambigus, ce taux montera ; c'est lui qu'il faudra suivre.
- **Répéter la mesure.** Deux exécutions, à huit heures d'intervalle, donnent les mêmes 80 étiquettes. Une troisième, après l'ajout de messages ambigus, dira si cette stabilité tient.
- **Suivre la production.** `AICallLog` enregistre la durée et le résultat de chaque appel ; le tableau de bord administrateur (Phase 4) affichera la latence p95 et le taux d'échec de la fonctionnalité `moderation`.
