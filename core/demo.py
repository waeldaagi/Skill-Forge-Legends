from django.conf import settings

from accounts.models import User

# Domaine réservé aux tests (RFC 2606) : aucun e-mail de démo ne peut atteindre une vraie personne.
DEMO_EMAIL_DOMAIN = "skillforge.test"


def create_demo_user(username, first_name, last_name, role):
    """Crée ou remet à jour un compte de démo, avec le mot de passe DEMO_PASSWORD."""
    user, _ = User.objects.get_or_create(username=username)
    user.first_name = first_name
    user.last_name = last_name
    user.role = role
    user.email = f"{username}@{DEMO_EMAIL_DOMAIN}"
    user.set_password(settings.DEMO_PASSWORD)
    user.save()
    return user
