from core.ai import delimit_user_content

PROMPT_VERSION = "assessment-v1"

SYSTEM_PROMPT = (
    "Tu es un évaluateur technique de preuves de compétences. "
    "Tu notes la soumission selon la grille donnée, avec un score par critère. "
    "Tu renvoies des justifications concrètes et des axes d'amélioration actionnables."
)


def build_prompt(certification_title, instructions, criteria, text_response, repository_url):
    criteria_block = "\n".join(
        f"- {item['name']} ({item['weight']}%) : {item['description']}" for item in criteria
    )
    return (
        f"Certification : {certification_title}\n"
        f"Consignes : {instructions}\n"
        f"Grille :\n{criteria_block}\n\n"
        f"Dépôt : {repository_url or 'aucun'}\n"
        f"Preuve texte :\n{delimit_user_content(text_response or '')}"
    )
