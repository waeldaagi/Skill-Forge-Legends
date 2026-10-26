from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, FormView, UpdateView

from core.permissions import RoleRequiredMixin

from .forms import JoinInstitutionForm, ProfileForm, RegistrationForm
from .models import User


class RegistrationView(CreateView):
    form_class = RegistrationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("core:home")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class ProfileView(LoginRequiredMixin, DetailView):
    model = User
    template_name = "accounts/profile.html"
    context_object_name = "profile_user"

    def get_object(self, queryset=None):
        return self.request.user


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileForm
    template_name = "accounts/profile_form.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Votre profil a été mis à jour.")
        return super().form_valid(form)


class PublicProfileView(DetailView):
    model = User
    template_name = "accounts/profile.html"
    context_object_name = "profile_user"

    def get_queryset(self):
        return User.objects.filter(is_public_profile=True, is_active=True)


class JoinInstitutionView(RoleRequiredMixin, FormView):
    # Le code d'invitation rattache un apprenant à son école ; les autres rôles n'en ont pas.
    allowed_roles = (User.Role.APPRENANT,)
    form_class = JoinInstitutionForm
    template_name = "accounts/join_institution.html"
    success_url = reverse_lazy("accounts:profile")

    def form_valid(self, form):
        self.request.user.etablissement = form.cleaned_data["invite_code"]
        self.request.user.save(update_fields=["etablissement"])
        messages.success(self.request, "Vous avez rejoint votre établissement.")
        return redirect(self.success_url)
