"""Offline checks for the one-click repository metadata updater."""

import unittest

from scripts import update_repository_discoverability as metadata


class TopicMergeTests(unittest.TestCase):
    def test_preserves_existing_topics_and_adds_discovery_topics(self):
        actual = metadata.merged_topics(["existing-project-topic", "qec"])
        self.assertEqual(actual[0], "existing-project-topic")
        self.assertEqual(actual.count("qec"), 1)
        for topic in metadata.DISCOVERY_TOPICS:
            self.assertIn(topic, actual)

    def test_idempotent(self):
        once = metadata.merged_topics(["existing-project-topic", "qec"])
        self.assertEqual(once, metadata.merged_topics(once))

    def test_rejects_topic_overflow_without_removing_originals(self):
        existing = [f"existing-topic-{i}" for i in range(20)]
        with self.assertRaisesRegex(ValueError, "20-topic limit"):
            metadata.merged_topics(existing)

    def test_rejects_invalid_existing_topic(self):
        with self.assertRaisesRegex(ValueError, "Invalid GitHub topic"):
            metadata.merged_topics(["Not Valid!"])

    def test_public_description_is_short(self):
        self.assertLessEqual(len(metadata.DESCRIPTION), 350)


if __name__ == "__main__":
    unittest.main()
