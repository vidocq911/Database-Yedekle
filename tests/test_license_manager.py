import unittest
from unittest.mock import patch

import license_manager


class LicenseManagerPreflightTests(unittest.TestCase):
    def test_missing_public_key_fails_before_network_request(self):
        with patch.object(
            license_manager, "_public_jwk",
            side_effect=FileNotFoundError("public key missing"),
        ), patch.object(license_manager.urllib.request, "urlopen") as urlopen:
            with self.assertRaises(FileNotFoundError):
                license_manager.activate("TEST-LICENSE-KEY")
            urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
