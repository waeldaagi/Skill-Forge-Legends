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
