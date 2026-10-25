from functools import cached_property

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DeleteView, DetailView, FormView, ListView, UpdateView
from django.views.generic.detail import SingleObjectMixin

from accounts.models import User
from core.permissions import OwnerRequiredMixin, RoleRequiredMixin

from . import services
from .forms import RejectionForm, ReplyForm, ReportForm, ThreadForm, ThreadSearchForm
from .models import Reply, Report, Thread

Role = User.Role
FORUM_ROLES = (Role.APPRENANT, Role.MENTOR, Role.FORMATEUR, Role.ADMIN)
MODERATOR_ROLES = (Role.ADMIN, Role.MENTOR)
PUBLISHED_MESSAGE = "Il sera visible par tous après la vérification automatique."


def thread_url(thread, reply=None):
    url = reverse("community:thread_detail", args=[thread.pk])
    return f"{url}#reponse-{reply.pk}" if reply else url


class ForumAccessMixin(RoleRequiredMixin):
    allowed_roles = FORUM_ROLES


# Fils


class ThreadListView(ForumAccessMixin, ListView):
    template_name = "community/thread_list.html"
    context_object_name = "threads"
    paginate_by = 15

    def get_queryset(self):
        self.search_form = ThreadSearchForm(self.request.GET or None)
        filters = self.search_form.cleaned_data if self.search_form.is_valid() else {}
        threads = services.visible_threads(self.request.user)
        if query := filters.get("q"):
            threads = threads.filter(Q(title__icontains=query) | Q(content__icontains=query))
        if filters.get("resolu") == "oui":
            threads = threads.filter(is_resolved=True)
        elif filters.get("resolu") == "non":
            threads = threads.filter(is_resolved=False)
        return threads

    def get_context_data(self, **kwargs):
        return super().get_context_data(search_form=self.search_form, **kwargs)


class ThreadCreateView(ForumAccessMixin, FormView):
    form_class = ThreadForm
    template_name = "community/thread_form.html"

    def form_valid(self, form):
        thread = services.create_thread(self.request.user, **form.cleaned_data)
        messages.info(self.request, f"Votre sujet est enregistré. {PUBLISHED_MESSAGE}")
        return redirect(thread_url(thread))


class ThreadDetailView(ForumAccessMixin, DetailView):
    template_name = "community/thread_detail.html"
    context_object_name = "thread"

    def get_queryset(self):
        return services.visible_threads(self.request.user)

    def get_context_data(self, **kwargs):
        thread, user = self.object, self.request.user
        is_author = thread.author_id == user.pk
        return super().get_context_data(
            replies=services.visible_replies(thread, user),
            reply_form=ReplyForm(),
            is_author=is_author,
            can_accept=is_author or user.role == Role.MENTOR,
            **kwargs,
        )


class AuthorThreadMixin(ForumAccessMixin, OwnerRequiredMixin):
    model = Thread
    owner_field = "author"


class ThreadUpdateView(AuthorThreadMixin, UpdateView):
    form_class = ThreadForm
    template_name = "community/thread_form.html"

    def form_valid(self, form):
        services.update_thread(self.object, **form.cleaned_data)
        messages.info(self.request, f"Votre sujet est modifié. {PUBLISHED_MESSAGE}")
        return redirect(thread_url(self.object))


class ThreadDeleteView(AuthorThreadMixin, DeleteView):
    template_name = "community/thread_confirm_delete.html"
    context_object_name = "thread"
    success_url = reverse_lazy("community:thread_list")

    def form_valid(self, form):
        messages.success(self.request, "Votre sujet et ses réponses sont supprimés.")
        return super().form_valid(form)


