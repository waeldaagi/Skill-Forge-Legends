from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
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
from .models import Chapter, Course, Question, Quiz, QuizAttempt, Resource
from .services import (
    enroll_learner,
    mark_chapter_completed,
    user_can_access_course,
)


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
        return (
            Course.objects.filter(status=Course.Status.PUBLISHED)
            .select_related("category", "trainer")
            .prefetch_related("chapters__quizzes")
        )


class EnrollView(LoginRequiredMixin, View):
    def post(self, request, slug):
        course = get_object_or_404(Course, slug=slug, status=Course.Status.PUBLISHED)
        if request.user.role != User.Role.APPRENANT:
            raise Http404
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
        return (
            Chapter.objects.filter(course__status=Course.Status.PUBLISHED)
            .select_related("course")
            .prefetch_related("resources")
        )

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code == 200 and not user_can_access_course(
            request.user, self.object.course
        ):
            raise Http404
        return response


class QuizDetailView(LoginRequiredMixin, DetailView):
    model = Quiz
    template_name = "courses/quiz.html"
    context_object_name = "quiz"

    def get_queryset(self):
        return Quiz.objects.filter(
            is_published=True, chapter__course__status=Course.Status.PUBLISHED
        ).prefetch_related("questions__choices")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        questions = list(self.object.questions.prefetch_related("choices"))
        correct_answers = 0
        answers = {}
        for question in questions:
            choice_id = request.POST.get(f"question-{question.pk}")
            answers[str(question.pk)] = choice_id
            if choice_id and question.choices.filter(pk=choice_id, is_correct=True).exists():
                correct_answers += 1
        score = round(correct_answers * 100 / len(questions)) if questions else 0
        QuizAttempt.objects.create(
            learner=request.user, quiz=self.object, score=score, answers=answers
        )
        messages.success(request, f"Quiz terminé : votre score est de {score} %.")
        return redirect("courses:quiz", pk=self.object.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        latest_attempt = QuizAttempt.objects.filter(
            learner=self.request.user, quiz=self.object
        ).first()
        context["latest_attempt"] = latest_attempt
        return context


class TrainerQuizMixin(RoleRequiredMixin):
    allowed_roles = (User.Role.FORMATEUR,)

    def get_queryset(self):
        return Quiz.objects.filter(chapter__course__trainer=self.request.user)


class TrainerQuizCreateView(TrainerQuizMixin, CreateView):
    model = Quiz
    form_class = QuizForm
    template_name = "courses/quiz_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.chapter = get_object_or_404(
            Chapter, pk=kwargs["chapter_pk"], course__trainer=request.user
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.chapter = self.chapter
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("courses:quiz_manage", kwargs={"pk": self.object.pk})


class TrainerQuizUpdateView(TrainerQuizMixin, UpdateView):
    form_class = QuizForm
    template_name = "courses/quiz_form.html"

    def get_success_url(self):
        return reverse("courses:quiz_manage", kwargs={"pk": self.object.pk})


class TrainerQuestionCreateView(RoleRequiredMixin, CreateView):
    model = Question
    form_class = QuestionForm
    template_name = "courses/question_form.html"
    allowed_roles = (User.Role.FORMATEUR,)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Ajouter une question"
        context["submit_label"] = "Enregistrer la question"
        context["cancel_url"] = reverse("courses:quiz_manage", kwargs={"pk": self.quiz.pk})
        return context

    def dispatch(self, request, *args, **kwargs):
        self.quiz = get_object_or_404(
            Quiz, pk=kwargs["quiz_pk"], chapter__course__trainer=request.user
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.quiz = self.quiz
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("courses:quiz_manage", kwargs={"pk": self.quiz.pk})


class TrainerQuestionUpdateView(RoleRequiredMixin, UpdateView):
    model = Question
    form_class = QuestionForm
    template_name = "courses/question_form.html"
    allowed_roles = (User.Role.FORMATEUR,)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Modifier la question"
        context["submit_label"] = "Enregistrer les modifications"
        context["cancel_url"] = reverse("courses:quiz_manage", kwargs={"pk": self.object.quiz.pk})
        return context

    def get_queryset(self):
        return Question.objects.filter(quiz__chapter__course__trainer=self.request.user)

    def get_success_url(self):
        return reverse("courses:quiz_manage", kwargs={"pk": self.object.quiz.pk})


class TrainerQuizManageView(TrainerQuizMixin, DetailView):
    template_name = "courses/quiz_manage.html"
    context_object_name = "quiz"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["generation_job"] = self.object.ai_jobs.order_by("-created_at").first()
        return context


class GenerateQuizView(TrainerQuizMixin, View):
    def post(self, request, pk):
        quiz = get_object_or_404(self.get_queryset(), pk=pk)
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
        questions = list(quiz.questions.prefetch_related("choices"))
        if not questions or any(question.choices.count() != 4 for question in questions):
            messages.error(
                request,
                "Ajoutez quatre choix à chaque question avant de publier le quiz.",
            )
            return redirect("courses:quiz_manage", pk=quiz.pk)
        if any(question.choices.filter(is_correct=True).count() != 1 for question in questions):
            messages.error(request, "Chaque question doit avoir une seule bonne réponse.")
            return redirect("courses:quiz_manage", pk=quiz.pk)
        quiz.is_published = True
        quiz.save(update_fields=["is_published"])
        messages.success(request, "Le quiz est publié.")
        return redirect("courses:quiz_manage", pk=quiz.pk)


class CompleteChapterView(LoginRequiredMixin, View):
    def post(self, request, pk):
        chapter = get_object_or_404(Chapter, pk=pk, course__status=Course.Status.PUBLISHED)
        if not user_can_access_course(request.user, chapter.course):
            raise Http404
        mark_chapter_completed(request.user, chapter)
        messages.success(request, "Chapitre marqué comme terminé.")
        return redirect("courses:detail", slug=chapter.course.slug)


class TrainerCourseMixin(RoleRequiredMixin):
    allowed_roles = (User.Role.FORMATEUR,)

    def get_queryset(self):
        return Course.objects.filter(trainer=self.request.user)


class TrainerCourseCreateView(TrainerCourseMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = "courses/form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Créer un cours"
        context["submit_label"] = "Enregistrer le cours"
        return context

    def form_valid(self, form):
        form.instance.trainer = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("courses:update", kwargs={"slug": self.object.slug})


class TrainerCourseUpdateView(TrainerCourseMixin, UpdateView):
    form_class = CourseForm
    template_name = "courses/form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Modifier le cours"
        context["submit_label"] = "Enregistrer les modifications"
        return context

    def get_success_url(self):
        return reverse("courses:update", kwargs={"slug": self.object.slug})


class TrainerCourseDeleteView(TrainerCourseMixin, DeleteView):
    template_name = "courses/confirm_delete.html"
    success_url = reverse_lazy("courses:list")


class TrainerChapterCreateView(RoleRequiredMixin, CreateView):
    model = Chapter
    form_class = ChapterForm
    template_name = "courses/form.html"
    allowed_roles = (User.Role.FORMATEUR,)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Ajouter un chapitre"
        context["submit_label"] = "Enregistrer le chapitre"
        context["cancel_url"] = self.course.get_absolute_url()
        return context

    def get_queryset(self):
        return Chapter.objects.filter(course__trainer=self.request.user)

    def dispatch(self, request, *args, **kwargs):
        self.course = get_object_or_404(Course, pk=kwargs["course_pk"], trainer=request.user)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.course = self.course
        return super().form_valid(form)

    def get_success_url(self):
        return self.course.get_absolute_url()


class TrainerResourceCreateView(RoleRequiredMixin, CreateView):
    model = Resource
    form_class = ResourceForm
    template_name = "courses/form.html"
    allowed_roles = (User.Role.FORMATEUR,)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Ajouter une ressource"
        context["submit_label"] = "Enregistrer la ressource"
        context["cancel_url"] = reverse("courses:chapter", kwargs={"pk": self.chapter.pk})
        return context

    def get_queryset(self):
        return Resource.objects.filter(chapter__course__trainer=self.request.user)

    def dispatch(self, request, *args, **kwargs):
        self.chapter = get_object_or_404(
            Chapter, pk=kwargs["chapter_pk"], course__trainer=request.user
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.chapter = self.chapter
        return super().form_valid(form)

    def get_success_url(self):
        return self.chapter.course.get_absolute_url()
