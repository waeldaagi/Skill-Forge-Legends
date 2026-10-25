from django import forms

from .models import Reply, Report, Thread


class ThreadForm(forms.ModelForm):
    class Meta:
        model = Thread
        fields = ["title", "content"]
        widgets = {"content": forms.Textarea(attrs={"rows": 8})}
        help_texts = {
            "title": "Résumez le problème en une phrase.",
            "content": "Ce que vous avez essayé, le message d'erreur exact, ce que vous attendiez.",
        }


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
    resolu = forms.ChoiceField(
        label="État",
        required=False,
        choices=[("", "Tous"), ("non", "Sans solution"), ("oui", "Résolus")],
    )
