from django.contrib.auth.models import Group


def assign_role_group(user):
    """Place l'utilisateur dans le groupe de son rôle et le retire des groupes des autres rôles."""
    other_role_groups = Group.objects.filter(name__in=user.Role.values).exclude(name=user.role)
    user.groups.remove(*other_role_groups)
    group, _ = Group.objects.get_or_create(name=user.role)
    user.groups.add(group)
