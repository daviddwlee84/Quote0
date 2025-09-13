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

### Streamlit UI

- [Quote/0 API Playground · Streamlit](https://quote0.streamlit.app/)

```bash
uv run streamlit run Streamlit_Playground.py
```

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
