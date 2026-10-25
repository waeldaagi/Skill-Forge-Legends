import factory

from accounts.tests.factories import UserFactory
from courses.models import Category, Chapter, Course


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda number: f"Catégorie {number}")


class TrainerFactory(UserFactory):
    role = "FORMATEUR"


class CourseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Course

    title = factory.Sequence(lambda number: f"Django appliqué {number}")
    description = "Construire une application Django maintenable."
    level = Course.Level.BEGINNER
    category = factory.SubFactory(CategoryFactory)
    trainer = factory.SubFactory(TrainerFactory)
    status = Course.Status.PUBLISHED


class ChapterFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Chapter

    course = factory.SubFactory(CourseFactory)
    title = factory.Sequence(lambda number: f"Chapitre {number}")
    order = factory.Sequence(lambda number: number + 1)
    content = "Le contenu pédagogique du chapitre."
