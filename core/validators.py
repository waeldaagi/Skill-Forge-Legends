from django.core.exceptions import ValidationError

MAX_UPLOAD_SIZE = 5 * 1024 * 1024
MAX_UPLOAD_LABEL = "5 Mo"


def validate_upload_size(file):
    """Refuse un fichier envoyé de plus de 5 Mo (avatars, images, ressources)."""
    # Un fichier déjà stocké a été contrôlé à son envoi : on ne relit pas le stockage,
    # qui peut ne plus le contenir (base de démo copiée sans le dossier media).
    if getattr(file, "_committed", False):
        return
    if file.size > MAX_UPLOAD_SIZE:
        raise ValidationError(
            f"Le fichier dépasse la taille maximale de {MAX_UPLOAD_LABEL}.", code="file_too_large"
        )
