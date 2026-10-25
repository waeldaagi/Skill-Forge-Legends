from django.urls import path

from . import views
from .models import Reply, Thread

app_name = "community"

urlpatterns = [
    path("", views.ThreadListView.as_view(), name="thread_list"),
    path("sujets/nouveau/", views.ThreadCreateView.as_view(), name="thread_create"),
    path("sujets/<int:pk>/", views.ThreadDetailView.as_view(), name="thread_detail"),
    path("sujets/<int:pk>/modifier/", views.ThreadUpdateView.as_view(), name="thread_update"),
    path("sujets/<int:pk>/supprimer/", views.ThreadDeleteView.as_view(), name="thread_delete"),
    path("sujets/<int:pk>/resolu/", views.ThreadResolveView.as_view(), name="thread_resolve"),
    path("sujets/<int:pk>/repondre/", views.ReplyCreateView.as_view(), name="reply_create"),
    path(
        "sujets/<int:pk>/signaler/",
        views.ReportCreateView.as_view(target_model=Thread),
        name="thread_report",
    ),
    path("reponses/<int:pk>/modifier/", views.ReplyUpdateView.as_view(), name="reply_update"),
    path("reponses/<int:pk>/supprimer/", views.ReplyDeleteView.as_view(), name="reply_delete"),
    path("reponses/<int:pk>/voter/", views.ReplyVoteView.as_view(), name="reply_vote"),
    path("reponses/<int:pk>/accepter/", views.ReplyAcceptView.as_view(), name="reply_accept"),
    path(
        "reponses/<int:pk>/signaler/",
        views.ReportCreateView.as_view(target_model=Reply),
        name="reply_report",
    ),
    path("moderation/", views.ModerationQueueView.as_view(), name="moderation_queue"),
    path(
        "moderation/sujets/<int:pk>/approuver/",
        views.ModerationDecisionView.as_view(target_model=Thread, decision="approve"),
        name="thread_approve",
    ),
    path(
        "moderation/sujets/<int:pk>/rejeter/",
        views.ModerationDecisionView.as_view(target_model=Thread, decision="reject"),
        name="thread_reject",
    ),
    path(
        "moderation/reponses/<int:pk>/approuver/",
        views.ModerationDecisionView.as_view(target_model=Reply, decision="approve"),
        name="reply_approve",
    ),
    path(
        "moderation/reponses/<int:pk>/rejeter/",
        views.ModerationDecisionView.as_view(target_model=Reply, decision="reject"),
        name="reply_reject",
    ),
    path(
        "moderation/signalements/<int:pk>/classer/",
        views.ReportDismissView.as_view(),
        name="report_dismiss",
    ),
]
