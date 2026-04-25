#!/usr/bin/env python3

import json
import sys

INC = 53.0
ECC = 0.0000011
ARGP = 0.0
MEAN_MOTION = 15.055
EPOCH = "26060.45726852"

F = 0  # ⭐ Walker phasing parameter


def checksum(line):
    s = 0
    for c in line[:68]:
        if c.isdigit():
            s += int(c)
        elif c == '-':
            s += 1
    return s % 10


def tle_line1():
    line = f"1 00000U 23666A   {EPOCH}  .00000000  00000-0 00000000 0 0000"
    line = line[:68].ljust(68)
    return line + str(checksum(line))


def tle_line2(raan, M):
    ecc_str = f"{int(ECC * 1e7):07d}"

    line = (
        f"2 00000 "
        f"{INC:8.4f} "
        f"{raan:8.4f} "
        f"{ecc_str} "
        f"{ARGP:8.4f} "
        f"{M:8.4f} "
        f"{MEAN_MOTION:11.8f}"
    )

    line = line[:68].ljust(68)
    return line + str(checksum(line))


def generate(num_planes, sats_per_plane, start_raan, start_M):

    instances = []
    links = []

    raan_step = 5.0
    M_step = 16.3637

    def idx(p, s):
        return p * sats_per_plane + s

    # -----------------------------
    # SATELLITES (WITH PHASING)
    # -----------------------------
    for p in range(num_planes):
        raan = (start_raan + p * raan_step) % 360

        for s in range(sats_per_plane):

            # ⭐ Walker delta phasing
            phase = (p * F * M_step)

            M = (start_M + s * M_step + phase) % 360

            instances.append({
                "type": "Satellite",
                "extra": {
                    "TLE_0": f"NODE_{p}_{s}",
                    "TLE_1": tle_line1(),
                    "TLE_2": tle_line2(raan, M),
                    "Area": "0.0.0.0",
                    "OrbitIndex": str(p),
                    "SatelliteIndex": str(s)
                },
                "device_info": {}
            })

    # -----------------------------
    # LINKS (UNCHANGED)
    # -----------------------------
    for p in range(num_planes):
        for s in range(sats_per_plane):

            cur = idx(p, s)

            # intra-plane ring
            nxt = idx(p, (s + 1) % sats_per_plane)

            links.append({
                "end_indexes": [cur, nxt],
                "type": "vlink",
                "init_parameter": {},
                "address_infos": [{}, {}],
                "extra": {}
            })

            # inter-plane
            nxt_plane = (p + 1) % num_planes
            vertical = idx(nxt_plane, s)

            links.append({
                "end_indexes": [cur, vertical],
                "type": "vlink",
                "init_parameter": {},
                "address_infos": [{}, {}],
                "extra": {}
            })

    return {
        "instances": instances,
        "links": links
    }


if __name__ == "__main__":

    if len(sys.argv) != 6:
        print(
            "Usage:\n"
            "python3 generate_topology.py "
            "<planes> <sats_per_plane> <start_raan> <start_M> <output.json>"
        )
        sys.exit(1)

    planes = int(sys.argv[1])
    sats = int(sys.argv[2])
    raan = float(sys.argv[3])
    M = float(sys.argv[4])
    out = sys.argv[5]

    topo = generate(planes, sats, raan, M)

    with open(out, "w") as f:
        json.dump(topo, f, indent=2)

    print(f"✔ Generated topology with Walker phasing → {out}")