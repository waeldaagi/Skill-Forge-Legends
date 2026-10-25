from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

ROLE_DENIED_MESSAGE = "Votre rôle ne donne pas accès à cette page."


class RoleRequiredMixin(LoginRequiredMixin):
    """Réserve une vue aux rôles de ``allowed_roles``.

    Visiteur anonyme : redirection vers la connexion. Rôle non autorisé : 403.
    """

    allowed_roles = ()

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role not in self.allowed_roles:
            raise PermissionDenied(ROLE_DENIED_MESSAGE)
        return super().dispatch(request, *args, **kwargs)


def role_required(*allowed_roles):
    """Équivalent de RoleRequiredMixin pour une vue fonction.

    Usage : ``@role_required(User.Role.MENTOR, User.Role.FORMATEUR)``.
    """

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.role not in allowed_roles:
                raise PermissionDenied(ROLE_DENIED_MESSAGE)
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


class OwnerRequiredMixin(LoginRequiredMixin):
    """Limite le queryset aux objets de l'utilisateur connecté (champ ``owner_field``).

    L'objet d'un autre utilisateur donne 404 : on ne révèle même pas qu'il existe.
    """

    owner_field = "owner"

    def get_queryset(self):
        return super().get_queryset().filter(**{self.owner_field: self.request.user})
