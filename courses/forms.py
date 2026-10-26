from django import forms
from django.db import transaction

from core.forms import https_url_formfield

from .models import Category, Chapter, Choice, Course, Question, Quiz, Resource
from .services import UNVERIFIED_TRAINER_MESSAGE

CHOICE_FIELDS = ("choice_1", "choice_2", "choice_3", "choice_4")


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ("title", "description", "level", "category", "image", "is_premium", "status")
        widgets = {"description": forms.Textarea(attrs={"rows": 6})}

    def __init__(self, *args, trainer, **kwargs):
        super().__init__(*args, **kwargs)
        self.trainer = trainer
        self.fields["category"].empty_label = "Choisissez une catégorie"
        self.fields["level"].choices = [("", "Choisissez un niveau"), *Course.Level.choices]

    def clean_status(self):
        status = self.cleaned_data["status"]
        if status == Course.Status.PUBLISHED and not self.trainer.is_verified:
            raise forms.ValidationError(UNVERIFIED_TRAINER_MESSAGE)
        return status


class ChapterForm(forms.ModelForm):
    """L'instance reçue porte déjà son cours : l'ordre est contrôlé dans ce cours."""

    class Meta:
        model = Chapter
        fields = ("title", "order", "content", "video_url")
        widgets = {"content": forms.Textarea(attrs={"rows": 10})}
        help_texts = {
            "video_url": "Lien YouTube ou Vimeo : la vidéo s'affiche dans le chapitre.",
        }
        formfield_callback = https_url_formfield

    def clean_order(self):
        # Le cours n'est pas un champ du formulaire : Django ne vérifie pas seul la contrainte.
        order = self.cleaned_data["order"]
        taken = Chapter.objects.filter(course_id=self.instance.course_id, order=order)
        if taken.exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Un autre chapitre de ce cours occupe déjà cette position.")
        return order


class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ("title", "file", "url")
        help_texts = {"file": "PDF, DOC, DOCX ou ZIP, 5 Mo au maximum."}
        formfield_callback = https_url_formfield

    def clean(self):
        cleaned_data = super().clean()
        if bool(cleaned_data.get("file")) == bool(cleaned_data.get("url")):
            raise forms.ValidationError("Choisissez un fichier ou un lien, exactement.")
        return cleaned_data


class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ("title",)


class QuestionForm(forms.ModelForm):
    """L'instance reçue porte déjà son quiz : l'ordre est contrôlé dans ce quiz."""

    choice_1 = forms.CharField(label="Choix 1", max_length=300)
    choice_2 = forms.CharField(label="Choix 2", max_length=300)
    choice_3 = forms.CharField(label="Choix 3", max_length=300)
    choice_4 = forms.CharField(label="Choix 4", max_length=300)
    correct_choice = forms.TypedChoiceField(
        label="Bonne réponse",
        choices=((1, "Choix 1"), (2, "Choix 2"), (3, "Choix 3"), (4, "Choix 4")),
        coerce=int,
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Question
        fields = ("statement", "explanation", "evidence", "order")
        widgets = {
            "statement": forms.Textarea(attrs={"rows": 3}),
            "explanation": forms.Textarea(attrs={"rows": 3}),
            "evidence": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = list(self.instance.choices.order_by("id")) if self.instance.pk else []
        for index, field_name in enumerate(CHOICE_FIELDS):
            if index < len(choices):
                self.fields[field_name].initial = choices[index].text
        correct = next(
            (index + 1 for index, choice in enumerate(choices) if choice.is_correct), None
        )
        if correct:
            self.fields["correct_choice"].initial = correct

    def clean_order(self):
        order = self.cleaned_data["order"]
        taken = Question.objects.filter(quiz_id=self.instance.quiz_id, order=order)
        if taken.exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Une autre question de ce quiz occupe déjà cette position.")
        return order

    def clean(self):
        cleaned_data = super().clean()
        seen = set()
        for field_name in CHOICE_FIELDS:
            text = cleaned_data.get(field_name)
            if text is None:
                continue
            if text.casefold() in seen:
                self.add_error(field_name, "Ce choix est identique à un autre choix.")
            seen.add(text.casefold())
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        question = super().save(commit=commit)
        if commit:
            question.choices.all().delete()
            correct_choice = self.cleaned_data["correct_choice"]
            for index, field_name in enumerate(CHOICE_FIELDS, start=1):
                Choice.objects.create(
                    question=question,
                    text=self.cleaned_data[field_name],
                    is_correct=index == correct_choice,
                )
        return question


class CourseFilterForm(forms.Form):
    query = forms.CharField(label="Rechercher", required=False)
    category = forms.ModelChoiceField(
        label="Catégorie",
        queryset=Category.objects.all(),
        required=False,
        empty_label="Toutes les catégories",
    )
    level = forms.ChoiceField(
        label="Niveau", choices=[("", "Tous les niveaux"), *Course.Level.choices], required=False
    )
