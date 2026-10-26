from functools import cached_property

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Max, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View

from accounts.models import User
from core.ai import run_ai_job
from core.permissions import RoleRequiredMixin

from .ai.quiz_generation import build_chapter_source
from .forms import (
    ChapterForm,
    CourseFilterForm,
    CourseForm,
    QuestionForm,
    QuizForm,
    ResourceForm,
)
from .models import Chapter, Course, Enrollment, Question, Quiz, QuizAttempt, Resource
from .services import (
    UNVERIFIED_TRAINER_MESSAGE,
    can_read_course,
    course_progress,
    enroll_learner,
    mark_chapter_completed,
    user_can_access_course,
)

LEARNER_ONLY_MESSAGE = "Seul un apprenant peut répondre à un quiz."


def next_position(queryset):
    """Premier ordre libre après le dernier chapitre ou la dernière question."""
    return (queryset.aggregate(last=Max("order"))["last"] or 0) + 1


class CourseListView(ListView):
    model = Course
    template_name = "courses/list.html"
    context_object_name = "courses"
    paginate_by = 9

    def get_queryset(self):
        queryset = Course.objects.filter(status=Course.Status.PUBLISHED).select_related(
            "category", "trainer"
        )
        form = CourseFilterForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data["query"]:
                queryset = queryset.filter(title__icontains=form.cleaned_data["query"])
            if form.cleaned_data["category"]:
                queryset = queryset.filter(category=form.cleaned_data["category"])
            if form.cleaned_data["level"]:
                queryset = queryset.filter(level=form.cleaned_data["level"])
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = CourseFilterForm(self.request.GET)
        return context


