from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Etablissement, User


class RegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [
            choice
            for choice in User.Role.choices
            if choice[0]
            in {
                User.Role.APPRENANT,
                User.Role.MENTOR,
                User.Role.FORMATEUR,
                User.Role.RECRUTEUR,
            }
        ]


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "avatar",
            "bio",
            "phone",
            "skills",
            "is_public_profile",
        )
        widgets = {"bio": forms.Textarea(attrs={"rows": 4})}


class JoinInstitutionForm(forms.Form):
    invite_code = forms.CharField(label="Code d’invitation", max_length=16, min_length=6)

    def clean_invite_code(self):
        code = self.cleaned_data["invite_code"].strip().upper()
        try:
            return Etablissement.objects.get(invite_code=code)
        except Etablissement.DoesNotExist as error:
            raise forms.ValidationError("Ce code d’invitation est invalide.") from error
