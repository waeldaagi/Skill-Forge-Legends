from django import forms
from django.utils import timezone

from .models import AvailabilitySlot, MentoringSession, MentorProfile, SessionReview

Status = MentoringSession.Status
DATETIME_LOCAL_FORMAT = "%Y-%m-%dT%H:%M"


class DateTimeLocalInput(forms.DateTimeInput):
    """Sélecteur date et heure natif du navigateur, par pas de 15 minutes."""

    input_type = "datetime-local"

    def __init__(self, attrs=None):
        super().__init__(attrs={"step": 900, **(attrs or {})}, format=DATETIME_LOCAL_FORMAT)


class MentorProfileForm(forms.ModelForm):
    class Meta:
        model = MentorProfile
        fields = ["title", "years_of_experience"]
        widgets = {"years_of_experience": forms.NumberInput(attrs={"min": 0, "max": 50})}


class AvailabilitySlotForm(forms.ModelForm):
    class Meta:
        model = AvailabilitySlot
        fields = ["start", "end"]
        widgets = {"start": DateTimeLocalInput(), "end": DateTimeLocalInput()}
        help_texts = {"end": "Entre 30 et 120 minutes après le début."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Le navigateur refuse déjà une date passée ; le modèle le revérifie côté serveur.
        now = timezone.localtime().strftime(DATETIME_LOCAL_FORMAT)
        for name in ("start", "end"):
            self.fields[name].widget.attrs["min"] = now


class BookingForm(forms.ModelForm):
    class Meta:
        model = MentoringSession
        fields = ["topic", "blocker_description"]
        widgets = {"blocker_description": forms.Textarea(attrs={"rows": 5})}
        help_texts = {
            "topic": "Une phrase, par exemple « Erreur 403 sur un formulaire HTMX ».",
            "blocker_description": "Ce que vous avez essayé et ce qui bloque : "
            "le mentor prépare la session à partir de ce texte.",
        }


class MentorNotesForm(forms.Form):
    mentor_notes = forms.CharField(
        label="Notes pour l'apprenant",
        required=False,
        max_length=2000,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Points vus, ressources, prochaines étapes.",
    )


class RefusalForm(forms.Form):
    mentor_notes = forms.CharField(
        label="Motif du refus",
        max_length=2000,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="L'apprenant le lira ; proposez si possible un autre mentor ou un autre moment.",
    )


class SessionReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        label="Note de la session",
        choices=[(5, "5 : très utile"), (4, "4"), (3, "3"), (2, "2"), (1, "1 : pas utile")],
        coerce=int,
        widget=forms.RadioSelect,
    )

    class Meta:
        model = SessionReview
        fields = ["rating", "comment"]
        widgets = {"comment": forms.Textarea(attrs={"rows": 4})}


class SlotFilterForm(forms.Form):
    periode = forms.ChoiceField(
        label="Période",
        required=False,
        choices=[("a_venir", "À venir"), ("passes", "Passés")],
    )
    etat = forms.ChoiceField(
        label="État",
        required=False,
        choices=[("", "Tous"), ("libres", "Libres"), ("reserves", "Réservés")],
    )


class SessionFilterForm(forms.Form):
    statut = forms.ChoiceField(
        label="Statut", required=False, choices=[("", "Tous"), *Status.choices]
    )
    periode = forms.ChoiceField(
        label="Période",
        required=False,
        choices=[("", "Toutes"), ("a_venir", "À venir"), ("passees", "Passées")],
    )


class MentorSearchForm(forms.Form):
    q = forms.CharField(label="Nom ou spécialité", required=False, max_length=80)
    disponible = forms.BooleanField(label="Avec un créneau libre", required=False)
