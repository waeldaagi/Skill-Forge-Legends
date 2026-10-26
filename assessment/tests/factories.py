import factory
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import User
from accounts.tests.factories import UserFactory
from assessment.models import Certification, Criterion, Submission
from courses.tests.factories import CourseFactory


class LearnerFactory(UserFactory):
    role = User.Role.APPRENANT


class TrainerFactory(UserFactory):
    role = User.Role.FORMATEUR
    is_verified = True


class MentorFactory(UserFactory):
    role = User.Role.MENTOR
    is_verified = True


class RecruiterFactory(UserFactory):
    role = User.Role.RECRUTEUR


class CertificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Certification

    course = factory.SubFactory(CourseFactory)
    title = factory.Sequence(lambda n: f"Certification {n}")
    instructions = "Fournissez une preuve détaillée et des tests."
    passing_score = 70
    max_attempts = 3
    is_active = True


class CriterionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Criterion

    certification = factory.SubFactory(CertificationFactory)
    name = factory.Sequence(lambda n: f"Critère {n}")
    description = "Description du critère"
    weight = 50


class SubmissionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Submission

    learner = factory.SubFactory(LearnerFactory)
    certification = factory.SubFactory(CertificationFactory)
    text_response = "J'ai appliqué les patterns demandés avec tests."
    repository_url = "https://github.com/example/skillforge-proof"
    attachment = factory.LazyFunction(
        lambda: SimpleUploadedFile("preuve.txt", b"preuve", content_type="text/plain")
    )
    attempt_number = 1
    status = Submission.Status.SOUMISE


def ready_certification(certification):
    CriterionFactory(certification=certification, weight=60, name="Architecture")
    CriterionFactory(certification=certification, weight=40, name="Tests")
    return certification
