class AIServiceError(Exception):
    """Échec d'un appel IA.

    ``user_message`` s'affiche tel quel ; ``retryable`` autorise la tâche Celery à relancer.
    """

    def __init__(self, error_type, user_message, *, retryable=False):
        super().__init__(f"{error_type} : {user_message}")
        self.error_type = error_type
        self.user_message = user_message
        self.retryable = retryable
