from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from accounts.tests.factories import UserFactory
from mentoring.forms import (
    DATETIME_LOCAL_FORMAT,
    AvailabilitySlotForm,
    BookingForm,
    MentorProfileForm,
    RefusalForm,
    SessionReviewForm,
)
from mentoring.models import AvailabilitySlot
from mentoring.tests.factories import AvailabilitySlotFactory, in_days


def local(moment):
    return timezone.localtime(moment).strftime(DATETIME_LOCAL_FORMAT)


class AvailabilitySlotFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mentor = UserFactory(role=User.Role.MENTOR)

    def form(self, start, end):
        return AvailabilitySlotForm(
            data={"start": local(start), "end": local(end)},
            instance=AvailabilitySlot(mentor=self.mentor),
        )

    def test_browser_datetime_value_is_accepted(self):
        form = self.form(in_days(2), in_days(2) + timedelta(hours=1))

        self.assertTrue(form.is_valid(), form.errors)

    def test_overlap_is_reported_as_a_form_error(self):
        AvailabilitySlotFactory(mentor=self.mentor, start=in_days(2))

        form = self.form(in_days(2) + timedelta(minutes=30), in_days(2) + timedelta(minutes=90))

        self.assertFalse(form.is_valid())
        self.assertIn("chevauche", form.non_field_errors()[0])

    def test_past_start_is_reported_on_the_start_field(self):
        form = self.form(timezone.now() - timedelta(days=1), timezone.now())

        self.assertFalse(form.is_valid())
        self.assertIn("dans le futur", form.errors["start"][0])

    def test_inputs_refuse_past_dates_in_the_browser(self):
        form = AvailabilitySlotForm()

        self.assertIn("min", form.fields["start"].widget.attrs)
        self.assertEqual(form.fields["end"].widget.input_type, "datetime-local")


class BookingFormTests(TestCase):
    def test_topic_and_blocker_are_required(self):
        form = BookingForm(data={"topic": "", "blocker_description": ""})

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["topic"], ["Ce champ est obligatoire."])
        self.assertIn("blocker_description", form.errors)


class MentorNotesFormsTests(TestCase):
    def test_refusal_requires_a_reason(self):
        form = RefusalForm(data={"mentor_notes": ""})

        self.assertFalse(form.is_valid())
        self.assertIn("mentor_notes", form.errors)


class SessionReviewFormTests(TestCase):
    def test_rating_outside_the_choices_is_refused(self):
        form = SessionReviewForm(data={"rating": "6", "comment": ""})

        self.assertFalse(form.is_valid())
        self.assertIn("rating", form.errors)

    def test_rating_is_converted_to_an_integer(self):
        form = SessionReviewForm(data={"rating": "4", "comment": "Très clair."})

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["rating"], 4)


class MentorProfileFormTests(TestCase):
    def test_experience_above_50_years_is_refused(self):
        form = MentorProfileForm(data={"title": "Développeur Django", "years_of_experience": 51})

        self.assertFalse(form.is_valid())
        self.assertIn("years_of_experience", form.errors)
