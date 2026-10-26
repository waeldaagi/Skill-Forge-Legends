from django import forms

from accounts.models import Skill
from courses.models import Course

from .models import Reply, Report, Thread


def published_courses():
    return Course.objects.filter(status=Course.Status.PUBLISHED)


class ThreadForm(forms.ModelForm):
    class Meta:
        model = Thread
        fields = ["title", "content", "course", "tags"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 8}),
            "tags": forms.CheckboxSelectMultiple,
        }
        help_texts = {
            "title": "Résumez le problème en une phrase.",
            "content": "Ce que vous avez essayé, le message d'erreur exact, ce que vous attendiez.",
            "course": "Facultatif : le cours auquel se rapporte la question.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course"].queryset = published_courses()
        self.fields["course"].empty_label = "Aucun cours en particulier"


class ReplyForm(forms.ModelForm):
    class Meta:
        model = Reply
        fields = ["content"]
        labels = {"content": "Votre réponse"}
        widgets = {"content": forms.Textarea(attrs={"rows": 5})}


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ["reason", "details"]
        widgets = {
            "reason": forms.RadioSelect,
            "details": forms.Textarea(attrs={"rows": 3}),
        }


class RejectionForm(forms.Form):
    reason = forms.CharField(
        label="Motif du rejet",
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="L'auteur lira ce motif.",
    )


class ThreadSearchForm(forms.Form):
    q = forms.CharField(label="Rechercher dans les sujets", required=False, max_length=80)
    course = forms.ModelChoiceField(
        label="Cours", queryset=published_courses(), required=False, empty_label="Tous les cours"
    )
    tag = forms.ModelChoiceField(
        label="Tag", queryset=Skill.objects.all(), required=False, empty_label="Tous les tags"
    )
    resolu = forms.ChoiceField(
        label="État",
        required=False,
        choices=[("", "Tous"), ("non", "Sans solution"), ("oui", "Résolus")],
    )
