from django.contrib import messages
from django.core.exceptions import PermissionDenied
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
    contact_candidate,
    finalize_human_review,
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


class CertificationCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = (Role.FORMATEUR,)
    form_class = CertificationForm
    template_name = "assessment/certification_form.html"

    def form_valid(self, form):
        if form.instance.course.trainer_id != self.request.user.pk:
            raise PermissionDenied("Vous ne pouvez créer une certification que sur vos cours.")
        messages.success(self.request, "Certification créée.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("assessment:criterion_create", kwargs={"certification_pk": self.object.pk})


class CertificationUpdateView(RoleRequiredMixin, UpdateView):
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

    def dispatch(self, request, *args, **kwargs):
        self.certification = get_object_or_404(
            Certification, pk=kwargs["certification_pk"], course__trainer=request.user
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if "instance" not in kwargs or kwargs["instance"] is None:
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


class SubmissionCreateView(RoleRequiredMixin, FormView):
    allowed_roles = (Role.APPRENANT,)
    form_class = SubmissionForm
    template_name = "assessment/submission_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.certification = get_object_or_404(
            Certification, pk=kwargs["certification_pk"], is_active=True
        )
        return super().dispatch(request, *args, **kwargs)

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
        except Exception as exc:
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

    def dispatch(self, request, *args, **kwargs):
        queryset = Submission.objects.select_related("certification__course", "ai_evaluation")
        self.submission = get_object_or_404(queryset, pk=kwargs["pk"])
        if (
            request.user.role == Role.FORMATEUR
            and self.submission.certification.course.trainer_id != request.user.pk
        ):
            raise PermissionDenied(
                "Vous ne pouvez relire que les soumissions de vos certifications."
            )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return super().get_context_data(submission=self.submission, **kwargs)

    def form_valid(self, form):
        review, certificate = finalize_human_review(
            submission=self.submission,
            reviewer=self.request.user,
            final_score=form.cleaned_data["final_score"],
            decision=form.cleaned_data["decision"],
            comment=form.cleaned_data["comment"],
            overrides_ai=form.cleaned_data["overrides_ai"],
        )
        del review
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

    def dispatch(self, request, *args, **kwargs):
        self.learner = get_object_or_404(recruiter_candidates(), pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

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
