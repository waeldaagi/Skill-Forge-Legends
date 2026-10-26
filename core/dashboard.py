from django.apps import apps
from django.utils.module_loading import import_string


def dashboard_panels(user):
    """Panneaux de l'accueil d'un utilisateur connecté, dans l'ordre d'INSTALLED_APPS.

    Chaque app déclare dans son AppConfig ``dashboard_panel = "<app>.dashboard.panel"``.
    ``panel(user)`` renvoie un dict avec la clé ``template``, ou None si le rôle n'a rien à voir.
    """
    panels = []
    for app_config in apps.get_app_configs():
        panel_path = getattr(app_config, "dashboard_panel", None)
        if panel_path:
            panel = import_string(panel_path)(user)
            if panel:
                panels.append(panel)
    return panels
