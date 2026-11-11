"""Isolated tests for the local account recovery and CSV append behavior."""

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import auth


class AdminRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.users = self.root / "users.json"
        self.access = self.root / "user_access_log.csv"
        self.activity = self.root / "activity_log.csv"
        self.users.write_text(json.dumps({
            "admin": {"user_id": "admin", "salt": "11" * 16, "password_hash": "22" * 32},
            "analyst": {"user_id": "analyst", **auth.make_password_record("analyst-password-123")},
        }), encoding="utf-8")
        self.access.write_text("timestamp_local,user_id,action\nold,analyst,login_success\n", encoding="utf-8")
        self.activity.write_text(
            "timestamp_local,user_id,category,action,details\nold,analyst,test,prior,preserved\n",
            encoding="utf-8",
        )
        self.paths = patch.multiple(
            auth, USERS_FILE=self.users, ACCESS_LOG=self.access, ACTIVITY_LOG=self.activity,
        )
        self.paths.start()
        self.addCleanup(self.paths.stop)
        self.addCleanup(self.temp_dir.cleanup)

    def test_login_and_unknown_legacy_scheme(self):
        self.assertEqual(auth.verify_login("ANALYST", "analyst-password-123"), (True, "user"))
        self.assertEqual(auth.verify_login("analyst", "wrong-password"), (False, None))
        with self.assertRaises(auth.UnsupportedPasswordScheme):
            auth.verify_login("admin", "not-verified")

    def test_recovery_gates_backup_role_preservation_and_login(self):
        for password, owned, phrase in (
            ("short", True, "RESET ADMIN PASSWORD"),
            ("valid-password-123", False, "RESET ADMIN PASSWORD"),
            ("valid-password-123", True, "wrong"),
        ):
            with self.subTest(password=password, owned=owned, phrase=phrase):
                with self.assertRaises(ValueError):
                    auth.recover_admin_password(password, ownership_confirmed=owned, confirmation=phrase)

        backup = auth.recover_admin_password(
            "new-admin-password-456", ownership_confirmed=True,
            confirmation="RESET ADMIN PASSWORD",
        )
        original = json.loads(backup.read_text(encoding="utf-8"))
        current = json.loads(self.users.read_text(encoding="utf-8"))
        self.assertTrue(backup.is_file())
        self.assertEqual(current["analyst"], original["analyst"])
        self.assertEqual(current["admin"]["password_scheme"], "pbkdf2_sha256")
        self.assertEqual(current["admin"]["iterations"], 600_000)
        self.assertEqual(current["admin"]["role"], "admin")
        self.assertEqual(auth.verify_login("admin", "new-admin-password-456"), (True, "admin"))
        self.assertEqual(auth.verify_login("admin", "wrong-password"), (False, None))

    def test_existing_user_refused_logout_and_csv_audit_append(self):
        with self.assertRaises(ValueError):
            auth.save_user("ANALYST", "another-password-123")
        auth.log_access("admin", "logout")
        auth.log_activity("admin", "security", "admin_password_recovered", "explicit recovery")

        with self.access.open(encoding="utf-8", newline="") as handle:
            access_rows = list(csv.DictReader(handle))
        with self.activity.open(encoding="utf-8", newline="") as handle:
            activity_rows = list(csv.DictReader(handle))
        self.assertEqual([row["action"] for row in access_rows], ["login_success", "logout"])
        self.assertEqual([row["action"] for row in activity_rows], ["prior", "admin_password_recovered"])
        content = self.activity.read_bytes()
        self.assertNotIn(b"\xef\xbb\xbf", content)
        self.assertNotIn(b"another-password-123", content)
        self.assertNotIn(b"22" * 32, content)


if __name__ == "__main__":
    unittest.main()
