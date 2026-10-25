from django.apps import apps
from django.urls import reverse


def navigation(request):
    """Liens de la navigation principale pour le rôle connecté.

    Chaque app les déclare dans l'attribut ``role_navigation`` de son AppConfig.
    """
    if not request.user.is_authenticated:
        return {"nav_links": []}
    nav_links = []
    for app_config in apps.get_app_configs():
        role_links = getattr(app_config, "role_navigation", {}).get(request.user.role, [])
        for label, url_name in role_links:
            url = reverse(url_name)
            nav_links.append({"label": label, "url": url, "is_current": request.path == url})
    return {"nav_links": nav_links}
