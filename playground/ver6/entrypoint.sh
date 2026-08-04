#!/bin/bash
set -e

# ---------------------------------------------------------------------------
# This entrypoint just launches Chromium pointed at $DISPLAY (forwarded from
# host) with flags relevant to WebRTC research. Override CMD at `docker run`
# time if you want to launch chromedriver instead (see README).
# ---------------------------------------------------------------------------

CHROMIUM_BIN=$(command -v google-chrome-stable || command -v google-chrome || command -v chromium)

# Where fake media (test pattern video + tone) lives, used with
# --use-file-for-fake-video-capture / --use-file-for-fake-audio-capture
FAKE_VIDEO=/home/webrtc/fake_media/test_pattern.y4m
FAKE_AUDIO=/home/webrtc/fake_media/tone.wav

FLAGS=(
  # --- Sandbox: keep enabled; only relevant Docker requirement is
  # `--cap-add=SYS_ADMIN` OR running with user namespaces set up right.
  # See README for the tradeoffs before reaching for --no-sandbox.

  # --- Auto-grant camera/mic so you don't need to click through permission
  # prompts on every automated run
  --use-fake-ui-for-media-stream
  --use-fake-device-for-media-stream

  # --- Feed a deterministic, repeatable video/audio source instead of relying
  # on real webcam/mic. This makes A/B runs across your DL policy variants
  # comparable, since the *source* content is identical every time.
  --use-file-for-fake-video-capture="${FAKE_VIDEO}"
  --use-file-for-fake-audio-capture="${FAKE_AUDIO}"

  # --- Useful for reproducibility / field-trial style experiment toggles.
  # Add your own via --force-fieldtrials="YourExperiment/GroupA/" if you're
  # instrumenting libwebrtc with custom field trials.
  # --force-fieldtrials=""

  # --- Logging: dump webrtc internals to a file you can pull stats from
  --enable-logging=stderr
  --v=1

  # --- Disable stuff irrelevant to headed/automation research use that
  # otherwise adds noise or network calls
  --disable-background-networking
  --disable-sync
  --no-first-run
  --disable-features=TranslateUI
  --disable-extensions

  # --- Window sizing helpful for consistent VMAF/SSIM capture if you're
  # screen-recording via ffmpeg on the X display
  --window-size=1280,800
  --window-position=0,0
)

if [ "$1" = "shell" ]; then
  exec /bin/bash
elif [ "$1" = "chromedriver" ]; then
  exec chromedriver --port=9515 --whitelisted-ips="" --allowed-ips=""
else
  exec "$CHROMIUM_BIN" "${FLAGS[@]}" "$@"
fi