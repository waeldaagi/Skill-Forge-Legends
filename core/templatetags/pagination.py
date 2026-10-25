from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def page_query(context, page_number):
    """Lien vers une autre page de la liste, filtres conservés : « ?statut=CONFIRMEE&page=2 »."""
    params = context["request"].GET.copy()
    params["page"] = page_number
    return f"?{params.urlencode()}"
