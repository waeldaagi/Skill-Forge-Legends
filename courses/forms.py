from django import forms

from .models import Category, Chapter, Choice, Course, Question, Quiz, Resource


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ("title", "description", "level", "category", "image", "is_premium", "status")
        widgets = {"description": forms.Textarea(attrs={"rows": 6})}


class ChapterForm(forms.ModelForm):
    class Meta:
        model = Chapter
        fields = ("title", "order", "content", "video_url")
        widgets = {"content": forms.Textarea(attrs={"rows": 10})}


class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ("title", "file", "url")

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
        for index, field_name in enumerate(("choice_1", "choice_2", "choice_3", "choice_4")):
            if index < len(choices):
                self.fields[field_name].initial = choices[index].text
        correct = next(
            (index + 1 for index, choice in enumerate(choices) if choice.is_correct), None
        )
        if correct:
            self.fields["correct_choice"].initial = correct

    def save(self, commit=True):
        question = super().save(commit=commit)
        if commit:
            question.choices.all().delete()
            correct_choice = self.cleaned_data["correct_choice"]
            for index in range(1, 5):
                Choice.objects.create(
                    question=question,
                    text=self.cleaned_data[f"choice_{index}"],
                    is_correct=index == correct_choice,
                )
        return question


class CourseFilterForm(forms.Form):
    query = forms.CharField(label="Rechercher", required=False)
    category = forms.ModelChoiceField(
        label="Catégorie", queryset=Category.objects.all(), required=False
    )
    level = forms.ChoiceField(
        label="Niveau", choices=[("", "Tous les niveaux"), *Course.Level.choices], required=False
    )
