from functools import cached_property

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, UpdateView

from accounts.models import User
from core.permissions import OwnerRequiredMixin, RoleRequiredMixin

from .forms import (
    CertificationForm,
    CriterionForm,
    HumanReviewForm,
    RecruiterContactForm,
    SubmissionForm,
    TalentSearchForm,
)
from .models import Certificate, Certification, Criterion, Submission
from .services import (
    REVIEWABLE_STATUSES,
    contact_candidate,
    finalize_human_review,
    learner_can_submit,
    recruiter_candidates,
    submit_submission,
    verified_certificates,
)

Role = User.Role


class CertificationListView(RoleRequiredMixin, ListView):
    allowed_roles = (Role.FORMATEUR,)
    template_name = "assessment/certification_list.html"
    context_object_name = "certifications"

    def get_queryset(self):
        return Certification.objects.filter(course__trainer=self.request.user).select_related(
            "course"
        )


class TrainerCertificationFormMixin:
    """Le formulaire ne propose que les cours du formateur connecté."""

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["trainer"] = self.request.user
        return kwargs


class CertificationCreateView(RoleRequiredMixin, TrainerCertificationFormMixin, CreateView):
    allowed_roles = (Role.FORMATEUR,)
    form_class = CertificationForm
    template_name = "assessment/certification_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Certification créée.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("assessment:criterion_create", kwargs={"certification_pk": self.object.pk})


