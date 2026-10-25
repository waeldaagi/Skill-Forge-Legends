from django import forms
from django.test import SimpleTestCase


class SessionRequestForm(forms.Form):
    topic = forms.CharField(label="Sujet", max_length=80, help_text="Une phrase suffit.")
    level = forms.ChoiceField(
        label="Niveau", choices=[("debutant", "Débutant"), ("avance", "Avancé")]
    )
    recorded = forms.BooleanField(label="Enregistrer la session", required=False)


class FormRendererTests(SimpleTestCase):
    def test_required_field_is_announced_in_text_not_only_by_color(self):
        html = str(SessionRequestForm())

        self.assertInHTML(
            '<label class="form-label" for="id_topic">'
            'Sujet <span class="sf-required">(obligatoire)</span></label>',
            html,
        )

    def test_optional_checkbox_has_no_required_mention(self):
        html = str(SessionRequestForm())

        self.assertInHTML(
            '<label class="form-check-label" for="id_recorded">Enregistrer la session</label>',
            html,
        )

    def test_widgets_receive_their_bootstrap_class(self):
        html = str(SessionRequestForm())

        self.assertInHTML(
            '<input type="checkbox" name="recorded" class="form-check-input" id="id_recorded">',
            html,
        )
        self.assertIn('<select name="level" class="form-select"', html)

    def test_error_is_linked_to_its_field_for_screen_readers(self):
        html = str(SessionRequestForm(data={"topic": "", "level": "debutant"}))

        self.assertInHTML(
            '<input type="text" name="topic" maxlength="80" class="form-control" required '
            'aria-invalid="true" aria-describedby="id_topic_helptext id_topic_error" '
            'id="id_topic">',
            html,
        )
        self.assertInHTML(
            '<div class="invalid-feedback d-block" id="id_topic_error">'
            "Ce champ est obligatoire.</div>",
            html,
        )
