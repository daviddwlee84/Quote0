import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from quote0.cli import main
from quote0.models import ApiResponse, CanvasApiRequest, DeviceInfo
from quote0.config import load_config
from quote0.apps.quota import ProviderQuota, QuotaWindow

CARD = {
    "refreshNow": False,
    "taskKey": "existing",
    "taskAlias": None,
    "windowData": {"default": [{"type": "span", "props": {"children": "Hello"}}]},
}


class ManagementCliTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        cwd = Path.cwd()
        os.chdir(self.folder)
        self.addCleanup(os.chdir, cwd)
        environment = patch.dict(
            os.environ, {"DOT_API_KEY": "key", "DOT_DEVICE_ID": "id"}, clear=True
        )
        environment.start()
        self.addCleanup(environment.stop)
        for name in ("DotClient", "Quote0"):
            mock = patch("quote0.cli." + name)
            setattr(self, name, mock.start())
            self.addCleanup(mock.stop)
        self.client = self.Quote0.return_value
        for method in (
            "send_text",
            "send_image",
            "send_canvas",
            "update_settings",
            "next_content",
        ):
            getattr(self.client, method).return_value = ApiResponse(
                success=True, message="Done"
            )
        self.DotClient.return_value.list_devices.return_value = ApiResponse(
            success=True,
            message="OK",
            response=[DeviceInfo(id="A", alias="My Desk"), DeviceInfo(id="B")],
        )

    def invoke(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                main(list(args))
                code = 0
            except SystemExit as exc:
                code = exc.code
        return code, stdout.getvalue(), stderr.getvalue()

    def file(self, name, data):
        path = self.folder / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return str(path)

    def test_discovery_json_and_table(self):
        code, out, err = self.invoke("devices", "list", "--json")
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)[0]["id"], "A")
        self.Quote0.assert_not_called()
        self.assertIn("My Desk", self.invoke("devices", "list")[1])

    def test_queries_and_content_switch(self):
        self.client.list_tasks.return_value = ApiResponse(
            success=True,
            message="OK",
            response=[
                {"key": "canvas-slot", "type": "CANVAS_API", "taskAlias": "Quota"}
            ],
        )
        code, out, _ = self.invoke("devices", "tasks", "--task-type", "fixed")
        self.assertEqual(code, 0)
        self.assertIn("canvas-slot", out)
        self.client.list_tasks.assert_called_once_with("fixed")
        self.assertEqual(self.invoke("devices", "next")[0], 0)
        self.client.next_content.assert_called_once()
        self.client.get_status.return_value = ApiResponse(
            success=True, response={"deviceId": "id"}, message="OK"
        )
        self.assertEqual(
            json.loads(self.invoke("devices", "status", "--json")[1]),
            {"deviceId": "id"},
        )

    def test_remote_failure_never_prints_fake_json_success(self):
        self.DotClient.return_value.list_devices.return_value = ApiResponse(
            success=False, message="Unauthorized", status_code=401
        )
        code, out, err = self.invoke("devices", "list", "--json")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("Unauthorized", err)

    def test_init_noninteractive_and_no_secrets(self):
        code, _, err = self.invoke(
            "config", "init", "--bind", "desk=A", "side=B", "--default-device", "desk"
        )
        self.assertEqual(code, 0, err)
        config = load_config(Path("quote0.toml"))
        self.assertEqual(
            config["devices"]["desk"], {"device_id": "A", "account": "personal"}
        )
        self.assertEqual(config["accounts"]["personal"], {"api_key_env": "DOT_API_KEY"})
        self.assertNotIn("api_key =", Path("quote0.toml").read_text())

    def test_init_interactive_selects_and_names_device(self):
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("builtins.input", side_effect=["1", "desk"]),
        ):
            code, _, err = self.invoke("config", "init")
        self.assertEqual(code, 0, err)
        self.assertEqual(load_config(Path("quote0.toml"))["defaults"]["device"], "desk")

    def test_init_cancel_and_failed_discovery_write_nothing(self):
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("builtins.input", return_value=""),
        ):
            self.assertEqual(self.invoke("config", "init")[0], 1)
        self.assertFalse(Path("quote0.toml").exists())
        self.DotClient.return_value.list_devices.return_value = ApiResponse(
            success=False, message="Timeout"
        )
        self.assertEqual(self.invoke("config", "init", "--bind", "desk=A")[0], 1)
        self.assertFalse(Path("quote0.toml").exists())

    def test_init_invalid_selection_never_writes(self):
        for args in (("desk=unknown",), ("desk=A", "desk=B"), ("desk=A", "side=B")):
            code, _, _ = self.invoke("config", "init", "--bind", *args)
            self.assertEqual(code, 1)
            self.assertFalse(Path("quote0.toml").exists())
        with patch("sys.stdin.isatty", return_value=False):
            self.assertEqual(self.invoke("config", "init")[0], 1)

    def test_init_existing_file_protected_and_force(self):
        Path("quote0.toml").write_text("original")
        self.assertEqual(self.invoke("config", "init", "--bind", "desk=A")[0], 1)
        self.assertEqual(Path("quote0.toml").read_text(), "original")
        self.DotClient.assert_not_called()
        self.assertEqual(
            self.invoke("config", "init", "--bind", "desk=A", "--force")[0], 0
        )
        self.assertEqual(
            load_config(Path("quote0.toml"))["devices"]["desk"]["device_id"], "A"
        )

    def test_text_styles_remote_icon_and_task_flags(self):
        style = self.file("styles.json", {"message": {"fontSize": 16}})
        code, _, err = self.invoke(
            "text",
            "--message",
            "Hi",
            "--styles-file",
            style,
            "--icon-url",
            "https://example.com/icon.png",
            "--task-key",
            "slot",
            "--task-alias",
            "",
        )
        self.assertEqual(code, 0, err)
        args = self.client.send_text.call_args.kwargs
        self.assertEqual(args["icon"], "https://example.com/icon.png")
        self.assertEqual(args["styles"].message.fontSize, 16)
        self.assertEqual(args["task_alias"], "")
        self.assertEqual(args["task_key"], "slot")

    def test_image_url_and_conflicting_sources(self):
        self.assertEqual(
            self.invoke("image", "--url", "https://example.com/a.png")[0], 0
        )
        self.assertEqual(
            self.client.send_image.call_args.kwargs["image_base64"],
            "https://example.com/a.png",
        )
        self.client.send_image.reset_mock()
        for args in (
            ("--url", "file:///a"),
            ("--url", "https://example.com/a.png", "--base64", "x"),
        ):
            self.assertEqual(self.invoke("image", *args)[0], 1)
        self.client.send_image.assert_not_called()

    def test_canvas_validation_is_offline_and_preserves_task_metadata_on_send(self):
        file = self.file("card.json", CARD)
        code, _, err = self.invoke(
            "canvas", "--file", file, "--validate-only", "--device", "missing"
        )
        self.assertEqual(code, 0, err)
        self.Quote0.assert_not_called()
        self.assertEqual(self.invoke("canvas", "--file", file)[0], 0)
        options = self.client.send_canvas.call_args.kwargs
        self.assertFalse(options["refresh_now"])
        self.assertEqual(options["task_key"], "existing")
        self.assertIsNone(options["task_alias"])
        self.assertEqual(
            self.invoke(
                "canvas",
                "--file",
                file,
                "--task-key",
                "override",
                "--task-alias",
                "New",
            )[0],
            0,
        )
        self.assertEqual(
            self.client.send_canvas.call_args.kwargs["task_key"], "override"
        )

    def test_invalid_canvas_and_settings_never_resolve_device(self):
        file = self.file(
            "bad.json", {"windowData": {"default": [{"type": "script", "props": {}}]}}
        )
        self.assertEqual(self.invoke("canvas", "--file", file)[0], 1)
        self.Quote0.assert_not_called()
        file = self.file("settings.json", {"interval": {"powerMs": 1000}})
        self.assertEqual(
            self.invoke("devices", "settings", "update", "--file", file)[0], 1
        )
        self.Quote0.assert_not_called()

    def test_settings_update_omission_and_clear(self):
        file = self.file(
            "settings.json",
            {
                "alias": None,
                "sleep": {"enabled": False, "start": "23:00", "end": "07:00"},
            },
        )
        self.assertEqual(
            self.invoke("devices", "settings", "update", "--file", file)[0], 0
        )
        request = self.client.update_settings.call_args.args[0]
        self.assertEqual(
            request.model_dump(exclude_unset=True), json.loads(Path(file).read_text())
        )

    def test_canvas_quota_export_needs_no_device_and_roundtrips(self):
        quota = ProviderQuota("codex", (QuotaWindow("primary", "5h", 0),))
        with patch("quote0.apps.quota.fetch_quotas", return_value=[quota]) as fetch:
            code, _, err = self.invoke(
                "apps",
                "quota",
                "--providers",
                "codex",
                "--renderer",
                "canvas",
                "--device",
                "missing",
                "--output",
                "quota.json",
            )
        self.assertEqual(code, 0, err)
        self.Quote0.assert_not_called()
        self.DotClient.assert_not_called()
        fetch.assert_called_once_with(["codex"], timeout=120)
        payload = json.loads(Path("quota.json").read_text())
        CanvasApiRequest.model_validate(payload)
        self.assertEqual(payload["data"]["providers"][0]["windows"][0]["percent"], "0%")
        self.assertEqual(self.invoke("canvas", "--file", "quota.json")[0], 0)

    def test_card_style_export_and_image_mismatch(self):
        quotas = [
            ProviderQuota(name, (QuotaWindow("primary", "5h", 75),))
            for name in ("codex", "claude", "gemini")
        ]
        with patch("quote0.apps.quota.fetch_quotas", return_value=quotas) as fetch:
            code, _, err = self.invoke(
                "apps",
                "quota",
                "--providers",
                "codex",
                "claude",
                "gemini",
                "--renderer",
                "canvas",
                "--canvas-style",
                "cards",
                "--output",
                "cards.json",
            )
            self.assertEqual(code, 0, err)
            payload = json.loads(Path("cards.json").read_text())
            self.assertEqual(payload["data"]["serviceCount"], "3 SERVICES")
            self.Quote0.assert_not_called()
            fetch.reset_mock()
            self.assertEqual(
                self.invoke(
                    "apps", "quota", "--providers", "codex", "--canvas-style", "cards"
                )[0],
                1,
            )
            fetch.assert_not_called()

    def test_card_theme_export_delivery_and_invalid_modes(self):
        quotas = [ProviderQuota("codex", (QuotaWindow("primary", "5h", 75),))]
        with patch("quote0.apps.quota.fetch_quotas", return_value=quotas) as fetch:
            code, _, err = self.invoke(
                "apps",
                "quota",
                "--providers",
                "codex",
                "--renderer",
                "canvas",
                "--canvas-style",
                "cards",
                "--card-theme",
                "dark",
                "--output",
                "dark.json",
            )
            self.assertEqual(code, 0, err)
            payload = json.loads(Path("dark.json").read_text())
            self.assertEqual(payload["border"], 1)
            self.Quote0.assert_not_called()
            self.assertEqual(
                self.invoke(
                    "apps",
                    "quota",
                    "--providers",
                    "codex",
                    "--renderer",
                    "canvas",
                    "--canvas-style",
                    "cards",
                    "--card-theme",
                    "dark",
                )[0],
                0,
            )
            self.assertEqual(self.client.send_canvas.call_args.kwargs["border"], 1)
            fetch.reset_mock()
            for extra in ([], ["--renderer", "canvas"]):
                self.assertEqual(
                    self.invoke(
                        "apps",
                        "quota",
                        "--providers",
                        "codex",
                        "--card-theme",
                        "light",
                        *extra,
                    )[0],
                    1,
                )
            fetch.assert_not_called()

    def test_pace_and_focus_are_independent_and_exports_fetch_once(self):
        quota = ProviderQuota(
            "codex",
            (
                QuotaWindow("primary", "5h", 100, window_minutes=300),
                QuotaWindow("secondary", "7d", 54, window_minutes=10080),
            ),
        )
        for renderer in ("image", "canvas"):
            for show in (False, True):
                for focus in ("primary", "long"):
                    with self.subTest(renderer=renderer, pace=show, focus=focus):
                        name = "pace.json" if renderer == "canvas" else "pace.png"
                        with patch(
                            "quote0.apps.quota.fetch_quotas", return_value=[quota]
                        ) as fetch:
                            code, _, err = self.invoke(
                                "apps",
                                "quota",
                                "--providers",
                                "codex",
                                "--renderer",
                                renderer,
                                "--pace" if show else "--no-pace",
                                "--quota-focus",
                                focus,
                                "--device",
                                "not-configured",
                                "--output",
                                name,
                            )
                        self.assertEqual(code, 0, err)
                        fetch.assert_called_once_with(["codex"], timeout=120)
                        self.Quote0.assert_not_called()
                        if renderer == "canvas":
                            data = json.loads(Path(name).read_text())["data"][
                                "providers"
                            ][0]
                            self.assertEqual("pace" in data, show)
                            self.assertEqual(
                                data["windows"][0]["slot"],
                                "secondary" if focus == "long" else "primary",
                            )
        with patch("quote0.apps.quota.fetch_quotas") as fetch:
            self.assertNotEqual(
                self.invoke(
                    "apps", "quota", "--providers", "codex", "--quota-focus", "unknown"
                )[0],
                0,
            )
            fetch.assert_not_called()

    def test_canvas_quota_delivery_and_failed_export_exit(self):
        quota = ProviderQuota("codex", error="Unavailable")
        with patch("quote0.apps.quota.fetch_quotas", return_value=[quota]):
            code, _, _ = self.invoke(
                "apps",
                "quota",
                "--providers",
                "codex",
                "--renderer",
                "canvas",
                "--no-refresh",
                "--task-key",
                "canvas-slot",
            )
            self.assertEqual(code, 1)
            self.client.send_canvas.assert_called_once()
            self.assertFalse(self.client.send_canvas.call_args.kwargs["refresh_now"])
            self.assertEqual(
                self.client.send_canvas.call_args.kwargs["task_key"], "canvas-slot"
            )
            self.client.send_image.assert_not_called()
            code, _, _ = self.invoke(
                "apps",
                "quota",
                "--providers",
                "codex",
                "--renderer",
                "canvas",
                "--output",
                "failed.json",
            )
            self.assertEqual(code, 1)
            self.assertTrue(Path("failed.json").exists())
        with patch("quote0.apps.quota.fetch_quotas") as fetch:
            self.assertEqual(
                self.invoke(
                    "apps",
                    "quota",
                    "--providers",
                    "codex",
                    "--renderer",
                    "canvas",
                    "--output",
                    "bad.png",
                )[0],
                1,
            )
            fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
