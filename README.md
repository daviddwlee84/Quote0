# Quote/0

A Quote/0 Client + Streamlit App and Notes about SSPAI's Quote/0

> Original tested firmware: 1.6.10 (not a claim about the latest release).

## Getting Started

1. Connect Type-C
2. Bind device in Mobile App
3. Select content to show
4. (optional) Request an API key in the App, then discover devices with `quote0 devices list`.
5. (optional) Setup `.env` (follow [`.env.example`](./.env.example))

- [Update Software](https://dot.mindreset.tech/tool/update)
  - update firmware
  - reset network
  - reset device

NOTE: to test if the display is normal you can use the script [checkerboard_gray.sh](scripts/image_api_test/checkerboard_gray.sh)

### CLI

- [quote0 · PyPI](https://pypi.org/project/quote0/)

```bash
# Install this package
$ uv tool install quote0

# Image API
# NOTE: the CHECKERBOARD_GRAY pattern is good to test if your monitor is defect
$ quote0 image --preset CHECKERBOARD_GRAY --api-key dot_app_.... --device-id ABCD1234ABCD
✅ Device ABCD1234ABCD Image API content switched.

# Text API with Environment Variable
export DOT_API_KEY=dot_app_....
export DOT_DEVICE_ID=ABCD1234ABCD

$ quote0 text --title Hello --message World
✅ Device ABCD1234ABCD text API content switched.
```

The CLI also loads `.env` from the current working directory when resolving a
device. Exported environment variables take precedence over `.env`; explicit
`--api-key` and `--device-id` flags take precedence over both.

The client uses the `/api/authV2/open` endpoints, with
the device ID in the URL and Bearer authentication. Success and error messages
come from the server; the HTTP status determines the result. If a request returns
404, verify the device ID and that the matching Image API, Text API or Canvas API content
has been added to the device's Loop in the Dot. App. See the
[API reference](docs/Quote0_API_Schema.md).

#### Accounts and devices

Discover devices and generate [quote0.toml](quote0.example.toml), without copying
serial numbers out of the app:

```bash
# DOT_API_KEY is already exported or stored in cwd/.env
quote0 devices list
quote0 config init

# Non-interactive initialization (IDs come from devices list)
quote0 config init --account personal --api-key-env DOT_API_KEY \
  --bind desk=DEVICE_A side=DEVICE_B --default-device desk
```

The interactive initializer lists devices, asks which to include and how to name
them, and lets you choose a default. No credentials are written to TOML. An existing
file is protected unless `--force` is supplied; cancellation or failed discovery
writes nothing. Use `--config /path/to/quote0.toml` for another destination.

```toml
[defaults]
account = "personal"
device = "desk"

[accounts.personal]
api_key_env = "DOT_API_KEY"

[devices.desk]
account = "personal"
device_id = "DEVICE_A"

[devices.side]
account = "personal"
device_id = "DEVICE_B"
```

An account may control multiple devices. For another account, add a separate
`[accounts.NAME]` with its environment variable and reference it from that device.
Remote aliases are display labels; the local names bind to fixed device IDs.
The old per-device `api_key_env` format is no longer supported: regenerate the
file or move those references into accounts.

```bash
quote0 devices list --account personal --json
quote0 text --device desk --message Hello
quote0 image --device side --file image.png
quote0 text --message Hello  # defaults.device when no explicit credentials
```

Device selection is explicit `--device`, explicit credential flags, configured
`defaults.device`, then the `DOT_API_KEY`/`DOT_DEVICE_ID` environment pair.
A named device uses its own account; explicit `--api-key`/`--device-id` may override
its fields. Without `--device`, supplying either credential flag selects direct
mode: only flags and `DOT_*` are used, and TOML is not read. Missing or invalid
named credentials fail instead of falling back to another account.

Account queries use `--api-key`, then `--account` or `defaults.account`, then
`DOT_API_KEY`. The default account does not override a selected device's account.
`.env` is always relative to the working directory, even with `--config` elsewhere;
exported environment variables take precedence over `.env`.

```python
from quote0 import DotClient, Quote0
from quote0.config import resolve_account, resolve_device

result = DotClient(resolve_account()).list_devices()
if result.success:
    for device in result.response:
        print(device.alias, device.id)

target = resolve_device(device="desk")
client = Quote0(target.api_key, target.device_id)
client.send_text(message="Hello", task_key="TEXT_TASK_KEY")
```

#### Content selection and management

```bash
quote0 devices status --device desk
quote0 devices tasks --device desk --task-type loop
quote0 devices next --device desk
quote0 text --device desk --task-key TEXT_TASK_KEY --task-alias Reminders \
  --message Hello --styles-file styles.json --icon-url https://example.com/icon.png
quote0 image --device desk --url https://example.com/image.png
```

Task listing also supports `--task-type fixed`. Query commands support `--json` for
response data without progress messages. Use the task `key` as `--task-key` when a
device has multiple contents of one API type; omission leaves selection to the
server (the first matching item). Omit `--task-alias` to preserve the name, or pass
`--task-alias ""` to clear it. Python also supports explicit `task_alias=None` to clear.

The public OpenAPI currently does not expose task creation/deletion, ordering or
enable/disable controls; use Dot App for those operations. `--no-refresh` saves
content without immediately switching the display; it does not disable the task.

A Text styles file contains, for example:

```json
{"message": {"fontFamily": "FusionPixel12", "fontSize": 12, "lineHeight": 1.25}}
```

Text icons and Image content accept PNG Base64/data URIs or public image URLs.
`--icon-file` and `--icon-url` are mutually exclusive; Image requires exactly one of
`--file`, `--preset`, `--base64`, `--url`. The server must be able to access remote
images anonymously; local validation does not fetch or verify remote image content.

#### Canvas

Add **Canvas API** content to the device's **Loop** in Dot App Content Studio first.
Save a request JSON, for example [canvas_card.json](examples/canvas_card.json):

```bash
quote0 canvas --file examples/canvas_card.json --validate-only
quote0 canvas --device desk --task-key CANVAS_TASK_KEY --file examples/canvas_card.json
```

JSON contains `windowData` and optionally `data`, `layoutFull`, `border`, `link`,
`refreshNow`, `taskKey`, and `taskAlias`. Explicit task flags override the file;
`--no-refresh` forces `refreshNow=false`, otherwise the file's setting is preserved.
`--validate-only` needs no device or API credentials. It checks structure, reserved
keys and documented size limits, not final rendering or remote image availability.
Canvas is a static element/template format, not a browser or arbitrary JavaScript.

```python
client.send_canvas(
    {"default": [{"type": "span", "props": {"children": "Hello Canvas"}}]},
    task_key="CANVAS_TASK_KEY",
)
```

#### Device settings

```bash
quote0 devices settings get --device desk --json
quote0 timezones list
quote0 devices settings update --device desk --file settings.json
```

A settings update is a partial object:

```json
{
  "alias": "Desk",
  "timezone": "Asia/Shanghai",
  "interval": {"powerMs": 300000, "batteryMs": 1800000},
  "sleep": {"enabled": true, "start": "23:00", "end": "07:00"}
}
```

Omitted fields remain unchanged; `alias`/`location` can be cleared with `null` or
an empty string. Intervals must be whole-minute multiples from 60,000 through
43,200,000 ms. Sleep needs all three fields and allows crossing midnight, but its
start and end cannot match. Timezone changes are checked against the live supported
list. These settings control device wake/refresh; scripts still schedule fetching
and uploading new quota data. Writes are sent once without automatic retries.

#### Apps: agent quota

`apps` groups applications built on the generic client. The first application
renders [CodexBar](https://github.com/steipete/CodexBar) quotas as a 296×152
monochrome PNG or native Canvas card. Install `codexbar` on `PATH` and configure its provider access
first. The integration targets the
[CodexBar 0.56.3 JSON format](https://github.com/steipete/CodexBar/blob/v0.56.3/docs/cli.md).
The generic library and content/device commands do not require CodexBar.

```bash
# Show the selected services on one device
quote0 apps quota --providers codex claude --device desk

# Preview only: no Quote/0 credentials or device configuration required
quote0 apps quota --providers codex claude --output quota.png

# The image can also be delivered through the generic CLI
quote0 image --device desk --file quota.png
```

`--providers` requires 1–6 distinct CodexBar provider IDs in display order.
Each uses CodexBar's current account; these are account-level quotas, not
per-running-agent budgets. Providers, content assignments, and refresh intervals
belong in commands or user scripts, not device configuration. `--output` always
exports instead of sending, even if delivery options are also supplied.
The default `--renderer image` writes PNG; `--renderer canvas` writes a `.json`
Canvas request. Neither export resolves a device or contacts Dot APIs.


```bash
# Native Canvas; explicitly select its content task when needed
quote0 apps quota --providers codex claude --device desk \
  --renderer canvas --task-key CANVAS_TASK_KEY

# Export and validate without a Dot device or credentials
quote0 apps quota --providers codex claude --renderer canvas --output quota.json
quote0 canvas --file quota.json --validate-only

# Fetch once, then export both versions using one snapshot and reference time
uv run python examples/quota_compare.py --providers codex claude --output-dir /tmp/quota-compare
```

Canvas uses the same provider ordering, remaining amounts, request counts, reset
timing and source timestamp as Image. JSON export is not a visual preview: compare
it on hardware after adding Canvas content. A successful API response does not
prove the device has displayed it, especially while running on battery and asleep.

| Services | Automatic layout |
| --- | --- |
| 1 | Up to three windows, remaining percentages, reset countdowns, and bars |
| 2–3 | Two windows per service, with remaining percentages and reset countdowns |
| 4–6 | One row per service, with two remaining percentages |

Window labels use the reported duration, or `P` / `S` / `T` for primary,
secondary, and tertiary when duration is unavailable. `--` means unavailable
data; `ERR` means fetching failed. The footer shows the oldest successful source
timestamp in local time, or the check time when all providers failed.

Legacy Cursor request plans also show request counts. For example, 25 used out
of 500 displays 95% remaining: the single-provider view shows `25/500 used`,
and multi-provider rows show `475/500` left. With two or three providers, the
second line includes used counts and the reset countdown. Counts come from
CodexBar's request-quota fields; percentage-only plans keep the normal layout.

Each provider request has a 120-second timeout, allowing for browser access
and CLI startup. Adjust it with `--timeout` (seconds per provider):

```bash
quote0 apps quota --device desk --providers claude cursor --timeout 180
```

A failed provider remains visible
while other providers continue; a partial or failed snapshot is still rendered
and saved/sent, then the command exits with status 1. Missing CodexBar, invalid
configuration, and delivery failures also exit nonzero. Quote/0 HTTP requests
use a 30-second timeout.

For Antigravity CLI usage, use a current CodexBar release. Older CodexBar builds
cannot read the local API in `agy` 1.2.2+ because it requires a CSRF token; the
final error may misleadingly say that the language server was not detected.
Updated builds support `agy`'s structured `/usage` report. See the
[upstream fix](https://github.com/steipete/CodexBar/pull/3685) and
[provider documentation](https://github.com/steipete/CodexBar/blob/v0.65.0/docs/antigravity.md).
If `agy` resolves to the older IDE launcher while the standalone CLI is installed
elsewhere, set CodexBar's override to the actual CLI executable, for example:

```bash
export ANTIGRAVITY_CLI_PATH="$HOME/.local/bin/agy"
codexbar usage --provider antigravity
```

Increasing Quote0's timeout does not change CodexBar's own source timeouts or
fix an incompatible provider integration.

Keep scheduling in a small wrapper, or adapt
[the refresh example](examples/quota_loop.sh):

```bash
while :; do
  quote0 apps quota --device desk --providers codex claude
  quote0 apps quota --device side --providers gemini
  sleep 300
done
```

The loop waits five minutes after each round, continues after individual
failures, and stops with Ctrl-C. Run it from the directory containing your
`quote0.toml` and `.env`, or use `--config` and exported keys.

### Agent skills and MCP

The installed Dot skills provide authoring/operation guidance. Installing them does
not configure the official MCP server or extend this package automatically. The
Python SDK and CLI run independently of `.agents/skills`; no skill scripts are
imported at runtime. See [Dot Skill](https://dot.mindreset.tech/docs/service/open/skill)
for the separate official MCP setup.

### Streamlit UI

- [Quote/0 API Playground · Streamlit](https://quote0.streamlit.app/)

```bash
uv run streamlit run Streamlit_Playground.py
```

### Development checks

```bash
uv run python -m unittest discover -s tests -v
```

The tests use simulated quota data and HTTP responses; they do not contact
providers or push to a device.

## Known issues



- [ ] Somehow Image API's "link" didn't work => NFC is not working

## Resources

- [Quote/0 摘录 - 少数派](https://sspai.com/create/quote0)
- [关于 Quote/0](https://dot.mindreset.tech/docs/quote_0)

### API

- [了解 API](https://dot.mindreset.tech/docs/service/open/what_is_api)
  - [图像 API](https://dot.mindreset.tech/docs/service/open/image_api) (296px × 152px)
  - [文本 API](https://dot.mindreset.tech/docs/service/open/text_api)
  - [Canvas API](https://dot.mindreset.tech/docs/service/open/canvas_api)
  - [Device List](https://dot.mindreset.tech/docs/service/open/list_devices_api)
  - [Device Settings](https://dot.mindreset.tech/docs/service/open/device_settings_api)
