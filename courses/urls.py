from django.urls import path

from . import views

app_name = "courses"

urlpatterns = [
    path("", views.CourseListView.as_view(), name="list"),
    path("nouveau/", views.TrainerCourseCreateView.as_view(), name="create"),
    path("<slug:slug>/", views.CourseDetailView.as_view(), name="detail"),
    path("<slug:slug>/inscription/", views.EnrollView.as_view(), name="enroll"),
    path("<slug:slug>/modifier/", views.TrainerCourseUpdateView.as_view(), name="update"),
    path("<slug:slug>/supprimer/", views.TrainerCourseDeleteView.as_view(), name="delete"),
    path("chapitres/<int:pk>/", views.ChapterDetailView.as_view(), name="chapter"),
    path("quiz/<int:pk>/", views.QuizDetailView.as_view(), name="quiz"),
    path(
        "formateur/chapitres/<int:chapter_pk>/quiz/nouveau/",
        views.TrainerQuizCreateView.as_view(),
        name="quiz_create",
    ),
    path(
        "formateur/quiz/<int:pk>/",
        views.TrainerQuizManageView.as_view(),
        name="quiz_manage",
    ),
    path(
        "formateur/quiz/<int:pk>/modifier/",
        views.TrainerQuizUpdateView.as_view(),
        name="quiz_update",
    ),
    path(
        "formateur/quiz/<int:pk>/publier/",
        views.PublishQuizView.as_view(),
        name="quiz_publish",
    ),
    path(
        "formateur/quiz/<int:pk>/generer/",
        views.GenerateQuizView.as_view(),
        name="quiz_generate",
    ),
    path(
        "formateur/quiz/<int:quiz_pk>/questions/nouveau/",
        views.TrainerQuestionCreateView.as_view(),
        name="question_create",
    ),
    path(
        "formateur/questions/<int:pk>/modifier/",
        views.TrainerQuestionUpdateView.as_view(),
        name="question_update",
    ),
    path(
        "chapitres/<int:pk>/terminer/",
        views.CompleteChapterView.as_view(),
        name="complete_chapter",
    ),
    path(
        "formateur/cours/<int:course_pk>/chapitres/nouveau/",
        views.TrainerChapterCreateView.as_view(),
        name="chapter_create",
    ),
    path(
        "formateur/chapitres/<int:chapter_pk>/ressources/nouveau/",
        views.TrainerResourceCreateView.as_view(),
        name="resource_create",
    ),
]
