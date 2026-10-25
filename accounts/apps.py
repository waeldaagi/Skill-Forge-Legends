from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "accounts"
    verbose_name = "Comptes et rôles"

    # Lu par « setup_roles ». Chaque app déclare ici les permissions de ses modèles par rôle.
    # Pas de suppression d'utilisateur : un compte se désactive, l'historique reste cohérent.
    role_permissions = {
        "ADMIN": ["accounts.view_user", "accounts.add_user", "accounts.change_user"],
    }
    role_navigation = {
        "APPRENANT": [("Mon profil", "accounts:profile")],
        "MENTOR": [("Mon profil", "accounts:profile")],
        "FORMATEUR": [("Mon profil", "accounts:profile")],
        "RECRUTEUR": [("Mon profil", "accounts:profile")],
        # Le lien « Administration » est déjà déclaré par core.
        "ADMIN": [("Mon profil", "accounts:profile")],
        "ETABLISSEMENT": [("Mon profil", "accounts:profile")],
    }
