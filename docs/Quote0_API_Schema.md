# Quote/0 API Schema

## Endpoint 与认证

| API | 请求 |
| --- | --- |
| Text | `POST https://dot.mindreset.tech/api/authV2/open/device/{deviceId}/text` |
| Image | `POST https://dot.mindreset.tech/api/authV2/open/device/{deviceId}/image` |

`deviceId` 是必填的 URL 路径参数，不再放入 JSON 请求体。请求头使用
`Authorization: Bearer <API key>` 和 `Content-Type: application/json`。

旧版 `/api/open/text` 与 `/api/open/image` 已弃用；官方目前仍说明它们会转发到新版，
但未来可能取消转发。Quote0 已直接使用新版接口。

以下请求体表列出 Quote0 client 支持的字段。Python 导出的 `ImageApiRequest` 与
`TextApiRequest` 仍保留 `deviceId` 字段以兼容原有调用，client 发送 JSON 时会排除该字段。
`Quote0(api_key, device_id)`、`send_image()` 和 `send_text()` 的调用方式不变。

## Text API

| 字段名       | 类型     | 必填 | 默认值 | 说明                                  | 用途                     |
| ------------ | -------- | ---- | ------ | ------------------------------------- | ------------------------ |
| `refreshNow` | `bool`   | 否   | `true` | 是否立刻显示内容                      | 控制内容的显示时机       |
| `title`      | `string` | 否   |        | 文本标题                              | 显示在屏幕上的标题       |
| `message`    | `string` | 否   |        | 文本内容                              | 显示在屏幕上的内容       |
| `signature`  | `string` | 否   |        | 文本签名                              | 显示在屏幕上的签名       |
| `icon`       | `string` | 否   |        | base64 编码 PNG 图标数据（40px*40px） | 显示在屏幕左下角上的图标 |
| `link`       | `string` | 否   |        | http/https 链接或 Scheme Url          | 碰一碰跳转的内容         |

## Image API

| 字段名         | 类型     | 必填 | 默认值            | 说明                                                                                                                                                                    | 用途               |
| -------------- | -------- | ---- | ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| `refreshNow`   | `bool`   | 否   | `true`            | 是否立刻显示内容                                                                                                                                                        | 控制内容的显示时机 |
| `image`        | `string` | 是   |                   | base64 编码 PNG 图像数据（296px*152px）                                                                                                                                 | 屏幕呈现的图像     |
| `link`         | `string` | 否   |                   | http/https 链接或 Scheme Url                                                                                                                                            | 碰一碰跳转的内容   |
| `border`       | `number` | 否   | `0`               | `0` 代表白色边框，`1` 代表黑色边框                                                                                                                                      | 屏幕呈现的边框     |
| `ditherType`   | `string` | 否   | `DIFFUSION`       | 抖动类型（可选：`DIFFUSION`、`ORDERED`、`NONE`）                                                                                                                        | 控制图像的抖动效果 |
| `ditherKernel` | `string` | 否   | `FLOYD_STEINBERG` | 抖动算法（可选：`THRESHOLD`、`ATKINSON`、`BURKES`、`FLOYD_STEINBERG`、`SIERRA2`、`STUCKI`、`JARVIS_JUDICE_NINKE`、`DIFFUSION_ROW`、`DIFFUSION_COLUMN`、`DIFFUSION_2D`） | 控制图像的抖动算法 |

## Response

新版使用 **HTTP 状态码** 表示请求结果，成功与失败的 JSON 响应体均使用 `message`，
不再依赖旧版响应中的 `code` 或 `result`。

| 字段名    | 类型     | 说明     |
| --------- | -------- | -------- |
| `message` | `string` | 响应描述 |

```json
{"message": "Device ABCD1234ABCD Image API content switched."}
```

| HTTP 状态码 | 含义             | 描述 |
| ----------- | ---------------- | ---- |
| `200` | 成功             | API 内容已切换，或数据已更新但未切换内容 |
| `400` | 参数错误         | 设备 ID 缺失或格式错误、无效的图像/图标、边框或抖动参数错误等 |
| `403` | 权限不足         | 当前 API key 无权操作此设备 |
| `404` | 设备或内容不存在 | 设备不存在或未注册，或设备 Loop 中未添加对应的 Image API / Text API 内容 |
| `500` | 设备响应失败     | API 内容切换失败 |

出现 404 时应检查装置序号和 Loop 内容，不能仅凭状态码认定 endpoint 已被移除。
Quote0 的 `ApiResponse.status_code` 保留 HTTP 状态，`response` 保留解析后的 JSON 对象
（包括 HTTP 错误响应），`message` 展示服务器信息，`error` 提供失败详情。

官方文档：[Text API](https://dot.mindreset.tech/docs/service/open/text_api)、
[Image API](https://dot.mindreset.tech/docs/service/open/image_api)。
