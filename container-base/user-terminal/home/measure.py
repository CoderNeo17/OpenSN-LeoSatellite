import socket
import time
import psutil
import json

SERVER_IP = "<ground_station_ip>"
PORT = 9999
INTERFACE = "eth0"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(1)

seq = 0
last_bytes = psutil.net_io_counters(pernic=True)[INTERFACE].bytes_sent

with open("trace.jsonl", "w") as f:

    prev_rtt = None

    while True:
        t_send = time.time_ns()

        msg = str(seq).encode()
        sock.sendto(msg, (SERVER_IP, PORT))

        lost = 0
        rtt_ms = None

        try:
            data, _ = sock.recvfrom(1024)
            t_recv = time.time_ns()
            rtt_ms = (t_recv - t_send) / 1e6
        except:
            lost = 1

        # throughput (200 ms window)
        time.sleep(0.2)
        new_bytes = psutil.net_io_counters(pernic=True)[INTERFACE].bytes_sent
        throughput = (new_bytes - last_bytes) * 8 / 0.2
        last_bytes = new_bytes

        # jitter
        jitter = 0
        if prev_rtt is not None and rtt_ms is not None:
            jitter = abs(rtt_ms - prev_rtt)
        prev_rtt = rtt_ms if rtt_ms is not None else prev_rtt

        # OPTIONAL: get satellite ID from your emulator if accessible
        sat_id = "unknown"

        log = {
            "time": time.time(),
            "rtt_ms": rtt_ms,
            "loss": lost,
            "throughput_bps": throughput,
            "jitter": jitter,
            "satellite": sat_id
        }

        f.write(json.dumps(log) + "\n")
        f.flush()

        seq += 1