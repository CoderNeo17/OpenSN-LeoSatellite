# Chromium + WebRTC research container

Chromium in Docker, with X11 display forwarding for GUI use, and a
chromedriver mode for programmatic control from your DL/controller process.

## Build

```bash
docker build -t chromium-webrtc-research:latest .
```

## Run with GUI (X11 forwarding, Linux host)

```bash
xhost +local:docker   # allow container to connect to your X server
                       # (scope this down to +local:root or a specific
                       # container hostname for anything beyond local dev)

docker run --rm -it \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    --network host \
    --ipc host \
    chromium-webrtc-research:latest
```

**If your host is macOS or Windows**, there's no native X server, so this
exact approach won't work as-is:
- macOS: install XQuartz, enable "Allow connections from network clients" in
  its preferences, `xhost + 127.0.0.1`, and set `DISPLAY=host.docker.internal:0`.
- Windows: use WSL2 with WSLg (has X11 forwarding built in), or VcXsrv.
- Cross-platform alternative that sidesteps all of this: run a VNC server
  (`x11vnc` or `tigervnc`) inside the container instead of forwarding to the
  host X server, and connect with any VNC client, or expose it via noVNC in
  a browser tab. Say the word if you want this variant instead — it's a
  small change to the Dockerfile/entrypoint.

## Run headless + programmatic control (chromedriver / Selenium)

This is likely what you want for the actual measurement/training loop —
GUI forwarding is for debugging and eyeballing behavior, not for your
automated runs.

```bash
docker run --rm -it --network host \
    chromium-webrtc-research:latest chromedriver
```

Then drive it from your controller process — see `example_drive.py` for a
Selenium example that reads `getStats()` and pushes bitrate decisions via
`setParameters()`.

## On `--no-sandbox`

Chromium's sandbox needs either:
- `--cap-add=SYS_ADMIN` on the container (weakens container isolation --
  fine for an isolated research VM, avoid on shared/multi-tenant hosts), or
- a properly configured user namespace (more setup, keeps isolation intact), or
- `--no-sandbox` as a Chromium flag (simplest, but disables a real security
  boundary — acceptable for throwaway measurement containers that only ever
  load your own test pages, not for anything that browses arbitrary content).

For a research harness that only ever loads pages you control, `--no-sandbox`
is a reasonable pragmatic choice. Add it to the `FLAGS` array in
`entrypoint.sh` if you go this route, rather than `--cap-add=SYS_ADMIN`.

## Networking your measurement setup

The `--network host` flag above assumes you want this container on the same
network namespace as whatever netem/tc rules your existing measurement
harness applies. If your current Firefox container instead attaches to a
custom bridge network with per-container `tc` shaping (e.g. `--network
my-measurement-net`), use that same flag here instead of `--network host`,
so both browsers sit under identical shaping rules.

## Launching programmatically (matches your existing launcher)

Since your program spins up containers from a specified image rather than
using compose, the equivalent call is just the image name plus whatever
flags you're already passing to your Firefox containers, with the
X11/WebRTC-relevant ones added. If you're using the Docker SDK for Python
(likely, given you're scripting this):

```python
import docker

client = docker.from_env()

container = client.containers.run(
    image="chromium-webrtc-research:latest",
    detach=True,
    environment={"DISPLAY": ":0"},
    volumes={"/tmp/.X11-unix": {"bind": "/tmp/.X11-unix", "mode": "rw"}},
    network_mode="host",       # or your existing measurement network name
    ipc_mode="host",           # Chromium needs real /dev/shm; see note below
    cap_add=["SYS_ADMIN"],     # only if not using --no-sandbox, see below
    command="chromedriver",    # or omit for GUI mode, or "shell" for a bash shell
)
```

Same three knobs matter regardless of how you launch it:
- `network_mode` — must match whatever network your netem shaping is applied to.
- `ipc_mode="host"` (or `shm_size="2g"` instead if you'd rather not share
  the host IPC namespace) — Chromium is memory-hungry on `/dev/shm` and
  will crash renderers without one of these.
- sandboxing — either `cap_add=["SYS_ADMIN"]`, or skip both and add
  `--no-sandbox` to the `FLAGS` array in `entrypoint.sh` instead (simpler,
  see caveat above).

## Logs / instrumentation

- `chrome://webrtc-internals` — open manually in the GUI mode for live
  inspection.
- `getStats()` — pull programmatically, see `example_drive.py`.
- `--enable-logging=stderr --v=1` (already in `entrypoint.sh`) — dumps
  internal WebRTC logging; redirect container stdout/stderr to a file per
  run for offline parsing.
- If you later move to patching libwebrtc source directly (see earlier
  discussion on standalone `peerconnection_client` builds), this same
  container structure works — just swap the apt-installed `chromium-browser`
  for your custom-built binary in the Dockerfile's COPY step, same as the
  Firefox approach.

## Files

- `Dockerfile` — image definition
- `entrypoint.sh` — launches Chromium with WebRTC-relevant flags, or
  chromedriver in automation mode
- `fake_media/` — deterministic test-pattern video + tone, generated at
  build time via ffmpeg, used for `getUserMedia()` without real hardware
- `docker-compose.yml` — convenience wrapper for the X11-forwarded run
- `example_drive.py` — Selenium example: read stats, push bitrate decisions
