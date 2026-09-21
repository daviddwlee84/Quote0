# Quote/0

A Quote/0 Client + Streamlit App and Notes about SSPAI's Quote/0

> Firmware version 1.6.10

## Getting Started

1. Connect Type-C
2. Bind device in Mobile App
3. Select content to show
4. (optional) Request API key in App (and get Device ID) -> use [API](#API)
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
🖼️  Using preset image: checkerboard_gray
📤 Sending image to Quote/0 device... (border: WHITE)
✅ Image sent successfully!

# Text API with Environment Variable
export DOT_API_KEY=dot_app_....
export DOT_DEVICE_ID=ABCD1234ABCD

$ quote0 text --title Hello --message World
📤 Sending text to Quote/0 device...
✅ Text sent successfully!
```

The CLI also loads `.env` from the current working directory when resolving a
device. Exported environment variables take precedence over `.env`; explicit
`--api-key` and `--device-id` flags take precedence over both.

#### Named devices

Copy [quote0.example.toml](quote0.example.toml) to `quote0.toml` and edit the
device IDs. Configuration describes delivery targets only:

```toml
[devices.desk]
device_id = "DEVICE_A"
api_key_env = "DOT_API_KEY"

[devices.side]
device_id = "DEVICE_B"
api_key_env = "DOT_SIDE_API_KEY"
```

Set the referenced keys in your environment or `.env`. Devices may reference
the same key if it is authorized for both, or different keys.

```bash
quote0 text --device desk --message Hello
quote0 image --device side --file image.png
quote0 image --config /path/to/devices.toml --device desk --file image.png
```

`--device` selects a named target; explicit credential flags can override its
fields. A named device uses its own ID and key reference, regardless of unrelated
`DOT_DEVICE_ID` / `DOT_API_KEY` variables. Without `--device`, the CLI uses the
original `DOT_*` environment variables and does not read TOML. `.env` is always
relative to the working directory, even when `--config` points elsewhere.

Python scripts can use the same resolver with the generic client:

```python
from quote0 import Quote0
from quote0.config import resolve_device

device = resolve_device(device="desk")
client = Quote0(device.api_key, device.device_id)
client.send_text(message="Hello")
```

#### Apps: agent quota

`apps` groups applications built on the generic client. The first application
renders [CodexBar](https://github.com/steipete/CodexBar) quotas as a 296×152
monochrome PNG. Install `codexbar` on `PATH` and configure its provider access
first. The integration targets the
[CodexBar 0.56.3 JSON format](https://github.com/steipete/CodexBar/blob/v0.56.3/docs/cli.md).
The generic library and `text` / `image` commands do not require CodexBar.

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
saves a PNG instead of sending, even if delivery options are also supplied.

| Services | Automatic layout |
| --- | --- |
| 1 | Up to three windows, remaining percentages, reset countdowns, and bars |
| 2–3 | Two windows per service, with remaining percentages and reset countdowns |
| 4–6 | One row per service, with two remaining percentages |

Window labels use the reported duration, or `P` / `S` / `T` for primary,
secondary, and tertiary when duration is unavailable. `--` means unavailable
data; `ERR` means fetching failed. The footer shows the oldest successful source
timestamp in local time, or the check time when all providers failed.

Provider requests have a 30-second timeout. A failed provider remains visible
while other providers continue; a partial or failed snapshot is still rendered
and saved/sent, then the command exits with status 1. Missing CodexBar, invalid
configuration, and delivery failures also exit nonzero. Quote/0 HTTP requests
use a 30-second timeout.

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

## Todo

- [ ] Determine whether same API Key can control multiple Device ID

Bug:

- [ ] Somehow Image API's "link" didn't work => NFC is not working

## Resources

- [Quote/0 摘录 - 少数派](https://sspai.com/create/quote0)
- [关于 Quote/0](https://dot.mindreset.tech/docs/quote_0)

### API

- [了解 API](https://dot.mindreset.tech/docs/server/template/api)
  - [图像 API](https://dot.mindreset.tech/docs/server/template/api/image_api) (296px × 152px)
  - [文本 API](https://dot.mindreset.tech/docs/server/template/api/text_api)
