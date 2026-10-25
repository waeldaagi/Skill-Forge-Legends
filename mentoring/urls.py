from django.urls import path

from . import views

app_name = "mentoring"

urlpatterns = [
    path("mentors/", views.MentorDirectoryView.as_view(), name="mentor_directory"),
    path("mentors/<int:pk>/", views.MentorDetailView.as_view(), name="mentor_detail"),
    path("profil/", views.MentorProfileEditView.as_view(), name="profile_edit"),
    path("creneaux/", views.SlotListView.as_view(), name="slot_list"),
    path("creneaux/nouveau/", views.SlotCreateView.as_view(), name="slot_create"),
    path("creneaux/<int:pk>/modifier/", views.SlotUpdateView.as_view(), name="slot_update"),
    path("creneaux/<int:pk>/supprimer/", views.SlotDeleteView.as_view(), name="slot_delete"),
    path("creneaux/<int:pk>/reserver/", views.SlotBookView.as_view(), name="slot_book"),
    path("sessions/", views.SessionListView.as_view(), name="session_list"),
    path("sessions/<int:pk>/", views.SessionDetailView.as_view(), name="session_detail"),
    path(
        "sessions/<int:pk>/confirmer/", views.SessionConfirmView.as_view(), name="session_confirm"
    ),
    path("sessions/<int:pk>/refuser/", views.SessionRefuseView.as_view(), name="session_refuse"),
    path(
        "sessions/<int:pk>/terminer/", views.SessionCompleteView.as_view(), name="session_complete"
    ),
    path("sessions/<int:pk>/annuler/", views.SessionCancelView.as_view(), name="session_cancel"),
    path("sessions/<int:pk>/avis/", views.SessionReviewView.as_view(), name="session_review"),
    path("sessions/<int:pk>/salle/", views.SessionRoomView.as_view(), name="session_room"),
]