class CourseDetailView(DetailView):
    model = Course
    template_name = "courses/detail.html"
    context_object_name = "course"

    def get_queryset(self):
        # Un brouillon n'est visible que de son formateur.
        visible = Q(status=Course.Status.PUBLISHED)
        if self.request.user.is_authenticated:
            visible |= Q(trainer=self.request.user)
        return (
            Course.objects.filter(visible)
            .select_related("category", "trainer")
            .prefetch_related("chapters__quizzes")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["is_owner"] = user.is_authenticated and self.object.trainer_id == user.pk
        context["is_learner"] = user.is_authenticated and user.role == User.Role.APPRENANT
        enrollment = None
        if context["is_learner"]:
            enrollment = Enrollment.objects.filter(learner=user, course=self.object).first()
        context["enrollment"] = enrollment
        if enrollment:
            context["progress"] = course_progress(user, self.object)
            context["completed_chapter_ids"] = set(
                enrollment.progress.values_list("chapter_id", flat=True)
            )
        return context


class EnrollView(RoleRequiredMixin, View):
    allowed_roles = (User.Role.APPRENANT,)

    def post(self, request, slug):
        course = get_object_or_404(Course, slug=slug, status=Course.Status.PUBLISHED)
        if not user_can_access_course(request.user, course):
            messages.error(request, "Ce cours premium nécessite un abonnement actif.")
            return redirect(course)
        enroll_learner(request.user, course)
        messages.success(request, "Votre inscription au cours est confirmée.")
        return redirect(course)


class ChapterDetailView(LoginRequiredMixin, DetailView):
    model = Chapter
    template_name = "courses/chapter.html"
    context_object_name = "chapter"

    def get_queryset(self):
        return Chapter.objects.select_related("course").prefetch_related("resources")

    def get_object(self, queryset=None):
        chapter = super().get_object(queryset)
        if not can_read_course(self.request.user, chapter.course):
            raise Http404
        return chapter

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_owner"] = self.object.course.trainer_id == self.request.user.pk
        context["is_learner"] = self.request.user.role == User.Role.APPRENANT
        chapters = self.object.course.chapters.all()
        context["previous_chapter"] = chapters.filter(order__lt=self.object.order).last()
        context["next_chapter"] = chapters.filter(order__gt=self.object.order).first()
        return context


class QuizDetailView(LoginRequiredMixin, DetailView):
    model = Quiz
    template_name = "courses/quiz.html"
    context_object_name = "quiz"

    def get_queryset(self):
        return (
            Quiz.objects.filter(is_published=True)
            .select_related("chapter__course")
            .prefetch_related("questions__choices")
        )

    def get_object(self, queryset=None):
        # Même règle que pour le chapitre : un cours premium exige un abonnement actif.
        quiz = super().get_object(queryset)
        if not can_read_course(self.request.user, quiz.chapter.course):
            raise Http404
        return quiz

    def post(self, request, *args, **kwargs):
        if request.user.role != User.Role.APPRENANT:
            raise PermissionDenied(LEARNER_ONLY_MESSAGE)
        self.object = self.get_object()
        questions = list(self.object.questions.all())
        if not questions:
            messages.error(request, "Ce quiz ne contient pas encore de question.")
            return redirect("courses:quiz", pk=self.object.pk)
        correct_answers = 0
        answers = {}
        for question in questions:
            # Comparaison aux choix de la question : une valeur forgée ne compte pas, sans erreur.
            choices = {str(choice.pk): choice for choice in question.choices.all()}
            choice = choices.get(request.POST.get(f"question-{question.pk}", ""))
            answers[str(question.pk)] = choice.pk if choice else None
            if choice and choice.is_correct:
                correct_answers += 1
        score = round(correct_answers * 100 / len(questions))
        QuizAttempt.objects.create(
            learner=request.user, quiz=self.object, score=score, answers=answers
        )
        messages.success(request, f"Quiz terminé : votre score est de {score} %.")
        return redirect("courses:quiz", pk=self.object.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_submit"] = self.request.user.role == User.Role.APPRENANT
        context["latest_attempt"] = QuizAttempt.objects.filter(
            learner=self.request.user, quiz=self.object
        ).first()
        return context


class CompleteChapterView(RoleRequiredMixin, View):
    allowed_roles = (User.Role.APPRENANT,)

    def post(self, request, pk):
        chapter = get_object_or_404(Chapter, pk=pk, course__status=Course.Status.PUBLISHED)
        if not user_can_access_course(request.user, chapter.course):
            raise Http404
        mark_chapter_completed(request.user, chapter)
        messages.success(request, "Chapitre marqué comme terminé.")
        return redirect("courses:detail", slug=chapter.course.slug)


# Espace formateur. Chaque objet est chargé après le contrôle de rôle (RoleRequiredMixin) :
# un anonyme est redirigé vers la connexion, un autre rôle reçoit 403, et le cours d'un autre
# formateur donne 404.


class TrainerRequiredMixin(RoleRequiredMixin):
    allowed_roles = (User.Role.FORMATEUR,)


class DeleteConfirmationMixin:
    template_name = "courses/confirm_delete.html"
    page_title = ""
    warning = ""
    submit_label = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = self.page_title
        context["warning"] = self.warning
        context["submit_label"] = self.submit_label
        context["cancel_url"] = self.get_success_url()
        return context


class TrainerCourseListView(TrainerRequiredMixin, ListView):
    template_name = "courses/trainer_list.html"
    context_object_name = "courses"

    def get_queryset(self):
        # annotate() regroupe la requête : Meta.ordering n'y est pas appliqué.
        return (
            Course.objects.filter(trainer=self.request.user)
            .select_related("category")
            .annotate(chapter_count=Count("chapters"))
            .order_by("-created_at")
        )


class TrainerCourseMixin(TrainerRequiredMixin):
    def get_queryset(self):
        return Course.objects.filter(trainer=self.request.user)


class CourseFormMixin:
    form_class = CourseForm
    template_name = "courses/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["trainer"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("courses:update", kwargs={"slug": self.object.slug})


class TrainerCourseCreateView(TrainerRequiredMixin, CourseFormMixin, CreateView):
    model = Course

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Créer un cours"
        context["submit_label"] = "Enregistrer le cours"
        context["cancel_url"] = reverse("courses:trainer_courses")
        return context

    def form_valid(self, form):
        form.instance.trainer = self.request.user
        return super().form_valid(form)


class TrainerCourseUpdateView(TrainerCourseMixin, CourseFormMixin, UpdateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Modifier le cours"
        context["submit_label"] = "Enregistrer les modifications"
        context["cancel_url"] = self.object.get_absolute_url()
        return context

    def form_valid(self, form):
        messages.success(self.request, "Le cours est enregistré.")
        return super().form_valid(form)


class TrainerCourseDeleteView(TrainerCourseMixin, DeleteConfirmationMixin, DeleteView):
    page_title = "Supprimer ce cours"
    warning = (
        "Le cours, ses chapitres, ses ressources, ses quiz et les inscriptions seront supprimés."
    )
    submit_label = "Supprimer le cours"
    success_url = reverse_lazy("courses:trainer_courses")


class TrainerChapterMixin(TrainerRequiredMixin):
    def get_queryset(self):
        return Chapter.objects.filter(course__trainer=self.request.user).select_related("course")

    def get_success_url(self):
        return self.object.course.get_absolute_url()


class TrainerChapterCreateView(TrainerRequiredMixin, CreateView):
    model = Chapter
    form_class = ChapterForm
    template_name = "courses/form.html"

    @cached_property
    def course(self):
        return get_object_or_404(Course, pk=self.kwargs["course_pk"], trainer=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = Chapter(course=self.course)
        return kwargs

    def get_initial(self):
        return {"order": next_position(self.course.chapters.all())}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Ajouter un chapitre à « {self.course.title} »"
        context["submit_label"] = "Enregistrer le chapitre"
        context["cancel_url"] = self.course.get_absolute_url()
        return context

    def get_success_url(self):
        return self.course.get_absolute_url()


class TrainerChapterUpdateView(TrainerChapterMixin, UpdateView):
    form_class = ChapterForm
    template_name = "courses/form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Modifier le chapitre"
        context["submit_label"] = "Enregistrer les modifications"
        context["cancel_url"] = self.get_success_url()
        return context


class TrainerChapterDeleteView(TrainerChapterMixin, DeleteConfirmationMixin, DeleteView):
    page_title = "Supprimer ce chapitre"
    warning = (
        "Le chapitre, ses ressources, ses quiz et la progression des apprenants seront supprimés."
    )
    submit_label = "Supprimer le chapitre"


class TrainerResourceMixin(TrainerRequiredMixin):
    def get_queryset(self):
        return Resource.objects.filter(chapter__course__trainer=self.request.user).select_related(
            "chapter"
        )

    def get_success_url(self):
        return reverse("courses:chapter", kwargs={"pk": self.object.chapter_id})


class TrainerResourceCreateView(TrainerRequiredMixin, CreateView):
    model = Resource
    form_class = ResourceForm
    template_name = "courses/form.html"

    @cached_property
    def chapter(self):
        return get_object_or_404(
            Chapter, pk=self.kwargs["chapter_pk"], course__trainer=self.request.user
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = Resource(chapter=self.chapter)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Ajouter une ressource à « {self.chapter.title} »"
        context["submit_label"] = "Enregistrer la ressource"
        context["cancel_url"] = self.get_success_url()
        return context

    def get_success_url(self):
        return reverse("courses:chapter", kwargs={"pk": self.chapter.pk})


class TrainerResourceUpdateView(TrainerResourceMixin, UpdateView):
    form_class = ResourceForm
    template_name = "courses/form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Modifier la ressource"
        context["submit_label"] = "Enregistrer les modifications"
        context["cancel_url"] = self.get_success_url()
        return context


class TrainerResourceDeleteView(TrainerResourceMixin, DeleteConfirmationMixin, DeleteView):
    page_title = "Supprimer cette ressource"
    warning = "La ressource ne sera plus proposée aux apprenants."
    submit_label = "Supprimer la ressource"


class TrainerQuizMixin(TrainerRequiredMixin):
    def get_queryset(self):
        return Quiz.objects.filter(chapter__course__trainer=self.request.user).select_related(
            "chapter__course"
        )


class TrainerQuizCreateView(TrainerRequiredMixin, CreateView):
    model = Quiz
    form_class = QuizForm
    template_name = "courses/quiz_form.html"

    @cached_property
    def chapter(self):
        return get_object_or_404(
            Chapter, pk=self.kwargs["chapter_pk"], course__trainer=self.request.user
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = Quiz(chapter=self.chapter)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Ajouter un quiz à « {self.chapter.title} »"
        context["cancel_url"] = self.chapter.course.get_absolute_url()
        return context

    def get_success_url(self):
        return reverse("courses:quiz_manage", kwargs={"pk": self.object.pk})


class TrainerQuizUpdateView(TrainerQuizMixin, UpdateView):
    form_class = QuizForm
    template_name = "courses/quiz_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Modifier le quiz"
        context["cancel_url"] = self.get_success_url()
        return context

    def get_success_url(self):
        return reverse("courses:quiz_manage", kwargs={"pk": self.object.pk})


class TrainerQuizDeleteView(TrainerQuizMixin, DeleteConfirmationMixin, DeleteView):
    page_title = "Supprimer ce quiz"
    warning = "Le quiz, ses questions et les tentatives des apprenants seront supprimés."
    submit_label = "Supprimer le quiz"

    def get_success_url(self):
        return self.object.chapter.course.get_absolute_url()


class TrainerQuizManageView(TrainerQuizMixin, DetailView):
    template_name = "courses/quiz_manage.html"
    context_object_name = "quiz"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("questions__choices")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["generation_job"] = self.object.ai_jobs.order_by("-created_at").first()
        return context


class GenerateQuizView(TrainerQuizMixin, View):
    def post(self, request, pk):
        quiz = get_object_or_404(self.get_queryset(), pk=pk)
        if quiz.is_published:
            # La génération remplace toutes les questions : les apprenants perdraient leur corrigé.
            messages.error(request, "Dépubliez le quiz avant de le générer à nouveau.")
            return redirect("courses:quiz_manage", pk=quiz.pk)
        run_ai_job(
            "quiz_generation",
            request.user,
            target=quiz,
            payload={
                "title": quiz.title,
                "source": build_chapter_source(quiz.chapter),
            },
        )
        messages.info(
            request, "La génération du quiz est lancée. Le résultat restera un brouillon."
        )
        return redirect("courses:quiz_manage", pk=quiz.pk)


class PublishQuizView(TrainerQuizMixin, View):
    def post(self, request, pk):
        quiz = get_object_or_404(self.get_queryset(), pk=pk)
        if not request.user.is_verified:
            messages.error(request, UNVERIFIED_TRAINER_MESSAGE)
            return redirect("courses:quiz_manage", pk=quiz.pk)
        questions = list(quiz.questions.prefetch_related("choices"))
        if not questions or any(len(question.choices.all()) != 4 for question in questions):
            messages.error(
                request,
                "Ajoutez quatre choix à chaque question avant de publier le quiz.",
            )
            return redirect("courses:quiz_manage", pk=quiz.pk)
        if any(
            sum(choice.is_correct for choice in question.choices.all()) != 1
            for question in questions
        ):
            messages.error(request, "Chaque question doit avoir une seule bonne réponse.")
            return redirect("courses:quiz_manage", pk=quiz.pk)
        quiz.is_published = True
        quiz.save(update_fields=["is_published"])
        messages.success(request, "Le quiz est publié.")
        return redirect("courses:quiz_manage", pk=quiz.pk)


class UnpublishQuizView(TrainerQuizMixin, View):
    def post(self, request, pk):
        quiz = get_object_or_404(self.get_queryset(), pk=pk)
        quiz.is_published = False
        quiz.save(update_fields=["is_published"])
        messages.success(
            request, "Le quiz est repassé en brouillon : les apprenants ne le voient plus."
        )
        return redirect("courses:quiz_manage", pk=quiz.pk)


class TrainerQuestionMixin(TrainerRequiredMixin):
    def get_queryset(self):
        return Question.objects.filter(
            quiz__chapter__course__trainer=self.request.user
        ).select_related("quiz")

    def get_success_url(self):
        return reverse("courses:quiz_manage", kwargs={"pk": self.object.quiz_id})


class TrainerQuestionCreateView(TrainerRequiredMixin, CreateView):
    model = Question
    form_class = QuestionForm
    template_name = "courses/question_form.html"

    @cached_property
    def quiz(self):
        return get_object_or_404(
            Quiz, pk=self.kwargs["quiz_pk"], chapter__course__trainer=self.request.user
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = Question(quiz=self.quiz)
        return kwargs

    def get_initial(self):
        return {"order": next_position(self.quiz.questions.all())}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Ajouter une question"
        context["submit_label"] = "Enregistrer la question"
        context["cancel_url"] = self.get_success_url()
        return context

    def get_success_url(self):
        return reverse("courses:quiz_manage", kwargs={"pk": self.quiz.pk})


class TrainerQuestionUpdateView(TrainerQuestionMixin, UpdateView):
    form_class = QuestionForm
    template_name = "courses/question_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Modifier la question"
        context["submit_label"] = "Enregistrer les modifications"
        context["cancel_url"] = self.get_success_url()
        return context


class TrainerQuestionDeleteView(TrainerQuestionMixin, DeleteConfirmationMixin, DeleteView):
    page_title = "Supprimer cette question"
    warning = "La question et ses quatre choix seront supprimés."
    submit_label = "Supprimer la question"
