import os
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

from quote0.config import (
    DeviceCredentials,
    load_config,
    make_config,
    resolve_account,
    resolve_device,
    write_config,
)


class ResolveDeviceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        original = Path.cwd()
        os.chdir(self.directory)
        self.addCleanup(os.chdir, original)
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        self.config = self.directory / "quote0.toml"

    def configured(self):
        settings = make_config(
            "personal", "DESK_KEY", ["desk=desk-id", "side=side-id"], "desk"
        )
        settings["accounts"]["office"] = {"api_key_env": "OFFICE_KEY"}
        settings["devices"]["work"] = {"account": "office", "device_id": "work-id"}
        write_config(self.config, settings)
        os.environ.update(
            DESK_KEY="desk-key",
            OFFICE_KEY="office-key",
            DOT_API_KEY="unrelated-key",
            DOT_DEVICE_ID="unrelated-id",
        )
        return settings

    def test_named_default_and_cross_account_devices(self):
        self.configured()
        self.assertEqual(resolve_device(), DeviceCredentials("desk-key", "desk-id"))
        self.assertEqual(
            resolve_device(device="side"), DeviceCredentials("desk-key", "side-id")
        )
        self.assertEqual(
            resolve_device(device="work"), DeviceCredentials("office-key", "work-id")
        )
        self.assertEqual(resolve_account(), "desk-key")
        self.assertEqual(resolve_account(account="office"), "office-key")

    def test_explicit_named_overrides(self):
        self.configured()
        self.assertEqual(
            resolve_device(device="desk", api_key="explicit"),
            DeviceCredentials("explicit", "desk-id"),
        )
        self.assertEqual(
            resolve_device(device="desk", device_id="explicit"),
            DeviceCredentials("desk-key", "explicit"),
        )

    def test_direct_flags_do_not_borrow_default_credentials(self):
        self.configured()
        self.assertEqual(
            resolve_device(api_key="direct"),
            DeviceCredentials("direct", "unrelated-id"),
        )
        self.assertEqual(
            resolve_device(device_id="direct"),
            DeviceCredentials("unrelated-key", "direct"),
        )
        del os.environ["DOT_DEVICE_ID"]
        with self.assertRaisesRegex(ValueError, "DOT_DEVICE_ID"):
            resolve_device(api_key="direct")
        self.config.write_text("invalid TOML")
        self.assertEqual(
            resolve_device(api_key="k", device_id="i"), DeviceCredentials("k", "i")
        )

    def test_named_missing_key_never_falls_back(self):
        self.configured()
        del os.environ["DESK_KEY"]
        with self.assertRaisesRegex(ValueError, "DESK_KEY.*missing or empty"):
            resolve_device(device="desk")
        with self.assertRaisesRegex(ValueError, "DESK_KEY"):
            resolve_device()

    def test_direct_environment_without_config_or_default(self):
        os.environ.update(DOT_API_KEY="key", DOT_DEVICE_ID="id")
        self.assertEqual(resolve_device(), DeviceCredentials("key", "id"))
        self.config.write_text('[accounts.personal]\napi_key_env="OTHER_KEY"\n')
        self.assertEqual(resolve_device(), DeviceCredentials("key", "id"))
        self.assertEqual(resolve_account(), "key")

    def test_dotenv_relative_to_cwd_and_exported_values_win(self):
        (self.directory / ".env").write_text(
            "DOT_API_KEY=dotenv\nDOT_DEVICE_ID=id\nDESK_KEY=desk\n"
        )
        os.environ["DOT_API_KEY"] = "exported"
        self.assertEqual(resolve_device(), DeviceCredentials("exported", "id"))
        elsewhere = self.directory / "other"
        elsewhere.mkdir()
        path = elsewhere / "devices.toml"
        write_config(path, make_config("personal", "DESK_KEY", ["desk=did"], "desk"))
        self.assertEqual(
            resolve_device(device="desk", config=path), DeviceCredentials("desk", "did")
        )

    def test_unknown_names_and_invalid_references(self):
        settings = self.configured()
        for call in (
            lambda: resolve_device(device="unknown"),
            lambda: resolve_account(account="unknown"),
        ):
            with self.assertRaisesRegex(ValueError, "Unknown"):
                call()
        settings["defaults"]["device"] = "unknown"
        with self.assertRaisesRegex(ValueError, "default device"):
            write_config(self.config, settings, force=True)
        self.assertEqual(load_config(self.config)["defaults"]["device"], "desk")
        settings["defaults"]["device"] = "desk"
        settings["devices"]["desk"]["account"] = "unknown"
        with self.assertRaisesRegex(ValueError, "unknown account"):
            write_config(self.config, settings, force=True)

    def test_bad_config_does_not_fall_back_or_echo_contents(self):
        os.environ.update(DOT_API_KEY="key", DOT_DEVICE_ID="id")
        for content in (
            '[devices.desk]\ndevice_id="secret-value',
            '[accounts.personal]\napi_key_env="secret-value"',
        ):
            self.config.write_text(content)
            with self.assertRaises(ValueError) as error:
                resolve_device()
            self.assertNotIn("secret-value", str(error.exception))

    def test_old_format_rejected(self):
        self.config.write_text(
            '[devices.desk]\ndevice_id="id"\napi_key_env="DOT_API_KEY"\n'
        )
        with self.assertRaisesRegex(ValueError, "Old device config"):
            resolve_device(device="desk")

    def test_missing_config_and_empty_explicit_credentials(self):
        with self.assertRaisesRegex(ValueError, "Cannot read device configuration"):
            resolve_device(device="desk")
        with self.assertRaisesRegex(ValueError, "DOT_API_KEY"):
            resolve_device()
        os.environ.update(DOT_API_KEY="key", DOT_DEVICE_ID="id")
        for args in ({"api_key": ""}, {"device_id": ""}):
            with self.assertRaises(ValueError):
                resolve_device(**args)

    def test_bindings_and_roundtrip(self):
        settings = make_config(
            "personal", "MY_KEY", ['desk=ID"\\quote', "side=B"], "desk"
        )
        write_config(self.config, settings)
        self.assertEqual(load_config(self.config), settings)
        self.assertNotIn("private-key", self.config.read_text())
        for bindings in (
            [],
            ["desk=A", "desk=B"],
            ["desk=A", "side=A"],
            ["bad name=A"],
            ["desk="],
            ["desk"],
        ):
            with self.subTest(bindings=bindings), self.assertRaises(ValueError):
                make_config("personal", "MY_KEY", bindings, "desk")

    def test_atomic_publish_and_force(self):
        settings = make_config("personal", "MY_KEY", ["desk=A"], "desk")
        self.config.write_text("keep me")
        with self.assertRaisesRegex(ValueError, "already exists"):
            write_config(self.config, settings)
        self.assertEqual(self.config.read_text(), "keep me")
        self.assertEqual(list(self.directory.glob(".quote0-*")), [])
        write_config(self.config, settings, force=True)
        self.assertEqual(load_config(self.config), settings)

    def test_credentials_are_frozen_and_hide_key(self):
        credentials = DeviceCredentials("private-key", "id")
        self.assertNotIn("private-key", repr(credentials))
        with self.assertRaises(FrozenInstanceError):
            credentials.device_id = "other"


if __name__ == "__main__":
    unittest.main()
