import json

from core.ai.features import get_feature


class MockProvider:
    """Fournisseur hors ligne et déterministe : la réponse vient de la fonctionnalité elle-même."""

    name = "mock"
    model = "mock"

    def generate(self, *, feature, system, prompt, timeout):
        return json.dumps(get_feature(feature).mock_output(prompt), ensure_ascii=False)
