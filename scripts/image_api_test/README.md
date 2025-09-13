# Image API Test

## Using the new CLI tool

The new `quote0` CLI tool provides a cleaner interface for sending images:

```bash
# Send base64 image (like the original plot_base64.sh)
echo 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR42mNgYGAAAAAEAAHI6uv5AAAAAElFTkSuQmCC' | ./plot_base64_cli.sh

# Or use the CLI directly
quote0 image --base64 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR42mNgYGAAAAAEAAHI6uv5AAAAAElFTkSuQmCC' --border BLACK

# Send preset images
quote0 image --preset ALL_BLACK
quote0 image --preset CHECKERBOARD_GRAY

# Send image files
quote0 image --file image.png --border WHITE
```

## Legacy methods (still work)

```bash
# Pipe Python output to plot
python t0_compact_base64_new.py | ./plot_base64.sh

# Cron job to regularly refresh
python mini_cron.py
```

## Available options

- `--file`: Path to image file
- `--preset`: Use preset test image (ALL_BLACK, CHECKERBOARD_GRAY, ONE_PIXEL_BLACK)
- `--base64`: Direct base64 encoded image string
- `--border`: Border color (WHITE=0, BLACK=1)
- `--link`: NFC link for touch interaction
- `--dither-type`: Dithering algorithm (DIFFUSION, ORDERED, NONE)
- `--no-refresh`: Don't refresh display immediately

Note: You can only use one of `--file`, `--preset`, or `--base64` at a time.
