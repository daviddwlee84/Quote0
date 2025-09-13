# Quote/0

Everything about SSPAI's Quote/0

> Firmware version 1.6.10

## Getting Started

1. Connect Type-C
2. Bind device in Mobile App
3. Select content to show
4. (optional) Request API key in App (and get Device ID) -> use [API](#API)

- [Update Software](https://dot.mindreset.tech/tool/update)
  - update firmware
  - reset network
  - reset device

NOTE: to test if the display is normal you can use the script [checkerboard_gray.sh](scripts/image_api_test/checkerboard_gray.sh)

## API

- [了解 API](https://dot.mindreset.tech/docs/server/template/api)
  - [图像 API](https://dot.mindreset.tech/docs/server/template/api/image_api) (296px × 152px)
  - [文本 API](https://dot.mindreset.tech/docs/server/template/api/text_api)

## My CLI

```bash
# Install this package
$ uv tool install quote0

# Image API
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

## Todo

Bug:

- [ ] Somehow Image API's "link" didn't work => NFC is not working

## Resources

- [Quote/0 摘录 - 少数派](https://sspai.com/create/quote0)
- [关于 Quote/0](https://dot.mindreset.tech/docs/quote_0)

### Projects

> [社区共创](https://dot.mindreset.tech/docs/server/community_co_creation)

- [stvlynn/quote0-mcp](https://github.com/stvlynn/quote0-mcp)
  - [Steven Lynn on X: "昨天在少数派爆金币买了这么一个墨水屏 Quote/0 自定义程度很高，开放了 API 于是回来后火速搓了一个 MCP server，可以把和 LLM 对话的要点总结推送到屏幕上，NFC 写入快速预览的链接 https://t.co/LHN4CTF8xa" / X](https://x.com/Stv_Lynn/status/1954423827737239664)
- [onehupo/DotClient](https://github.com/onehupo/DotClient)

---

- [MCP-Playground/docs/Environment.md at main · daviddwlee84/MCP-Playground](https://github.com/daviddwlee84/MCP-Playground/blob/main/docs/Environment.md): `direnv` + `.env` / `python-dotenv`

```bash
# direnv
brew install direnv
grep -q 'direnv hook zsh' ~/.zshrc || echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc

# dotenv (not sure if this is needed, but we use it in the `.envrc`)
# pip install "python-dotenv[cli]"
uv tool install "python-dotenv[cli]"
```

```bash
$ direnv allow
direnv: loading ~/Documents/Program/Personal/Quote0/.envrc                                                                       
direnv: export +DOT_API_KEY +DOT_DEVICE_ID
```

Upload package

```bash
# Build package
uv run python -m build

# Register PyPI / TestPyPI
# https://test.pypi.org/account/register/
# Update $HOME/.pypirc with PyPI API Key config
uv run twine upload --repository testpypi dist/*
uv run twine upload dist/*
```
