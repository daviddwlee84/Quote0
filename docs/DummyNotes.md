# Dummy Notes

> Make README.md more clean

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
