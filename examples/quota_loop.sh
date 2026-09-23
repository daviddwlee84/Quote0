#!/bin/sh
# Run from the directory containing quote0.toml and .env.
# Edit the device names and provider lists for your setup.
# To use Canvas, add --renderer canvas --task-key YOUR_CANVAS_TASK_KEY.
# Add the matching API content to the device Loop first.
# Continue after individual failures; Ctrl-C stops the loop.
trap 'exit 0' INT TERM

while :; do
    quote0 apps quota --device desk --renderer image --providers codex claude
    quote0 apps quota --device side --renderer image --providers gemini
    sleep 300
done