class ThreadResolveView(AuthorThreadMixin, SingleObjectMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        thread = self.get_object()
        services.set_resolved(thread, not thread.is_resolved)
        state = "résolu" if thread.is_resolved else "sans solution"
        messages.success(request, f"Sujet marqué comme {state}.")
        return redirect(thread_url(thread))


# Réponses


class ReplyCreateView(ForumAccessMixin, FormView):
    form_class = ReplyForm
    template_name = "community/reply_form.html"

    @cached_property
    def thread(self):
        return get_object_or_404(services.visible_threads(self.request.user), pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        return super().get_context_data(thread=self.thread, **kwargs)

    def form_valid(self, form):
        try:
            reply = services.create_reply(self.thread, self.request.user, **form.cleaned_data)
        except services.ReplyNotAllowed as exc:
            messages.error(self.request, str(exc))
            return redirect(thread_url(self.thread))
        messages.info(self.request, f"Votre réponse est enregistrée. {PUBLISHED_MESSAGE}")
        return redirect(thread_url(self.thread, reply))


class AuthorReplyMixin(ForumAccessMixin, OwnerRequiredMixin):
    model = Reply
    owner_field = "author"
    context_object_name = "reply"


class ReplyUpdateView(AuthorReplyMixin, UpdateView):
    form_class = ReplyForm
    template_name = "community/reply_form.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(thread=self.object.thread, **kwargs)

    def form_valid(self, form):
        services.update_reply(self.object, **form.cleaned_data)
        messages.info(self.request, f"Votre réponse est modifiée. {PUBLISHED_MESSAGE}")
        return redirect(thread_url(self.object.thread, self.object))


class ReplyDeleteView(AuthorReplyMixin, DeleteView):
    template_name = "community/reply_confirm_delete.html"

    def get_success_url(self):
        return thread_url(self.object.thread)

    def form_valid(self, form):
        messages.success(self.request, "Votre réponse est supprimée.")
        return super().form_valid(form)


class PublishedReplyMixin(ForumAccessMixin):
    http_method_names = ["post"]

    @cached_property
    def reply(self):
        return get_object_or_404(
            Reply.objects.select_related("thread"),
            pk=self.kwargs["pk"],
            moderation_status=Reply.ModerationStatus.APPROUVE,
            thread__moderation_status=Thread.ModerationStatus.APPROUVE,
        )


class ReplyVoteView(PublishedReplyMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            services.toggle_vote(request.user, self.reply)
        except services.VoteNotAllowed as exc:
            if request.headers.get("HX-Request"):
                return HttpResponseForbidden(str(exc))
            messages.error(request, str(exc))
            return redirect(thread_url(self.reply.thread, self.reply))
        if request.headers.get("HX-Request"):
            # HTMX ne remplace que le bouton : le compteur se met à jour sans recharger la page.
            reply = services.visible_replies(self.reply.thread, request.user).get(pk=self.reply.pk)
            return render(request, "community/partials/vote_button.html", {"reply": reply})
        return redirect(thread_url(self.reply.thread, self.reply))


class ReplyAcceptView(PublishedReplyMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            services.accept_reply(request.user, self.reply)
        except services.AcceptNotAllowed as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Réponse acceptée : le sujet est marqué comme résolu.")
        return redirect(thread_url(self.reply.thread, self.reply))


# Signalements et modération


class ReportCreateView(ForumAccessMixin, FormView):
    form_class = ReportForm
    template_name = "community/report_form.html"
    target_model = Thread

    @cached_property
    def target(self):
        return get_object_or_404(
            self.target_model.objects.select_related("author"),
            pk=self.kwargs["pk"],
            moderation_status=Thread.ModerationStatus.APPROUVE,
        )

    def get_context_data(self, **kwargs):
        return super().get_context_data(target=self.target, **kwargs)

    def form_valid(self, form):
        target = self.target
        thread = target if isinstance(target, Thread) else target.thread
        try:
            services.report_post(self.request.user, target, **form.cleaned_data)
        except services.ReportNotAllowed as exc:
            messages.error(self.request, str(exc))
        else:
            messages.success(self.request, "Merci. Un modérateur va relire ce message.")
        return redirect(thread_url(thread))


class ModerationQueueView(RoleRequiredMixin, ListView):
    allowed_roles = MODERATOR_ROLES
    template_name = "community/moderation_queue.html"
    context_object_name = "reports"

    def get_queryset(self):
        self.queue = services.moderation_queue()
        return self.queue["reports"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            pending_threads=list(self.queue["threads"]),
            pending_replies=list(self.queue["replies"]),
            **kwargs,
        )
        # Un formulaire de rejet par élément, avec des id uniques : un libellé, un champ.
        for prefix, items in [
            ("sujet", context["pending_threads"]),
            ("reponse", context["pending_replies"]),
            ("signalement", context["reports"]),
        ]:
            for item in items:
                item.rejection_form = RejectionForm(auto_id=f"rejet-{prefix}-{item.pk}-%s")
        return context


class ModerationDecisionView(RoleRequiredMixin, View):
    allowed_roles = MODERATOR_ROLES
    http_method_names = ["post"]
    target_model = Thread
    decision = "approve"

    def post(self, request, *args, **kwargs):
        post = get_object_or_404(self.target_model, pk=kwargs["pk"])
        if self.decision == "approve":
            services.approve(post)
            messages.success(request, "Message publié.")
        else:
            form = RejectionForm(request.POST)
            if not form.is_valid():
                messages.error(request, "Indiquez le motif du rejet : l'auteur le lira.")
                return redirect("community:moderation_queue")
            services.reject(post, form.cleaned_data["reason"])
            messages.success(request, "Message rejeté. L'auteur verra le motif.")
        return redirect("community:moderation_queue")


class ReportDismissView(RoleRequiredMixin, View):
    allowed_roles = MODERATOR_ROLES
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        services.dismiss_report(
            get_object_or_404(Report, pk=kwargs["pk"], status=Report.Status.OUVERT)
        )
        messages.success(request, "Signalement classé sans suite : le message reste publié.")
        return redirect("community:moderation_queue")
