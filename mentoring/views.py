from functools import cached_property

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.models import User
from core.permissions import OwnerRequiredMixin, RoleRequiredMixin

from . import services
from .forms import (
    AvailabilitySlotForm,
    BookingForm,
    MentorNotesForm,
    MentorProfileForm,
    MentorSearchForm,
    RefusalForm,
    SessionFilterForm,
    SessionReviewForm,
    SlotFilterForm,
)
from .models import AvailabilitySlot, MentoringSession, MentorProfile

Role = User.Role
Status = MentoringSession.Status
PAGE_SIZE = 10


# Mentor : profil et créneaux


class MentorProfileEditView(RoleRequiredMixin, UpdateView):
    allowed_roles = (Role.MENTOR,)
    form_class = MentorProfileForm
    template_name = "mentoring/profile_form.html"
    success_url = reverse_lazy("mentoring:slot_list")

    def get_object(self, queryset=None):
        # Une seule page pour créer puis modifier le profil : il n'en existe qu'un par mentor.
        profile = MentorProfile.objects.filter(mentor=self.request.user).first()
        return profile or MentorProfile(mentor=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Votre profil de mentor est enregistré.")
        return super().form_valid(form)


class SlotListView(RoleRequiredMixin, ListView):
    allowed_roles = (Role.MENTOR,)
    template_name = "mentoring/slot_list.html"
    context_object_name = "slots"
    paginate_by = PAGE_SIZE

    def get_queryset(self):
        self.filter_form = SlotFilterForm(self.request.GET or None)
        filters = self.filter_form.cleaned_data if self.filter_form.is_valid() else {}
        slots = AvailabilitySlot.objects.filter(mentor=self.request.user)
        now = timezone.now()
        if filters.get("periode") == "passes":
            slots = slots.filter(end__lt=now).order_by("-start")
        else:
            slots = slots.filter(end__gte=now)
        if filters.get("etat") == "libres":
            slots = slots.filter(is_booked=False)
        elif filters.get("etat") == "reserves":
            slots = slots.filter(is_booked=True)
        return slots

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            filter_form=self.filter_form,
            has_profile=MentorProfile.objects.filter(mentor=self.request.user).exists(),
            **kwargs,
        )


class SlotCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = (Role.MENTOR,)
    form_class = AvailabilitySlotForm
    template_name = "mentoring/slot_form.html"
    success_url = reverse_lazy("mentoring:slot_list")

    def get_form_kwargs(self):
        # Le mentor doit être connu avant la validation : clean() cherche les chevauchements.
        return {**super().get_form_kwargs(), "instance": AvailabilitySlot(mentor=self.request.user)}

    def form_valid(self, form):
        messages.success(self.request, f"Créneau ajouté : {form.instance.period}.")
        return super().form_valid(form)


class EditableSlotMixin(RoleRequiredMixin, OwnerRequiredMixin):
    allowed_roles = (Role.MENTOR,)
    model = AvailabilitySlot
    owner_field = "mentor"
    success_url = reverse_lazy("mentoring:slot_list")

    def get_object(self, queryset=None):
        slot = super().get_object(queryset)
        try:
            services.ensure_slot_editable(slot)
        except services.SlotLocked as exc:
            raise PermissionDenied(str(exc)) from exc
        return slot


class SlotUpdateView(EditableSlotMixin, UpdateView):
    form_class = AvailabilitySlotForm
    template_name = "mentoring/slot_form.html"

    def form_valid(self, form):
        messages.success(self.request, f"Créneau modifié : {form.instance.period}.")
        return super().form_valid(form)


class SlotDeleteView(EditableSlotMixin, DeleteView):
    template_name = "mentoring/slot_confirm_delete.html"
    context_object_name = "slot"

    def form_valid(self, form):
        messages.success(self.request, f"Créneau supprimé : {self.object.period}.")
        return super().form_valid(form)


# Apprenant : annuaire et réservation


