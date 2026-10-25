from django.conf import settings

from accounts.models import User


def create_demo_user(username, first_name, last_name, role):
    """Crée ou met à jour un compte de démonstration idempotent."""
    user, _ = User.objects.get_or_create(
        username=username,
        defaults={
            "first_name": first_name,
            "last_name": last_name,
            "email": f"{username}@skillforge.test",
            "role": role,
        },
    )
    user.first_name = first_name
    user.last_name = last_name
    user.email = f"{username}@skillforge.test"
    user.role = role
    user.is_active = True
    user.set_password(settings.DEMO_PASSWORD)
    user.save()
    return user
