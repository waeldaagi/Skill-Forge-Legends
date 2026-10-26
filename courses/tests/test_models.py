from django.test import SimpleTestCase, TestCase

from courses.models import Category, Chapter

from .factories import CategoryFactory, CourseFactory


class SlugTests(TestCase):
    def test_same_title_gets_a_numbered_slug(self):
        first = CourseFactory(title="Docker en pratique")
        second = CourseFactory(title="Docker en pratique")
        third = CourseFactory(title="Docker en pratique")

        self.assertEqual(
            [first.slug, second.slug, third.slug],
            ["docker-en-pratique", "docker-en-pratique-2", "docker-en-pratique-3"],
        )

    def test_slug_is_kept_when_the_title_changes(self):
        course = CourseFactory(title="Docker en pratique")

        course.title = "Docker et Compose en pratique"
        course.save()

        course.refresh_from_db()
        self.assertEqual(course.slug, "docker-en-pratique")

    def test_title_without_letters_still_gets_an_address(self):
        course = CourseFactory(title="!!!")

        self.assertEqual(course.slug, "cours")
        self.assertEqual(course.get_absolute_url(), "/cours/cours/")

    def test_categories_whose_names_give_the_same_slug_are_both_saved(self):
        CategoryFactory(name="C++")
        CategoryFactory(name="C#")

        slugs = Category.objects.filter(name__in=["C++", "C#"]).values_list("slug", flat=True)
        self.assertEqual(sorted(slugs), ["c", "c-2"])


class VideoEmbedTests(SimpleTestCase):
    def embed(self, url):
        return Chapter(video_url=url).video_embed_url

    def test_youtube_links_become_embed_links(self):
        expected = "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"
        for url in (
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ&t=42s",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.embed(url), expected)

    def test_vimeo_links_become_player_links(self):
        self.assertEqual(
            self.embed("https://vimeo.com/76979871"), "https://player.vimeo.com/video/76979871"
        )

    def test_unknown_or_malformed_links_are_not_embedded(self):
        for url in (
            "https://example.com/video.mp4",
            "https://www.youtube.com/watch?v=trop-court",
            "https://www.youtube.com/watch",
            "https://evil.test/youtube.com/watch?v=dQw4w9WgXcQ",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.embed(url), "")
