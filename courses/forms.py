from django import forms

from .models import Category, Chapter, Course, Resource


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


class CourseFilterForm(forms.Form):
    query = forms.CharField(label="Rechercher", required=False)
    category = forms.ModelChoiceField(
        label="Catégorie", queryset=Category.objects.all(), required=False
    )
    level = forms.ChoiceField(
        label="Niveau", choices=[("", "Tous les niveaux"), *Course.Level.choices], required=False
    )
