import factory

from accounts.tests.factories import UserFactory
from courses.models import Category, Chapter, Choice, Course, Question, Quiz


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda number: f"Catégorie {number}")


class TrainerFactory(UserFactory):
    """Formateur vérifié : seul un formateur vérifié peut publier."""

    role = "FORMATEUR"
    is_verified = True


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


class QuizFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Quiz

    chapter = factory.SubFactory(ChapterFactory)
    title = factory.Sequence(lambda number: f"Quiz {number}")
    is_published = True


class QuestionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Question

    quiz = factory.SubFactory(QuizFactory)
    statement = factory.Sequence(lambda number: f"Question {number}")
    explanation = "Explication de la bonne réponse."
    evidence = "Le contenu pédagogique du chapitre."
    order = factory.Sequence(lambda number: number + 1)


class ChoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Choice

    question = factory.SubFactory(QuestionFactory)
    text = factory.Sequence(lambda number: f"Choix {number}")
    is_correct = False


def complete_question(quiz, order=1, correct=1):
    """Question de quatre choix, dont le choix numéro ``correct`` est la bonne réponse."""
    question = QuestionFactory(quiz=quiz, order=order)
    for index in range(1, 5):
        ChoiceFactory(question=question, text=f"Réponse {index}", is_correct=index == correct)
    return question
