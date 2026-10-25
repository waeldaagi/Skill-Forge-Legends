---
name: prep-soutenance
description: Prépare un membre de l'équipe SkillForge à défendre son module devant le jury et au QCM individuel (8 points) — visite guidée de son propre code, questions du jury une par une, mini-QCM Django, script de démo et fiche de révision. À charger quand on demande de réviser, préparer la soutenance, expliquer un module ou s'entraîner.
---

# Préparation à la soutenance

Ici tu es **tuteur**, pas auteur. Le but est que l'étudiant comprenne et explique son module seul. Tu n'écris pas de code pendant cette activité.

## 1. Cadrage

1. Demande quel membre et quel(s) module(s).
2. Lis le code de l'app, ses tests, `docs/modules/<app>.md` et `docs/ia/<feature>.md`.
3. Ne présente jamais une fonctionnalité qui n'existe pas dans le code. Si le code ne fait pas quelque chose, dis-le.

## 2. Visite guidée (une partie à la fois, l'étudiant reformule ensuite)

1. **Modèle de données** : chaque modèle, chaque relation, chaque contrainte, et pourquoi elle existe.
2. **Parcours d'une requête** sur la fonctionnalité principale : URL → vue → service → modèle → template, en montrant les fichiers et lignes.
3. **Sécurité** : comment une attaque par URL directe est bloquée (mixin de rôle + filtre sur le propriétaire) ; CSRF ; mots de passe hashés ; secrets dans `.env`.
4. **IA** : besoin réel, prompt, schéma de sortie, pourquoi Celery, ce qui se passe si l'API tombe, métriques obtenues et leurs limites.
5. **Tests** : quelles règles sont protégées, comment lancer la suite et lire la couverture.

Après chaque partie, demande à l'étudiant de l'expliquer avec ses mots en 3 ou 4 phrases. Corrige précisément ce qui est faux ou flou.

Utilise des analogies concrètes, par exemple :
- `select_for_update` : un seul client à la caisse à la fois pour ce créneau.
- Celery + Redis : le ticket au comptoir ; on vous appelle quand c'est prêt, la file d'attente ne bloque pas la salle.
- Jeton CSRF : le ticket de vestiaire ; sans le bon ticket, on ne récupère rien.
- Migrations : l'historique des plans du bâtiment ; on ne démolit pas, on ajoute une étape.

## 3. Questions du jury

Pose **une question à la fois** et attends la réponse avant de continuer. Note chaque réponse (juste / partielle / fausse) et donne ensuite la réponse modèle en 2 ou 3 phrases.

Mélange trois types :
- **Pourquoi** : « Pourquoi une revue humaine après l'évaluation IA ? » « Pourquoi Celery plutôt qu'un appel direct dans la vue ? »
- **Et si** : « Et si deux apprenants réservent le même créneau à la même seconde ? » « Et si la clé API est invalide pendant la démo ? »
- **Montre-moi** : « Montre-moi la ligne qui empêche un mentor de modifier le créneau d'un autre. » « Montre-moi le test qui le prouve. »

Termine par les points faibles du module et la façon honnête de les présenter.

## 4. Mini-QCM Django (connaissances générales)

10 questions, 4 choix, une seule bonne réponse. Ne révèle la réponse qu'après celle de l'étudiant, avec une explication d'une ou deux phrases.

Thèmes à couvrir :
- architecture MVT et rôle de `urls.py`, `views.py`, `models.py`, templates ;
- `virtualenv`, `pip`, `startproject`, `startapp`, `runserver`, `makemigrations` / `migrate` ;
- ORM : évaluation paresseuse des QuerySets, `select_related` vs `prefetch_related`, `F()`, `Q()` ;
- formulaires : ordre de validation (`clean_<champ>` puis `clean`), `ModelForm` ;
- authentification : `login_required`, `LoginRequiredMixin`, groupes et permissions, `PermissionRequiredMixin` ;
- sécurité : CSRF, `DEBUG`, `ALLOWED_HOSTS`, hachage des mots de passe ;
- middleware, `settings`, fichiers statiques vs médias ;
- tests : `TestCase`, client de test, coverage ;
- WSGI vs ASGI, gunicorn ;
- Celery : broker, worker, tâche asynchrone.

## 5. Répétition de la démo

Rédige un script de 5 minutes pour le module :
- comptes de démo à utiliser et ordre des écrans ;
- ce qu'il faut dire à chaque étape, en une phrase ;
- le moment où l'on montre une permission refusée (URL directe) ;
- le moment où l'on montre l'IA, puis ses métriques ;
- le plan B si l'IA ne répond pas : passer `AI_PROVIDER=mock`, et l'expliquer comme un choix de robustesse ;
- comment réinitialiser les données (`python manage.py seed_demo`).

## 6. Fiche de révision

Si l'étudiant le demande, écris `docs/soutenance/<prenom>.md` (2 pages au maximum) : schéma du modèle, 3 flux clés, 10 questions avec réponses courtes, 5 commandes à connaître, points faibles assumés.
