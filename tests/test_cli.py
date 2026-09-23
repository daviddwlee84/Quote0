import base64
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from quote0.cli import main
from quote0.models import ApiResponse, BorderColor


class CliTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        original_directory = Path.cwd()
        os.chdir(self.directory)
        self.addCleanup(os.chdir, original_directory)
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        client = patch("quote0.cli.Quote0")
        self.client_class = client.start()
        self.addCleanup(client.stop)
        self.client = self.client_class.return_value
        success = ApiResponse(success=True, message="Sent")
        self.client.send_text.return_value = success
        self.client.send_image.return_value = success

    def invoke(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                main(list(args))
                code = 0
            except SystemExit as exc:
                code = exc.code
        return code, stdout.getvalue(), stderr.getvalue()

    def quota_mocks(self, error=None):
        fetch = patch(
            "quote0.apps.quota.fetch_quotas",
            return_value=[SimpleNamespace(provider="codex", error=error)],
        )
        render = patch(
            "quote0.apps.quota.render_quota",
            return_value=Image.new("1", (296, 152), 1),
        )
        fetch_mock = fetch.start()
        render.start()
        self.addCleanup(fetch.stop)
        self.addCleanup(render.stop)
        return fetch_mock

    def test_legacy_explicit_text_flags(self):
        code, _, _ = self.invoke(
            "text",
            "--api-key",
            "key",
            "--device-id",
            "id",
            "--title",
            "Hello",
            "--message",
            "World",
            "--no-refresh",
        )
        self.assertEqual(code, 0)
        self.client_class.assert_called_once_with("key", "id")
        self.assertEqual(self.client.send_text.call_args.kwargs["message"], "World")
        self.assertFalse(self.client.send_text.call_args.kwargs["refresh_now"])

    def test_legacy_env_image_preset(self):
        os.environ.update(DOT_API_KEY="key", DOT_DEVICE_ID="id")
        code, _, _ = self.invoke("image", "--preset", "ALL_BLACK", "--border", "BLACK")
        self.assertEqual(code, 0)
        self.client_class.assert_called_once_with("key", "id")
        payload = self.client.send_image.call_args.kwargs
        self.assertEqual(payload["border"], BorderColor.BLACK)
        with Image.open(io.BytesIO(base64.b64decode(payload["image_base64"]))) as image:
            self.assertEqual(image.size, (296, 152))

    def test_console_entrypoint_loads_dotenv_after_import(self):
        (self.directory / ".env").write_text(
            "DOT_API_KEY=dotenv-key\nDOT_DEVICE_ID=dotenv-id\n", encoding="utf-8"
        )
        code, _, _ = self.invoke("text", "--message", "Hello")
        self.assertEqual(code, 0)
        self.client_class.assert_called_once_with("dotenv-key", "dotenv-id")

    def test_named_devices_and_config_path(self):
        config = self.directory / "devices.toml"
        config.write_text(
            '[devices.desk]\ndevice_id="a"\napi_key_env="DESK_KEY"\n'
            '[devices.side]\ndevice_id="b"\napi_key_env="SIDE_KEY"\n',
            encoding="utf-8",
        )
        os.environ.update(DESK_KEY="key-a", SIDE_KEY="key-b", DOT_DEVICE_ID="unrelated")
        for name, key, device_id in [("desk", "key-a", "a"), ("side", "key-b", "b")]:
            with self.subTest(device=name):
                code, _, _ = self.invoke(
                    "text", "--device", name, "--config", str(config), "--message", "Hi"
                )
                self.assertEqual(code, 0)
                self.client_class.assert_called_with(key, device_id)

    def test_invalid_image_sources_do_not_send(self):
        os.environ.update(DOT_API_KEY="key", DOT_DEVICE_ID="id")
        code, _, _ = self.invoke("image", "--preset", "ALL_BLACK", "--base64", "other")
        self.assertEqual(code, 1)
        self.client.send_image.assert_not_called()

    def test_quota_preview_needs_no_device_or_credentials(self):
        fetch = self.quota_mocks()
        target = self.directory / "quota.png"
        code, _, _ = self.invoke(
            "apps",
            "quota",
            "--providers",
            "codex",
            "claude",
            "--device",
            "not-configured",
            "--output",
            str(target),
        )
        self.assertEqual(code, 0)
        self.client_class.assert_not_called()
        fetch.assert_called_once_with(["codex", "claude"], timeout=120)
        with Image.open(target) as image:
            self.assertEqual(image.size, (296, 152))
            self.assertEqual(image.format, "PNG")

    def test_quota_custom_timeout_is_forwarded(self):
        fetch = self.quota_mocks()
        code, _, _ = self.invoke(
            "apps",
            "quota",
            "--providers",
            "claude",
            "--timeout",
            "180",
            "--output",
            str(self.directory / "quota.png"),
        )
        self.assertEqual(code, 0)
        fetch.assert_called_once_with(["claude"], timeout=180)

    def test_quota_delivery_encodes_rendered_png(self):
        self.quota_mocks()
        os.environ.update(DOT_API_KEY="key", DOT_DEVICE_ID="id")
        code, _, _ = self.invoke(
            "apps", "quota", "--providers", "codex", "--no-refresh"
        )
        self.assertEqual(code, 0)
        payload = self.client.send_image.call_args.kwargs
        self.assertEqual(payload["dither_type"], "NONE")
        self.assertEqual(payload["border"], BorderColor.WHITE)
        self.assertFalse(payload["refresh_now"])
        with Image.open(io.BytesIO(base64.b64decode(payload["image_base64"]))) as image:
            self.assertEqual(image.size, (296, 152))

    def test_quota_provider_failure_still_delivers_and_exits_nonzero(self):
        self.quota_mocks(error="Fetch timed out")
        os.environ.update(DOT_API_KEY="key", DOT_DEVICE_ID="id")
        code, _, stderr = self.invoke("apps", "quota", "--providers", "codex")
        self.assertEqual(code, 1)
        self.client.send_image.assert_called_once()
        self.assertIn("codex: Fetch timed out", stderr)

    def test_failed_quota_preview_is_written_with_nonzero_exit(self):
        self.quota_mocks(error="Unavailable")
        target = self.directory / "quota.png"
        code, _, _ = self.invoke(
            "apps", "quota", "--providers", "codex", "--output", str(target)
        )
        self.assertEqual(code, 1)
        self.assertTrue(target.is_file())
        self.client_class.assert_not_called()

    def test_invalid_device_fails_before_quota_fetch(self):
        fetch = self.quota_mocks()
        code, _, _ = self.invoke(
            "apps", "quota", "--providers", "codex", "--device", "missing"
        )
        self.assertEqual(code, 1)
        fetch.assert_not_called()
        self.client_class.assert_not_called()

    def test_invalid_provider_selection_fails_before_fetch(self):
        fetch = self.quota_mocks()
        for providers in [["codex", "codex"], ["a", "b", "c", "d", "e", "f", "g"]]:
            with self.subTest(providers=providers):
                code, _, _ = self.invoke(
                    "apps", "quota", "--providers", *providers, "--output", "quota.png"
                )
                self.assertEqual(code, 1)
        fetch.assert_not_called()
        self.client_class.assert_not_called()

    def test_providers_are_required(self):
        code, _, _ = self.invoke("apps", "quota", "--output", "quota.png")
        self.assertEqual(code, 2)
        self.client_class.assert_not_called()

    def test_delivery_failure_returns_nonzero(self):
        self.quota_mocks()
        os.environ.update(DOT_API_KEY="key", DOT_DEVICE_ID="id")
        self.client.send_image.return_value = ApiResponse(
            success=False, message="Timed out"
        )
        code, _, stderr = self.invoke("apps", "quota", "--providers", "codex")
        self.assertEqual(code, 1)
        self.assertIn("Timed out", stderr)

    def test_generic_import_and_help_do_not_load_quota_or_need_codexbar(self):
        source = Path(__file__).resolve().parents[1] / "src"
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; import quote0; from quote0.cli import main; "
                "assert 'quote0.apps.quota' not in sys.modules; main(['--help'])",
            ],
            env={"PATH": "", "PYTHONPATH": str(source)},
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("apps", result.stdout)


if __name__ == "__main__":
    unittest.main()
