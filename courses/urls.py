from django.urls import path

from . import views

app_name = "courses"

urlpatterns = [
    path("", views.CourseListView.as_view(), name="list"),
    # Les pages du formateur sont sous « formateur/ » : aucun slug de cours ne peut les masquer.
    path("formateur/cours/", views.TrainerCourseListView.as_view(), name="trainer_courses"),
    path("formateur/cours/nouveau/", views.TrainerCourseCreateView.as_view(), name="create"),
    path("<slug:slug>/", views.CourseDetailView.as_view(), name="detail"),
    path("<slug:slug>/inscription/", views.EnrollView.as_view(), name="enroll"),
    path("<slug:slug>/modifier/", views.TrainerCourseUpdateView.as_view(), name="update"),
    path("<slug:slug>/supprimer/", views.TrainerCourseDeleteView.as_view(), name="delete"),
    path("chapitres/<int:pk>/", views.ChapterDetailView.as_view(), name="chapter"),
    path(
        "chapitres/<int:pk>/terminer/",
        views.CompleteChapterView.as_view(),
        name="complete_chapter",
    ),
    path("quiz/<int:pk>/", views.QuizDetailView.as_view(), name="quiz"),
    path(
        "formateur/cours/<int:course_pk>/chapitres/nouveau/",
        views.TrainerChapterCreateView.as_view(),
        name="chapter_create",
    ),
    path(
        "formateur/chapitres/<int:pk>/modifier/",
        views.TrainerChapterUpdateView.as_view(),
        name="chapter_update",
    ),
    path(
        "formateur/chapitres/<int:pk>/supprimer/",
        views.TrainerChapterDeleteView.as_view(),
        name="chapter_delete",
    ),
    path(
        "formateur/chapitres/<int:chapter_pk>/ressources/nouveau/",
        views.TrainerResourceCreateView.as_view(),
        name="resource_create",
    ),
    path(
        "formateur/ressources/<int:pk>/modifier/",
        views.TrainerResourceUpdateView.as_view(),
        name="resource_update",
    ),
    path(
        "formateur/ressources/<int:pk>/supprimer/",
        views.TrainerResourceDeleteView.as_view(),
        name="resource_delete",
    ),
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
        "formateur/quiz/<int:pk>/supprimer/",
        views.TrainerQuizDeleteView.as_view(),
        name="quiz_delete",
    ),
    path(
        "formateur/quiz/<int:pk>/publier/",
        views.PublishQuizView.as_view(),
        name="quiz_publish",
    ),
    path(
        "formateur/quiz/<int:pk>/depublier/",
        views.UnpublishQuizView.as_view(),
        name="quiz_unpublish",
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
        "formateur/questions/<int:pk>/supprimer/",
        views.TrainerQuestionDeleteView.as_view(),
        name="question_delete",
    ),
]
