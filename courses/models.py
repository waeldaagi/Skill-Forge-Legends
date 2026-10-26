import re
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from core.validators import validate_upload_size

YOUTUBE_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def unique_slug(model, value, fallback):
    """Slug libre pour ``model`` : « django », puis « django-2 », « django-3 »…"""
    max_length = model._meta.get_field("slug").max_length
    base = slugify(value)[: max_length - 6].strip("-") or fallback
    slug, number = base, 2
    while model.objects.filter(slug=slug).exists():
        slug = f"{base}-{number}"
        number += 1
    return slug


class Category(models.Model):
    name = models.CharField("nom", max_length=80, unique=True)
    slug = models.SlugField("slug", max_length=90, unique=True, editable=False)

    class Meta:
        ordering = ("name",)
        verbose_name = "catégorie"
        verbose_name_plural = "catégories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(Category, self.name, fallback="categorie")
        super().save(*args, **kwargs)


class Course(models.Model):
    class Level(models.TextChoices):
        BEGINNER = "BEGINNER", "Débutant"
        INTERMEDIATE = "INTERMEDIATE", "Intermédiaire"
        ADVANCED = "ADVANCED", "Avancé"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Brouillon"
        PUBLISHED = "PUBLISHED", "Publié"

    title = models.CharField("titre", max_length=180)
    slug = models.SlugField("slug", max_length=200, unique=True, editable=False)
    description = models.TextField("description")
    level = models.CharField("niveau", max_length=20, choices=Level.choices)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="courses", verbose_name="catégorie"
    )
    trainer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="courses",
        limit_choices_to={"role": "FORMATEUR"},
        verbose_name="formateur",
    )
    image = models.ImageField(
        "image",
        upload_to="courses/",
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"]), validate_upload_size],
    )
    is_premium = models.BooleanField("cours premium", default=False)
    status = models.CharField("statut", max_length=12, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("status", "category"))]
        verbose_name = "cours"
        verbose_name_plural = "cours"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Calculé une seule fois : renommer le cours ne casse pas les liens déjà partagés.
        if not self.slug:
            self.slug = unique_slug(Course, self.title, fallback="cours")
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("courses:detail", kwargs={"slug": self.slug})


class Chapter(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="chapters")
    title = models.CharField("titre", max_length=180)
    order = models.PositiveIntegerField("ordre", validators=[MinValueValidator(1)])
    content = models.TextField("contenu")
    video_url = models.URLField("vidéo", blank=True)

    class Meta:
        ordering = ("order",)
        constraints = [
            models.UniqueConstraint(fields=("course", "order"), name="unique_chapter_order"),
        ]
        verbose_name = "chapitre"
        verbose_name_plural = "chapitres"

    def __str__(self):
        return f"{self.course.title} · {self.order}. {self.title}"

    @property
    def video_embed_url(self):
        """URL à intégrer dans l'iframe (YouTube ou Vimeo) ; chaîne vide pour un autre site.

        Une URL « youtube.com/watch?v=… » collée telle quelle est refusée dans une iframe.
        """
        parts = urlsplit(self.video_url)
        host = (parts.hostname or "").removeprefix("www.").removeprefix("m.")
        segments = [segment for segment in parts.path.split("/") if segment]
        video_id = ""
        if host == "youtu.be" and segments:
            video_id = segments[0]
        elif host in {"youtube.com", "youtube-nocookie.com"}:
            if parts.path == "/watch":
                video_id = parse_qs(parts.query).get("v", [""])[0]
            elif len(segments) >= 2 and segments[0] in {"embed", "shorts", "live"}:
                video_id = segments[1]
        if YOUTUBE_VIDEO_ID.match(video_id):
            return f"https://www.youtube-nocookie.com/embed/{video_id}"
        if host in {"vimeo.com", "player.vimeo.com"} and segments and segments[-1].isdigit():
            return f"https://player.vimeo.com/video/{segments[-1]}"
        return ""


class Resource(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="resources")
    title = models.CharField("titre", max_length=180)
    file = models.FileField(
        "fichier",
        upload_to="resources/",
        blank=True,
        validators=[FileExtensionValidator(["pdf", "doc", "docx", "zip"]), validate_upload_size],
    )
    url = models.URLField("lien", blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    (models.Q(file__isnull=False) & ~models.Q(file="") & models.Q(url=""))
                    | (models.Q(file="") & models.Q(url__isnull=False) & ~models.Q(url=""))
                ),
                name="resource_exactly_one_source",
            )
        ]
        verbose_name = "ressource"
        verbose_name_plural = "ressources"

    def __str__(self):
        return self.title

    def clean(self):
        if bool(self.file) == bool(self.url):
            raise ValidationError(
                "Une ressource doit contenir un fichier ou un lien, mais pas les deux."
            )


class Enrollment(models.Model):
    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments"
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_at = models.DateTimeField("inscrit le", auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("learner", "course"), name="unique_course_enrollment"),
        ]
        verbose_name = "inscription"
        verbose_name_plural = "inscriptions"

    def __str__(self):
        return f"{self.learner} · {self.course}"


class ChapterProgress(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="progress")
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="progress")
    completed_at = models.DateTimeField("terminé le", auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("enrollment", "chapter"), name="unique_chapter_progress"
            ),
        ]
        verbose_name = "progression de chapitre"
        verbose_name_plural = "progressions de chapitre"

    def __str__(self):
        return f"{self.enrollment.learner} · {self.chapter}"


class Quiz(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="quizzes")
    title = models.CharField("titre", max_length=180)
    is_ai_generated = models.BooleanField("généré par l'IA", default=False)
    is_published = models.BooleanField("publié", default=False)

    class Meta:
        ordering = ("title",)
        verbose_name = "quiz"
        verbose_name_plural = "quiz"

    def __str__(self):
        return f"{self.chapter.title} · {self.title}"

    @property
    def ai_jobs(self):
        from core.models import AIJob

        return AIJob.objects.filter(object_id=self.pk, content_type__model="quiz")


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    statement = models.TextField("question")
    explanation = models.TextField("explication")
    evidence = models.TextField("extrait justificatif")
    order = models.PositiveIntegerField("ordre", validators=[MinValueValidator(1)])

    class Meta:
        ordering = ("order",)
        constraints = [
            models.UniqueConstraint(fields=("quiz", "order"), name="unique_question_order"),
        ]
        verbose_name = "question"
        verbose_name_plural = "questions"

    def __str__(self):
        return self.statement[:80]


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField("choix", max_length=300)
    is_correct = models.BooleanField("bonne réponse", default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("question", "text"), name="unique_choice_per_question"),
        ]
        verbose_name = "choix"
        verbose_name_plural = "choix"

    def __str__(self):
        return self.text


class QuizAttempt(models.Model):
    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_attempts"
    )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    score = models.PositiveIntegerField("score", validators=[MinValueValidator(0)])
    answers = models.JSONField("réponses", default=dict)
    completed_at = models.DateTimeField("terminé le", auto_now_add=True)

    class Meta:
        ordering = ("-completed_at",)
        verbose_name = "tentative de quiz"
        verbose_name_plural = "tentatives de quiz"

    def __str__(self):
        return f"{self.learner} · {self.quiz} · {self.score}%"

    def clean(self):
        if self.score > 100:
            raise ValidationError("Le score doit être compris entre 0 et 100.")
