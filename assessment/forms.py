from django import forms

from accounts.models import Skill
from core.forms import https_url_formfield

from .models import Certification, Criterion, HumanReview, Submission


class CertificationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk is None:
            self.fields["is_active"].initial = False

    class Meta:
        model = Certification
        fields = ["course", "title", "instructions", "passing_score", "max_attempts", "is_active"]
        widgets = {"instructions": forms.Textarea(attrs={"rows": 6})}


class CriterionForm(forms.ModelForm):
    class Meta:
        model = Criterion
        fields = ["name", "description", "weight"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ["text_response", "repository_url", "attachment"]
        widgets = {"text_response": forms.Textarea(attrs={"rows": 8})}
        formfield_callback = https_url_formfield


class HumanReviewForm(forms.ModelForm):
    class Meta:
        model = HumanReview
        fields = ["final_score", "decision", "comment", "overrides_ai"]
        widgets = {"comment": forms.Textarea(attrs={"rows": 4})}


class TalentSearchForm(forms.Form):
    q = forms.CharField(label="Recherche", required=False, max_length=80)
    skill = forms.ModelChoiceField(
        label="Compétence",
        queryset=Skill.objects.order_by("name"),
        required=False,
        empty_label="Toutes",
    )
    certification = forms.ModelChoiceField(
        label="Certification",
        queryset=Certification.objects.filter(is_active=True).order_by("title"),
        required=False,
        empty_label="Toutes",
    )


class RecruiterContactForm(forms.Form):
    subject = forms.CharField(label="Sujet", max_length=150)
    message = forms.CharField(label="Message", widget=forms.Textarea(attrs={"rows": 5}))
