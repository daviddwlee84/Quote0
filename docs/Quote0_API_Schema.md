# Quote/0 OpenAPI support

Base: `https://dot.mindreset.tech/api/authV2/open`. All operations use
`Authorization: Bearer <API key>`; POST bodies use JSON. Device IDs are escaped URL
path segments and are not sent in request bodies.

| SDK method | Method and path |
| --- | --- |
| `DotClient.list_devices()` | `GET /devices` |
| `DotClient.list_timezones()` | `GET /timezones` |
| `Quote0.get_status()` | `GET /device/{id}/status` |
| `Quote0.list_tasks("loop" or "fixed")` | `GET /device/{id}/{taskType}/list` |
| `Quote0.next_content()` | `POST /device/{id}/next` |
| `Quote0.send_text(...)` | `POST /device/{id}/text` |
| `Quote0.send_image(...)` | `POST /device/{id}/image` |
| `Quote0.send_canvas(window_data, ...)` | `POST /device/{id}/canvas` |
| `Quote0.get_settings()` | `GET /device/{id}/settings` |
| `Quote0.update_settings(dict_or_model)` | `POST /device/{id}/settings` |

`Quote0` inherits the account queries. Existing `Quote0(api_key, device_id)`,
`send_text()` and `send_image(image_base64=...)` calls remain supported.
`send_image(image=...)` is the more general alternative for a public URL or Base64.
Do not supply both image arguments. The exported Text/Image request models retain
`deviceId` for existing callers; the client excludes it when sending.

## Responses and failures

Every SDK operation returns `ApiResponse[T]` with `success`, `status_code`,
`response`, `message`, and `error`. Successful queries contain typed data:
`list[DeviceInfo]`, `list[TimezoneInfo]`, `DeviceStatus`, `list[DeviceTask]`, or
`DeviceSettings`. Read models preserve additional server fields.

Successful controls contain the server's JSON object, usually `{ "message": "..." }`.
HTTP status determines success; legacy `code`/`result` fields are not interpreted.
Error JSON objects remain available in `response`. Invalid JSON or an unexpected
successful response shape becomes a failed `ApiResponse`. Local validation errors
raise `ValueError` (including Pydantic `ValidationError`); CLI commands report them
and exit nonzero. `--json` prints only query data to stdout; errors go to stderr.

Requests have a 30-second timeout and are not automatically retried. The official
rate limit is 10 requests/second; callers should handle 429 without repeatedly
resending writes. A 404 can indicate a missing device or missing matching API
content in its Loop, rather than an obsolete endpoint. Content must first be added
in Dot App Content Studio. Success means the server accepted the operation, not
that a sleeping/battery-powered device has already displayed it.

## Content options

Text, Image and Canvas accept `refresh_now` (default true), `task_key` and
`task_alias`, serialized as `refreshNow`, `taskKey`, and `taskAlias`.
Use a task's `key` returned by `list_tasks()` to target a particular content item.
Without a key the server chooses its first matching item.

Task listing is read-only. The published OpenAPI has no task creation, deletion,
reordering or enable/disable endpoint; those remain Dot App operations.
`refreshNow=false` controls immediate display, not whether the task is enabled.

Omitting `task_alias` preserves the name. An empty string or explicit `None` clears
it. The SDK uses an omission sentinel so that a default call never clears aliases.
Strings may contain at most 100 characters; numeric aliases are also accepted.
CLI `--task-alias ""` explicitly clears a name.

| Content | Additional fields |
| --- | --- |
| Text | `title`, `message`, `signature`, `icon`, `link`, `styles` |
| Image | `image`, `border`, `link`, `ditherType`, `ditherKernel` |
| Canvas | `windowData`, `data`, `layoutFull`, `border`, `link` |

`border` is 0 (white) or 1 (black). Image dither types are `DIFFUSION`, `ORDERED`,
`NONE`; kernels follow the official schema. Text preserves message newlines/tabs.
Icon and image strings may be PNG Base64, PNG data URIs, or public http(s) image URLs.
Icon Base64 decodes to at most 1 MB; Image Base64 to at most 3 MB. Remote URLs must
be anonymously accessible, at most 2048 characters, and directly return image
content of at most 3 MB. CLI local-file checks enforce the respective byte limits;
remote content/format validation remains server-side.

Text `styles.title`/`styles.signature` support `fontFamily`, `fontSize` (8–48), and
`fontWeight` (100–900 in steps of 100); `styles.message` additionally supports
`lineHeight` (0.8–3). Font names use the official Text API vocabulary, e.g.
`ChillDuanSans`, `FusionPixel12`, `Zpix12`.

## Canvas validation and export

`CanvasApiRequest` requires `windowData.default` to be an array. Nodes use `type`
(`div`, `span`, `img`) and `props` with `tw`, `style`, and `children`. The validator
also accepts documented `$for`/`$empty` and `$ifAny`/`$then`/`$else` structures.
Templates are strings; the client does not execute or compile them.

Local checks cover JSON shape, reserved keys, disallowed event/HTML properties,
80 static elements, nesting depth 16, strings of at most 4000 characters in
windowData, and UTF-8 JSON sizes: data 64 KiB, windowData 128 KiB, layoutFull 8 KiB.
They do not guarantee font metrics, supported CSS semantics, remote images, or
server-expanded loop geometry. No browser/JS or offline server-rendering clone is
included. Failures identify the JSON path.

Canvas JSON files use the public request field names. Explicit CLI task flags
override the corresponding fields; `--no-refresh` forces false and otherwise the
file's value is preserved. `--validate-only` runs before credential/device
resolution. Quota Canvas exports include data/layout without credentials or a
device binding, and can be sent with the generic Canvas CLI.

## Settings

Updates accept at least one of `alias`, `location`, `timezone`, `interval`, `sleep`.
Omitted fields are preserved; explicit `null`/empty string clears only alias or
location. Names are at most 100 characters. Unknown fields and null values for
other settings are rejected locally.

`interval.powerMs`/`batteryMs` must be integers in 60,000–43,200,000, in multiples
of 60,000. Either or both can be updated. A supplied sleep object requires boolean
`enabled`, `start` and `end` in local `HH:mm`; equal times are invalid, crossing
midnight is valid. A timezone update first queries `/timezones` and requires an
exact returned key; query failure prevents the settings POST.

## Sources

Schemas were checked against the official
[Dot OpenAPI schema](https://github.com/MindReset/dot_skill/blob/main/openapi/dot-openapi.yaml).
See [Text](https://dot.mindreset.tech/docs/service/open/text_api),
[Image](https://dot.mindreset.tech/docs/service/open/image_api),
[Canvas](https://dot.mindreset.tech/docs/service/open/canvas_api),
[Device List](https://dot.mindreset.tech/docs/service/open/list_devices_api), and
[Settings](https://dot.mindreset.tech/docs/service/open/device_settings_api).
The package has no runtime dependency on the separately installed skills or MCP.
