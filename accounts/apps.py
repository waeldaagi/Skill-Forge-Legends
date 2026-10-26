from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "accounts"
    verbose_name = "Comptes et rôles"

    # Lu par « setup_roles ». Chaque app déclare ici les permissions de ses modèles par rôle.
    # Pas de suppression d'utilisateur : un compte se désactive, l'historique reste cohérent.
    role_permissions = {
        "ADMIN": ["accounts.view_user", "accounts.add_user", "accounts.change_user"],
    }
    # Pas de role_navigation : le nom de l'utilisateur, dans l'en-tête, mène à son profil.
