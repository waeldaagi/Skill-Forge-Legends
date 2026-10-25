from django.template import Context, Template
from django.test import RequestFactory, SimpleTestCase


class PageQueryTests(SimpleTestCase):
    def render(self, query_string, page_number):
        request = RequestFactory().get(f"/mentorat/sessions/?{query_string}")
        template = Template("{% load pagination %}{% page_query number %}")
        return template.render(Context({"request": request, "number": page_number}))

    def test_next_page_link_keeps_the_list_filters(self):
        self.assertEqual(self.render("statut=CONFIRMEE&page=1", 2), "?statut=CONFIRMEE&amp;page=2")

    def test_page_is_added_when_the_list_has_no_filter(self):
        self.assertEqual(self.render("", 3), "?page=3")
