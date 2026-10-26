from django.apps import apps
from django.urls import reverse

# Clé de role_navigation pour un visiteur non connecté (catalogue public, par exemple).
ANONYMOUS = "ANONYME"


def navigation(request):
    """Liens de la navigation principale pour le rôle connecté, ou pour un visiteur anonyme.

    Chaque app les déclare dans l'attribut ``role_navigation`` de son AppConfig.
    """
    role = request.user.role if request.user.is_authenticated else ANONYMOUS
    nav_links = []
    for app_config in apps.get_app_configs():
        for label, url_name in getattr(app_config, "role_navigation", {}).get(role, []):
            url = reverse(url_name)
            nav_links.append({"label": label, "url": url, "is_current": request.path == url})
    return {"nav_links": nav_links}
