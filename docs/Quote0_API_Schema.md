# Quote/0 API Schema

## Text API


| 字段名       | 类型     | 必填 | 默认值 | 说明                                  | 用途                     |
| ------------ | -------- | ---- | ------ | ------------------------------------- | ------------------------ |
| `refreshNow` | `bool`   | 否   | `true` | 是否立刻显示内容                      | 控制内容的显示时机       |
| `deviceId`   | `string` | 是   |        | 设备序列号                            | 分辨不同的设备           |
| `title`      | `string` | 否   |        | 文本标题                              | 显示在屏幕上的标题       |
| `message`    | `string` | 否   |        | 文本内容                              | 显示在屏幕上的内容       |
| `signature`  | `string` | 否   |        | 文本签名                              | 显示在屏幕上的签名       |
| `icon`       | `string` | 否   |        | base64 编码 PNG 图标数据（40px*40px） | 显示在屏幕左下角上的图标 |
| `link`       | `string` | 否   |        | http/https 链接或 Scheme Url          | 碰一碰跳转的内容         |

## Image API

| 字段名         | 类型     | 必填 | 默认值            | 说明                                                                                                                                                                    | 用途               |
| -------------- | -------- | ---- | ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| `refreshNow`   | `bool`   | 否   | `true`            | 是否立刻显示内容                                                                                                                                                        | 控制内容的显示时机 |
| `deviceId`     | `string` | 是   |                   | 设备序列号                                                                                                                                                              | 分辨不同的设备     |
| `image`        | `string` | 是   |                   | base64 编码 PNG 图像数据（296px*152px）                                                                                                                                 | 屏幕呈现的图像     |
| `link`         | `string` | 否   |                   | http/https 链接或 Scheme Url                                                                                                                                            | 碰一碰跳转的内容   |
| `border`       | `number` | 否   | `0`               | `0` 代表白色边框，`1` 代表黑色边框                                                                                                                                      | 屏幕呈现的边框     |
| `ditherType`   | `string` | 否   | `DIFFUSION`       | 抖动类型（可选：`DIFFUSION`、`ORDERED`、`NONE`）                                                                                                                        | 控制图像的抖动效果 |
| `ditherKernel` | `string` | 否   | `FLOYD_STEINBERG` | 抖动算法（可选：`THRESHOLD`、`ATKINSON`、`BURKES`、`FLOYD_STEINBERG`、`SIERRA2`、`STUCKI`、`JARVIS_JUDICE_NINKE`、`DIFFUSION_ROW`、`DIFFUSION_COLUMN`、`DIFFUSION2_D`） | 控制图像的抖动算法 |
