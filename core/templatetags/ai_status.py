from django import template

from core.ai.features import get_feature

register = template.Library()


@register.inclusion_tag("core/partials/ai_status_region.html")
def ai_job_status(job):
    """Zone de statut d'un AIJob, actualisée par HTMX : ``{% ai_job_status job %}``."""
    return {"job": job, "feature": get_feature(job.feature)}
