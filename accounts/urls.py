from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path(
        "connexion/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html", redirect_authenticated_user=True
        ),
        name="login",
    ),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "mot-de-passe/oubli/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset_form.html",
            email_template_name="accounts/password_reset_email.txt",
            success_url="/comptes/mot-de-passe/oubli/termine/",
        ),
        name="password_reset",
    ),
    path(
        "mot-de-passe/oubli/termine/",
        auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "mot-de-passe/reinitialiser/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url="/comptes/mot-de-passe/reinitialiser/termine/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "mot-de-passe/reinitialiser/termine/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path("inscription/", views.RegistrationView.as_view(), name="register"),
    path("profil/", views.ProfileView.as_view(), name="profile"),
    path("profil/modifier/", views.ProfileUpdateView.as_view(), name="profile_edit"),
    path("profil/<int:pk>/", views.PublicProfileView.as_view(), name="public_profile"),
    path("etablissement/rejoindre/", views.JoinInstitutionView.as_view(), name="join_institution"),
]
