"""Matrice d'accès : chaque URL du mentorat, pour chaque rôle et pour un visiteur anonyme.

Les utilisateurs de la matrice ne sont propriétaires d'aucun objet : un rôle autorisé reçoit 404
sur le créneau ou la session d'un autre. Le tableau de docs/modules/mentoring.md reprend ces règles.
"""

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounts.tests.factories import UserFactory
from mentoring.tests.factories import (
    AvailabilitySlotFactory,
    MentoringSessionFactory,
    MentorProfileFactory,
)

ANONYMOUS = None
Role = User.Role


def expected(allowed_roles, allowed_status=200):
    statuses = {ANONYMOUS: 302}
    for role in Role:
        statuses[role] = allowed_status if role in allowed_roles else 403
    return statuses


class MentoringAccessMatrixTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profile = MentorProfileFactory()
        cls.slot = AvailabilitySlotFactory(mentor=cls.profile.mentor)
        cls.session = MentoringSessionFactory(slot__mentor=cls.profile.mentor)
        # Mentor vérifié : seul un mentor vérifié publie des créneaux (voir test_views.py).
        cls.users = {role: UserFactory(role=role, is_verified=role == Role.MENTOR) for role in Role}

    def check(self, url, statuses, method="get"):
        for role, status in statuses.items():
            with self.subTest(url=url, role=role):
                self.client.logout()
                if role is not ANONYMOUS:
                    self.client.force_login(self.users[role])
                response = getattr(self.client, method)(url)
                self.assertEqual(response.status_code, status)

    def test_learner_pages(self):
        learner_only = expected({Role.APPRENANT})
        self.check(reverse("mentoring:mentor_directory"), learner_only)
        self.check(reverse("mentoring:mentor_detail", args=[self.profile.pk]), learner_only)
        self.check(reverse("mentoring:slot_book", args=[self.slot.pk]), learner_only)

    def test_mentor_pages(self):
        mentor_only = expected({Role.MENTOR})
        self.check(reverse("mentoring:profile_edit"), mentor_only)
        self.check(reverse("mentoring:slot_list"), mentor_only)
        self.check(reverse("mentoring:slot_create"), mentor_only)

    def test_slot_of_another_mentor_is_not_found(self):
        other_mentors_slot = expected({Role.MENTOR}, allowed_status=404)
        self.check(reverse("mentoring:slot_update", args=[self.slot.pk]), other_mentors_slot)
        self.check(reverse("mentoring:slot_delete", args=[self.slot.pk]), other_mentors_slot)

    def test_session_list_is_shared_by_learners_and_mentors(self):
        self.check(reverse("mentoring:session_list"), expected({Role.APPRENANT, Role.MENTOR}))

    def test_session_of_other_participants_is_not_found(self):
        participants = expected({Role.APPRENANT, Role.MENTOR}, allowed_status=404)
        self.check(reverse("mentoring:session_detail", args=[self.session.pk]), participants)
        self.check(reverse("mentoring:session_room", args=[self.session.pk]), participants)

    def test_mentor_actions_on_another_mentors_session_are_not_found(self):
        not_owner = expected({Role.MENTOR}, allowed_status=404)
        pk = self.session.pk
        self.check(reverse("mentoring:session_confirm", args=[pk]), not_owner, method="post")
        self.check(reverse("mentoring:session_refuse", args=[pk]), not_owner)
        self.check(reverse("mentoring:session_complete", args=[pk]), not_owner)

    def test_learner_actions_on_another_learners_session_are_not_found(self):
        not_owner = expected({Role.APPRENANT}, allowed_status=404)
        pk = self.session.pk
        self.check(reverse("mentoring:session_cancel", args=[pk]), not_owner)
        self.check(reverse("mentoring:session_review", args=[pk]), not_owner)
