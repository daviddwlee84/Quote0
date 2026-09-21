#!/bin/sh
# Run from the directory containing quote0.toml and .env.
# Edit the device names and provider lists for your setup.
# Continue after individual failures; Ctrl-C stops the loop.
trap 'exit 0' INT TERM

while :; do
    quote0 apps quota --device desk --providers codex claude
    quote0 apps quota --device side --providers gemini
    sleep 300
done
