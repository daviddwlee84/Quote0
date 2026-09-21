import os
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

from quote0.config import DeviceCredentials, resolve_device


class ResolveDeviceTests(unittest.TestCase):
    def setUp(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.directory = Path(temporary_directory.name)
        original_directory = Path.cwd()
        os.chdir(self.directory)
        self.addCleanup(os.chdir, original_directory)
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    def write_config(self, content):
        path = self.directory / "quote0.toml"
        path.write_text(content, encoding="utf-8")
        return path

    def test_legacy_environment_does_not_read_config(self):
        os.environ.update(DOT_API_KEY="legacy-key", DOT_DEVICE_ID="legacy-id")
        self.write_config("not valid TOML at all")
        self.assertEqual(resolve_device(), DeviceCredentials("legacy-key", "legacy-id"))
        self.assertEqual(
            resolve_device(config=Path("missing.toml")),
            DeviceCredentials("legacy-key", "legacy-id"),
        )

    def test_loads_dotenv_at_runtime_without_overriding_exported_values(self):
        (self.directory / ".env").write_text(
            "DOT_API_KEY=dotenv-key\nDOT_DEVICE_ID=dotenv-id\n", encoding="utf-8"
        )
        os.environ["DOT_API_KEY"] = "exported-key"
        self.assertEqual(
            resolve_device(), DeviceCredentials("exported-key", "dotenv-id")
        )

    def test_explicit_legacy_values_override_environment(self):
        os.environ.update(DOT_API_KEY="legacy-key", DOT_DEVICE_ID="legacy-id")
        self.assertEqual(
            resolve_device(api_key="explicit-key", device_id="explicit-id"),
            DeviceCredentials("explicit-key", "explicit-id"),
        )

    def test_named_devices_use_their_own_credentials(self):
        self.write_config(
            '[devices.desk]\ndevice_id = "desk-id"\napi_key_env = "DESK_KEY"\n'
            '[devices.office]\ndevice_id = "office-id"\napi_key_env = "OFFICE_KEY"\n'
        )
        os.environ.update(
            DESK_KEY="desk-key",
            OFFICE_KEY="office-key",
            DOT_API_KEY="unrelated-key",
            DOT_DEVICE_ID="unrelated-id",
        )
        self.assertEqual(
            resolve_device(device="desk"), DeviceCredentials("desk-key", "desk-id")
        )
        self.assertEqual(
            resolve_device(device="office"),
            DeviceCredentials("office-key", "office-id"),
        )

    def test_named_key_can_be_loaded_from_dotenv(self):
        config = self.write_config(
            '[devices.desk]\ndevice_id = "desk-id"\napi_key_env = "DESK_KEY"\n'
        )
        (self.directory / ".env").write_text("DESK_KEY=dotenv-key\n", encoding="utf-8")
        self.assertEqual(
            resolve_device(device="desk", config=config),
            DeviceCredentials("dotenv-key", "desk-id"),
        )

    def test_explicit_values_override_each_named_field(self):
        self.write_config(
            '[devices.desk]\ndevice_id = "desk-id"\napi_key_env = "DESK_KEY"\n'
        )
        os.environ["DESK_KEY"] = "desk-key"
        self.assertEqual(
            resolve_device(device="desk", api_key="explicit-key"),
            DeviceCredentials("explicit-key", "desk-id"),
        )
        self.assertEqual(
            resolve_device(device="desk", device_id="explicit-id"),
            DeviceCredentials("desk-key", "explicit-id"),
        )

    def test_explicit_values_can_complete_a_named_profile(self):
        self.write_config("[devices.desk]\n")
        self.assertEqual(
            resolve_device(
                device="desk", api_key="explicit-key", device_id="explicit-id"
            ),
            DeviceCredentials("explicit-key", "explicit-id"),
        )

    def test_named_device_does_not_fall_back_to_legacy_environment(self):
        self.write_config(
            '[devices.desk]\ndevice_id = "desk-id"\napi_key_env = "DESK_KEY"\n'
        )
        os.environ.update(DOT_API_KEY="legacy-key", DOT_DEVICE_ID="legacy-id")
        with self.assertRaisesRegex(ValueError, "DESK_KEY.*missing or empty"):
            resolve_device(device="desk")
        self.write_config('[devices.desk]\napi_key_env = "DESK_KEY"\n')
        os.environ["DESK_KEY"] = "desk-key"
        with self.assertRaisesRegex(ValueError, "non-empty device_id"):
            resolve_device(device="desk")

    def test_missing_legacy_values_name_the_required_variable(self):
        with self.assertRaisesRegex(ValueError, "DOT_API_KEY"):
            resolve_device()
        os.environ["DOT_API_KEY"] = "key"
        with self.assertRaisesRegex(ValueError, "DOT_DEVICE_ID"):
            resolve_device()

    def test_empty_explicit_values_do_not_fall_back(self):
        os.environ.update(DOT_API_KEY="key", DOT_DEVICE_ID="id")
        for arguments in ({"api_key": ""}, {"device_id": ""}):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                resolve_device(**arguments)

    def test_unknown_device_and_missing_file_are_actionable(self):
        with self.assertRaisesRegex(ValueError, "Cannot read device configuration"):
            resolve_device(device="desk")
        self.write_config("[devices.desk]\n")
        with self.assertRaisesRegex(ValueError, "Unknown device 'office'"):
            resolve_device(device="office")

    def test_invalid_profile_fields_do_not_expose_values(self):
        cases = [
            ('devices = {desk = "sensitive-value"}', "must be a TOML table"),
            (
                '[devices.desk]\ndevice_id = 123\napi_key_env = "DESK_KEY"',
                "non-empty device_id",
            ),
            (
                '[devices.desk]\ndevice_id = "id"\napi_key_env = "sensitive-value"',
                "valid api_key_env",
            ),
        ]
        for content, message in cases:
            with self.subTest(content=content):
                self.write_config(content)
                with self.assertRaisesRegex(ValueError, message) as caught:
                    resolve_device(device="desk")
                self.assertNotIn("sensitive-value", str(caught.exception))

    def test_invalid_toml_diagnostic_does_not_expose_contents(self):
        self.write_config('[devices.desk]\ndevice_id = "secret-value')
        with self.assertRaisesRegex(ValueError, "Invalid TOML") as caught:
            resolve_device(device="desk")
        self.assertNotIn("secret-value", str(caught.exception))

    def test_credentials_are_frozen_and_hide_the_key_from_repr(self):
        credentials = DeviceCredentials("private-key", "id")
        self.assertNotIn("private-key", repr(credentials))
        with self.assertRaises(FrozenInstanceError):
            credentials.device_id = "other"


if __name__ == "__main__":
    unittest.main()
