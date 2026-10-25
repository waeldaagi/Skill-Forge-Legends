from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.test import RequestFactory, TestCase
from django.views import View
from django.views.generic import DetailView

from accounts.models import User
from accounts.tests.factories import UserFactory
from core.models import AIJob
from core.permissions import OwnerRequiredMixin, RoleRequiredMixin, role_required


class MentorOnlyView(RoleRequiredMixin, View):
    allowed_roles = (User.Role.MENTOR,)

    def get(self, request):
        return HttpResponse("espace mentor")


@role_required(User.Role.FORMATEUR, User.Role.MENTOR)
def teaching_view(request):
    return HttpResponse("espace pédagogique")


class OwnJobView(OwnerRequiredMixin, DetailView):
    model = AIJob
    owner_field = "user"

    def render_to_response(self, context, **response_kwargs):
        return HttpResponse(str(self.object.pk))


def get(view, user, **kwargs):
    request = RequestFactory().get("/espace/")
    request.user = user
    return view(request, **kwargs)


class RoleRequiredMixinTests(TestCase):
    def test_anonymous_visitor_is_sent_to_the_login_page(self):
        response = get(MentorOnlyView.as_view(), AnonymousUser())

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/comptes/connexion/?next="))

    def test_allowed_role_gets_the_page(self):
        response = get(MentorOnlyView.as_view(), UserFactory(role=User.Role.MENTOR))

        self.assertEqual(response.content, b"espace mentor")

    def test_every_other_role_is_refused(self):
        for role in User.Role:
            if role == User.Role.MENTOR:
                continue
            with self.subTest(role=role), self.assertRaises(PermissionDenied):
                get(MentorOnlyView.as_view(), UserFactory(role=role))


class RoleRequiredDecoratorTests(TestCase):
    def test_anonymous_visitor_is_sent_to_the_login_page(self):
        response = get(teaching_view, AnonymousUser())

        self.assertEqual(response.status_code, 302)

    def test_any_listed_role_gets_the_page(self):
        for role in (User.Role.FORMATEUR, User.Role.MENTOR):
            with self.subTest(role=role):
                response = get(teaching_view, UserFactory(role=role))
                self.assertEqual(response.status_code, 200)

    def test_unlisted_role_is_refused(self):
        with self.assertRaises(PermissionDenied):
            get(teaching_view, UserFactory(role=User.Role.RECRUTEUR))

    def test_decorated_view_keeps_its_name(self):
        self.assertEqual(teaching_view.__name__, "teaching_view")


class OwnerRequiredMixinTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = UserFactory()
        cls.job = AIJob.objects.create(feature="classement_demo", user=cls.owner)

    def test_owner_reaches_the_object(self):
        response = get(OwnJobView.as_view(), self.owner, pk=self.job.pk)

        self.assertEqual(response.content.decode(), str(self.job.pk))

    def test_object_of_another_user_is_not_found(self):
        with self.assertRaises(Http404):
            get(OwnJobView.as_view(), UserFactory(), pk=self.job.pk)

    def test_anonymous_visitor_is_sent_to_the_login_page(self):
        response = get(OwnJobView.as_view(), AnonymousUser(), pk=self.job.pk)

        self.assertEqual(response.status_code, 302)
