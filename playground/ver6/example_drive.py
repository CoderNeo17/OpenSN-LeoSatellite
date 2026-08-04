"""
Example: drive the containerized Chromium via chromedriver (remote WebDriver),
navigate to a WebRTC test page, and pull live getStats() data.

Run the container with the "chromedriver" arg first:
    docker run --rm -it --network host \
        -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix \
        chromium-webrtc-research:latest chromedriver

Then run this script from your host or another container on the same network.
"""

import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

CHROMEDRIVER_URL = "http://localhost:9515"

options = Options()
options.add_argument("--use-fake-ui-for-media-stream")
options.add_argument("--use-fake-device-for-media-stream")
# Point at whatever page runs your WebRTC test harness / your own
# setParameters()-driven control page
TEST_PAGE = "https://your-test-harness.local/webrtc_test.html"

driver = webdriver.Remote(command_executor=CHROMEDRIVER_URL, options=options)

try:
    driver.get(TEST_PAGE)
    time.sleep(5)  # let the connection establish

    # Pull getStats() via JS execution -- adapt the selector/variable name
    # to however your test page exposes its RTCPeerConnection object
    stats_json = driver.execute_async_script("""
        const callback = arguments[arguments.length - 1];
        window.pc.getStats(null).then(stats => {
            const out = [];
            stats.forEach(report => out.push(report));
            callback(JSON.stringify(out));
        });
    """)
    stats = json.loads(stats_json)
    for report in stats:
        if report.get("type") in ("inbound-rtp", "outbound-rtp", "candidate-pair"):
            print(report.get("type"), {
                k: v for k, v in report.items()
                if k in ("bytesSent", "bytesReceived", "packetsLost",
                          "jitter", "currentRoundTripTime", "framesDecoded",
                          "frameWidth", "frameHeight", "qpSum")
            })

    # Example: push a new decision from your controller via setParameters()
    driver.execute_script("""
        const sender = window.pc.getSenders()[0];
        const params = sender.getParameters();
        if (!params.encodings) { params.encodings = [{}]; }
        params.encodings[0].maxBitrate = arguments[0];
        sender.setParameters(params);
    """, 500_000)  # bits/sec -- replace with your model's output

finally:
    driver.quit()
