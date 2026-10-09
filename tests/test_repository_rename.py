"""Offline, network-free checks for the guarded in-place GitHub repository rename."""

import os
import unittest
from unittest.mock import patch

from scripts import rename_repository as rename


class RepositoryRenameSafetyTests(unittest.TestCase):
    def test_identity_matches_existing_repository_id_and_exact_name(self):
        rename.validate_identity(
            {"id": rename.REPO_ID, "full_name": rename.EXPECTED_OLD},
            rename.EXPECTED_OLD,
        )

    def test_cannot_target_other_repository_with_same_name(self):
        with self.assertRaisesRegex(RuntimeError, "identity"):
            rename.validate_identity(
                {"id": 22, "full_name": rename.EXPECTED_OLD},
                rename.EXPECTED_OLD,
            )

    def test_cannot_target_other_repository_with_same_id(self):
        with self.assertRaisesRegex(RuntimeError, "identity"):
            rename.validate_identity(
                {"id": rename.REPO_ID, "full_name": "another-owner/Aegis"},
                rename.EXPECTED_OLD,
            )

    def test_all_repository_links_staged_before_rename(self):
        rename.check_sources_prepared()

    def test_deny_rename_on_any_branch_other_than_main(self):
        with patch.dict(
            os.environ,
            {"GITHUB_REF": "refs/heads/feature", "GITHUB_REPOSITORY": rename.EXPECTED_OLD},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "main"):
                rename.main()

    def test_deny_wrong_repository(self):
        with patch.dict(
            os.environ,
            {"GITHUB_REF": "refs/heads/main", "GITHUB_REPOSITORY": "another-user/Aegis"},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "expected identity"):
                rename.main()

    def test_deny_without_explicit_confirmation(self):
        with patch.dict(
            os.environ,
            {"GITHUB_REF": "refs/heads/main", "GITHUB_REPOSITORY": rename.EXPECTED_OLD},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "confirmation"):
                rename.main()

    def test_deny_without_actions_secret(self):
        with patch.dict(
            os.environ,
            {
                "GITHUB_REF": "refs/heads/main",
                "GITHUB_REPOSITORY": rename.EXPECTED_OLD,
                "AEGIS_RENAME_CONFIRM": rename.NEW_NAME,
            },
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "Actions secret AEGIS"):
                rename.main()


if __name__ == "__main__":
    unittest.main()