class CertificationUpdateView(RoleRequiredMixin, TrainerCertificationFormMixin, UpdateView):
    allowed_roles = (Role.FORMATEUR,)
    model = Certification
    form_class = CertificationForm
    template_name = "assessment/certification_form.html"
    success_url = reverse_lazy("assessment:certification_list")

    def get_queryset(self):
        return Certification.objects.filter(course__trainer=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Certification mise à jour.")
        return super().form_valid(form)


class CertificationDeleteView(RoleRequiredMixin, DeleteView):
    allowed_roles = (Role.FORMATEUR,)
    model = Certification
    template_name = "assessment/certification_confirm_delete.html"
    success_url = reverse_lazy("assessment:certification_list")

    def get_queryset(self):
        return Certification.objects.filter(course__trainer=self.request.user)


class CriterionCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = (Role.FORMATEUR,)
    model = Criterion
    form_class = CriterionForm
    template_name = "assessment/criterion_form.html"

    @cached_property
    def certification(self):
        # Chargée après le contrôle de rôle : un anonyme est redirigé, un autre rôle reçoit 403.
        return get_object_or_404(
            Certification, pk=self.kwargs["certification_pk"], course__trainer=self.request.user
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = Criterion(certification=self.certification)
        return kwargs

    def form_valid(self, form):
        form.instance.certification = self.certification
        messages.success(self.request, "Critère enregistré.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        return super().get_context_data(certification=self.certification, **kwargs)

    def get_success_url(self):
        return reverse(
            "assessment:criterion_create", kwargs={"certification_pk": self.certification.pk}
        )


class CriterionUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = (Role.FORMATEUR,)
    model = Criterion
    form_class = CriterionForm
    template_name = "assessment/criterion_form.html"

    def get_queryset(self):
        return Criterion.objects.filter(certification__course__trainer=self.request.user)

    def get_context_data(self, **kwargs):
        return super().get_context_data(certification=self.object.certification, **kwargs)

    def get_success_url(self):
        return reverse("assessment:certification_list")


class CriterionDeleteView(RoleRequiredMixin, DeleteView):
    allowed_roles = (Role.FORMATEUR,)
    model = Criterion
    template_name = "assessment/criterion_confirm_delete.html"

    def get_queryset(self):
        return Criterion.objects.filter(certification__course__trainer=self.request.user)

    def get_success_url(self):
        return reverse("assessment:certification_list")


class CertificationCatalogView(RoleRequiredMixin, ListView):
    allowed_roles = (Role.APPRENANT,)
    template_name = "assessment/certification_catalog.html"
    context_object_name = "certifications"

    def get_queryset(self):
        learner_certificates = Certificate.objects.filter(
            learner=self.request.user,
            is_revoked=False,
        )
        return (
            Certification.objects.filter(is_active=True)
            .select_related("course")
            .prefetch_related(
                Prefetch(
                    "certificates",
                    queryset=learner_certificates,
                    to_attr="learner_certificates",
                )
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # « Soumettre » n'est proposé que si le cours est terminé (règle du service).
        for certification in context["certifications"]:
            certification.can_submit = learner_can_submit(self.request.user, certification)
        return context


class SubmissionCreateView(RoleRequiredMixin, FormView):
    allowed_roles = (Role.APPRENANT,)
    form_class = SubmissionForm
    template_name = "assessment/submission_form.html"

    @cached_property
    def certification(self):
        return get_object_or_404(Certification, pk=self.kwargs["certification_pk"], is_active=True)

    def get_context_data(self, **kwargs):
        return super().get_context_data(certification=self.certification, **kwargs)

    def form_valid(self, form):
        try:
            submission = submit_submission(
                learner=self.request.user,
                certification=self.certification,
                text_response=form.cleaned_data["text_response"],
                repository_url=form.cleaned_data["repository_url"],
                attachment=form.cleaned_data["attachment"],
            )
        except ValidationError as exc:
            form.add_error(None, " ".join(exc.messages))
            return self.form_invalid(form)
        except PermissionDenied as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, "Soumission envoyée. L'évaluation IA démarre.")
        return redirect("assessment:submission_detail", pk=submission.pk)


class SubmissionListView(RoleRequiredMixin, ListView):
    allowed_roles = (Role.APPRENANT,)
    template_name = "assessment/submission_list.html"
    context_object_name = "submissions"

    def get_queryset(self):
        return Submission.objects.filter(learner=self.request.user).select_related(
            "certification", "ai_job"
        )


class SubmissionDetailView(RoleRequiredMixin, OwnerRequiredMixin, DetailView):
    allowed_roles = (Role.APPRENANT,)
    model = Submission
    owner_field = "learner"
    template_name = "assessment/submission_detail.html"
    context_object_name = "submission"


class ReviewQueueView(RoleRequiredMixin, ListView):
    allowed_roles = (Role.MENTOR, Role.FORMATEUR)
    template_name = "assessment/review_queue.html"
    context_object_name = "submissions"

    def get_queryset(self):
        queryset = Submission.objects.filter(
            status__in=[Submission.Status.EVALUEE_IA, Submission.Status.EN_REVUE]
        ).select_related("learner", "certification", "ai_evaluation")
        if self.request.user.role == Role.FORMATEUR:
            queryset = queryset.filter(certification__course__trainer=self.request.user)
        return queryset


class SubmissionReviewView(RoleRequiredMixin, FormView):
    allowed_roles = (Role.MENTOR, Role.FORMATEUR)
    template_name = "assessment/review_form.html"
    form_class = HumanReviewForm

    @cached_property
    def submission(self):
        # Seules les soumissions en attente se relisent : une décision rendue ne change plus
        # (un certificat a pu être délivré). Un formateur ne relit que ses certifications.
        queryset = Submission.objects.select_related(
            "learner", "certification__course", "ai_evaluation"
        ).filter(status__in=REVIEWABLE_STATUSES)
        if self.request.user.role == Role.FORMATEUR:
            queryset = queryset.filter(certification__course__trainer=self.request.user)
        return get_object_or_404(queryset, pk=self.kwargs["pk"])

    def get_initial(self):
        # Le relecteur part du score proposé par l'IA, qu'il confirme ou corrige.
        evaluation = getattr(self.submission, "ai_evaluation", None)
        return {"final_score": evaluation.total_score} if evaluation else {}

    def get_context_data(self, **kwargs):
        return super().get_context_data(submission=self.submission, **kwargs)

    def form_valid(self, form):
        _review, certificate = finalize_human_review(
            submission=self.submission,
            reviewer=self.request.user,
            final_score=form.cleaned_data["final_score"],
            decision=form.cleaned_data["decision"],
            comment=form.cleaned_data["comment"],
            overrides_ai=form.cleaned_data["overrides_ai"],
            site_url=self.request.build_absolute_uri("/"),
        )
        if certificate:
            messages.success(self.request, "Revue validée. Certificat délivré.")
        else:
            messages.success(self.request, "Revue enregistrée.")
        return redirect("assessment:review_queue")


class CertificateVerifyView(DetailView):
    model = Certificate
    slug_field = "public_id"
    slug_url_kwarg = "public_id"
    context_object_name = "certificate"
    template_name = "assessment/certificate_verify.html"


class CertificateAPIView(DetailView):
    model = Certificate
    slug_field = "public_id"
    slug_url_kwarg = "public_id"

    def render_to_response(self, context, **response_kwargs):
        certificate = context["object"]
        return JsonResponse(
            {
                "public_id": str(certificate.public_id),
                "learner": str(certificate.learner),
                "certification": certificate.certification.title,
                "issued_at": certificate.issued_at.isoformat(),
                "is_revoked": certificate.is_revoked,
            }
        )


class TalentSearchView(RoleRequiredMixin, ListView):
    allowed_roles = (Role.RECRUTEUR,)
    template_name = "assessment/talent_search.html"
    context_object_name = "learners"

    def get_queryset(self):
        self.form = TalentSearchForm(self.request.GET or None)
        filters = self.form.cleaned_data if self.form.is_valid() else {}
        return recruiter_candidates(
            query=filters.get("q", ""),
            skill=filters.get("skill"),
            certification=filters.get("certification"),
        )

    def get_context_data(self, **kwargs):
        return super().get_context_data(form=self.form, **kwargs)


class TalentProfileView(RoleRequiredMixin, DetailView):
    allowed_roles = (Role.RECRUTEUR,)
    model = User
    template_name = "assessment/talent_profile.html"
    context_object_name = "learner"

    def get_queryset(self):
        return recruiter_candidates()

    def get_context_data(self, **kwargs):
        learner = self.object
        return super().get_context_data(certificates=verified_certificates(learner), **kwargs)


class RecruiterContactView(RoleRequiredMixin, FormView):
    allowed_roles = (Role.RECRUTEUR,)
    form_class = RecruiterContactForm
    template_name = "assessment/recruiter_contact.html"

    @cached_property
    def learner(self):
        return get_object_or_404(recruiter_candidates(), pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        return super().get_context_data(learner=self.learner, **kwargs)

    def form_valid(self, form):
        contact_candidate(
            recruiter=self.request.user,
            learner=self.learner,
            subject=form.cleaned_data["subject"],
            message=form.cleaned_data["message"],
        )
        messages.success(self.request, "Message envoyé au candidat.")
        return redirect("assessment:talent_profile", pk=self.learner.pk)
