"""Offline tests for creating one verified community discussion."""

import unittest
from scripts import publish_welcome_discussion as welcome


class DiscussionSafetyTests(unittest.TestCase):
    def test_pick_general_category(self):
        options = [
            {"id": "a", "name": "Announcements"},
            {"id": "b", "name": "General"},
        ]
        self.assertEqual(welcome.category_id(options), "b")

    def test_fallback_is_explicit(self):
        self.assertEqual(welcome.category_id([{"id": "x", "name": "Show and tell"}]), "x")

    def test_empty_categories_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "No GitHub Discussion categories"):
            welcome.category_id([])

    def test_skip_already_published(self):
        url = "https://github.com/hamidbahri92/Aegis-QEC/discussions/1"
        self.assertEqual(
            welcome.find_existing([{"title": welcome.TITLE, "url": url}]),
            url,
        )

    def test_does_not_skip_unrelated_discussion(self):
        self.assertIsNone(welcome.find_existing([{"title": "Other title", "url": "x"}]))

    def test_visitor_invitation_contains_real_project_links(self):
        self.assertIn("/issues/50", welcome.BODY)
        self.assertIn("/issues/51", welcome.BODY)
        self.assertIn("Stim", welcome.BODY)
        self.assertIn("PyMatching", welcome.BODY)


if __name__ == "__main__":
    unittest.main()
