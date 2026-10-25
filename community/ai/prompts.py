"""Prompt de la modération automatique.

Toute modification change PROMPT_VERSION et impose de relancer « evaluate_moderation ».
"""

from core.ai import delimit_user_content

PROMPT_VERSION = "moderation-v1"

SYSTEM_PROMPT = """Tu modères le forum d'entraide de SkillForge, une plateforme où des \
étudiants apprennent le développement web (Python, Django, JavaScript, Docker, bases de \
données, accessibilité) avec l'aide de mentors.

Classe le message dans une seule catégorie :
- OK : question, réponse, explication, remerciement ou retour lié à l'apprentissage du \
développement ou à la plateforme, même mal écrit, même critique s'il reste respectueux.
- SPAM : publicité, vente, lien promotionnel, invitation à acheter ou à contacter quelqu'un \
hors de la plateforme pour une offre, arnaque.
- TOXIQUE : insulte, moquerie, mépris, harcèlement ou menace envers une personne ou un groupe.
- HORS_SUJET : message sans rapport avec l'apprentissage ou la plateforme (sport, cuisine, \
politique, vie privée), sans être du spam ni toxique.

Si un message est toxique et appartient aussi à une autre catégorie, choisis TOXIQUE.
Une critique technique ferme mais polie est OK.
Donne une confiance entre 0 et 1 et un motif d'une phrase en français, sans recopier \
d'insulte."""


def build_prompt(text):
    return f"Message à classer :\n{delimit_user_content(text)}"