class MentorDirectoryView(RoleRequiredMixin, ListView):
    allowed_roles = (Role.APPRENANT,)
    template_name = "mentoring/mentor_directory.html"
    context_object_name = "profiles"
    paginate_by = 12

    def get_queryset(self):
        self.search_form = MentorSearchForm(self.request.GET or None)
        filters = self.search_form.cleaned_data if self.search_form.is_valid() else {}
        profiles = services.mentor_directory().order_by(
            F("average_rating").desc(nulls_last=True), "mentor__last_name"
        )
        if query := filters.get("q"):
            profiles = profiles.filter(
                Q(title__icontains=query)
                | Q(mentor__first_name__icontains=query)
                | Q(mentor__last_name__icontains=query)
            )
        if filters.get("disponible"):
            profiles = profiles.filter(next_free_slot__isnull=False)
        return profiles

    def get_context_data(self, **kwargs):
        return super().get_context_data(search_form=self.search_form, **kwargs)


class MentorDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = (Role.APPRENANT,)
    template_name = "mentoring/mentor_detail.html"
    context_object_name = "profile"

    def get_queryset(self):
        return services.mentor_directory()

    def get_context_data(self, **kwargs):
        free_slots = services.free_slots(self.object.mentor)[:20]
        return super().get_context_data(free_slots=free_slots, **kwargs)


class SlotBookView(RoleRequiredMixin, FormView):
    allowed_roles = (Role.APPRENANT,)
    form_class = BookingForm
    template_name = "mentoring/slot_book.html"

    @cached_property
    def slot(self):
        # Chargé après le contrôle de rôle : un anonyme ou un autre rôle n'apprend rien du créneau.
        return get_object_or_404(
            AvailabilitySlot.objects.select_related("mentor"), pk=self.kwargs["pk"]
        )

    def get(self, request, *args, **kwargs):
        if self.slot.is_booked or self.slot.start <= timezone.now():
            messages.error(request, "Ce créneau n'est plus disponible. Choisissez-en un autre.")
            return redirect("mentoring:mentor_directory")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return super().get_context_data(slot=self.slot, **kwargs)

    def form_valid(self, form):
        try:
            session = services.book_slot(self.request.user, self.slot, **form.cleaned_data)
        except services.SlotUnavailable as exc:
            messages.error(self.request, str(exc))
            return redirect("mentoring:mentor_directory")
        messages.success(self.request, "Demande envoyée. Le mentor doit maintenant la confirmer.")
        return redirect("mentoring:session_detail", pk=session.pk)


# Sessions : apprenant et mentor


class ParticipantSessionMixin(RoleRequiredMixin):
    """Sessions dont l'utilisateur est l'apprenant ou le mentor ; les autres donnent 404."""

    allowed_roles = (Role.APPRENANT, Role.MENTOR)

    def get_queryset(self):
        user = self.request.user
        return MentoringSession.objects.select_related("slot__mentor", "learner", "review").filter(
            Q(learner=user) | Q(slot__mentor=user)
        )


class SessionListView(ParticipantSessionMixin, ListView):
    template_name = "mentoring/session_list.html"
    context_object_name = "sessions"
    paginate_by = PAGE_SIZE

    def get_queryset(self):
        self.filter_form = SessionFilterForm(self.request.GET or None)
        filters = self.filter_form.cleaned_data if self.filter_form.is_valid() else {}
        sessions = super().get_queryset()
        if status := filters.get("statut"):
            sessions = sessions.filter(status=status)
        if filters.get("periode") == "a_venir":
            sessions = sessions.filter(slot__end__gte=timezone.now()).order_by("slot__start")
        elif filters.get("periode") == "passees":
            sessions = sessions.filter(slot__end__lt=timezone.now())
        return sessions

    def get_context_data(self, **kwargs):
        is_learner = self.request.user.role == Role.APPRENANT
        return super().get_context_data(
            filter_form=self.filter_form, is_learner=is_learner, **kwargs
        )


class SessionDetailView(ParticipantSessionMixin, DetailView):
    template_name = "mentoring/session_detail.html"
    context_object_name = "session"

    def get_context_data(self, **kwargs):
        session = self.object
        is_mentor = session.slot.mentor_id == self.request.user.pk
        room_open = services.room_is_open(session)
        return super().get_context_data(
            is_mentor=is_mentor,
            can_answer=is_mentor and session.status == Status.DEMANDEE,
            can_complete=is_mentor and session.status == Status.CONFIRMEE,
            can_cancel=not is_mentor and session.status in (Status.DEMANDEE, Status.CONFIRMEE),
            can_review=not is_mentor
            and session.status == Status.TERMINEE
            and not hasattr(session, "review"),
            room_open=room_open,
            room_pending=session.status == Status.CONFIRMEE and not room_open,
            **kwargs,
        )


class MentorSessionMixin(RoleRequiredMixin):
    """Session dont l'utilisateur est le mentor ; chargée après le contrôle de rôle."""

    allowed_roles = (Role.MENTOR,)

    @cached_property
    def session(self):
        return get_object_or_404(
            MentoringSession.objects.select_related("slot__mentor", "learner"),
            pk=self.kwargs["pk"],
            slot__mentor=self.request.user,
        )


class LearnerSessionMixin(RoleRequiredMixin):
    """Session dont l'utilisateur est l'apprenant ; chargée après le contrôle de rôle."""

    allowed_roles = (Role.APPRENANT,)

    @cached_property
    def session(self):
        return get_object_or_404(
            MentoringSession.objects.select_related("slot__mentor", "learner"),
            pk=self.kwargs["pk"],
            learner=self.request.user,
        )


class SessionActionMixin:
    """Appelle un service, affiche son succès ou son refus, puis revient sur la session."""

    success_message = ""

    def run_action(self, action, *args):
        try:
            action(self.session, *args)
        except services.MentoringError as exc:
            messages.error(self.request, str(exc))
        else:
            messages.success(self.request, self.success_message)
        return redirect("mentoring:session_detail", pk=self.session.pk)

    def get_context_data(self, **kwargs):
        return super().get_context_data(session=self.session, **kwargs)


class SessionConfirmView(MentorSessionMixin, SessionActionMixin, View):
    http_method_names = ["post"]
    success_message = "Session confirmée. L'apprenant est prévenu par e-mail."

    def post(self, request, *args, **kwargs):
        return self.run_action(services.confirm_session)


class SessionRefuseView(MentorSessionMixin, SessionActionMixin, FormView):
    form_class = RefusalForm
    template_name = "mentoring/session_notes_form.html"
    success_message = "Session refusée. Le créneau est de nouveau libre."
    extra_context = {"page_title": "Refuser la demande", "submit_label": "Refuser la demande"}

    def form_valid(self, form):
        return self.run_action(services.refuse_session, form.cleaned_data["mentor_notes"])


class SessionCompleteView(MentorSessionMixin, SessionActionMixin, FormView):
    form_class = MentorNotesForm
    template_name = "mentoring/session_notes_form.html"
    success_message = "Session terminée. L'apprenant peut maintenant donner son avis."
    extra_context = {"page_title": "Terminer la session", "submit_label": "Terminer la session"}

    def form_valid(self, form):
        return self.run_action(services.complete_session, form.cleaned_data["mentor_notes"])


class SessionCancelView(LearnerSessionMixin, SessionActionMixin, TemplateView):
    template_name = "mentoring/session_cancel.html"
    success_message = "Session annulée. Le mentor est prévenu par e-mail."

    def post(self, request, *args, **kwargs):
        return self.run_action(services.cancel_session)


class SessionReviewView(LearnerSessionMixin, SessionActionMixin, FormView):
    form_class = SessionReviewForm
    template_name = "mentoring/session_review_form.html"
    success_message = "Merci, votre avis est enregistré."

    def form_valid(self, form):
        return self.run_action(
            services.add_review, form.cleaned_data["rating"], form.cleaned_data["comment"]
        )


class SessionRoomView(ParticipantSessionMixin, DetailView):
    template_name = "mentoring/session_room.html"
    context_object_name = "session"

    def get_object(self, queryset=None):
        session = super().get_object(queryset)
        if not services.room_is_open(session):
            raise PermissionDenied(
                "La salle ouvre 15 minutes avant le début d'une session confirmée "
                "et ferme à sa fin."
            )
        return session

    def get_context_data(self, **kwargs):
        detail_url = reverse("mentoring:session_detail", args=[self.object.pk])
        return super().get_context_data(detail_url=detail_url, **kwargs)
