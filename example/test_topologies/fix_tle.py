#!/usr/bin/env python3

import sys
import json


def compute_checksum(line):
    total = 0
    for c in line[:68]:
        if c.isdigit():
            total += int(c)
        elif c == '-':
            total += 1
    return total % 10


def format_tle_line1(line1):
    line1 = line1.strip()

    # remove old checksum
    line1 = line1[:68].ljust(68)

    checksum = compute_checksum(line1)
    return line1 + str(checksum)


def format_tle_line2(satnum, inc, raan, ecc, argp, M, n):
    """
    Strict column-based formatting
    """

    ecc_str = f"{int(ecc * 1e7):07d}"

    line = (
        f"2 {satnum:05d} "
        f"{inc:8.4f} "
        f"{raan:8.4f} "
        f"{ecc_str} "
        f"{argp:8.4f} "
        f"{M:8.4f} "
        f"{n:11.8f}"
    )

    # enforce exact width
    line = line[:68].ljust(68)

    checksum = compute_checksum(line)
    return line + str(checksum)


def main(filepath):
    with open(filepath, "r") as f:
        data = json.load(f)

    # group satellites by orbit
    planes = {}
    for obj in data["instances"]:
        if obj["type"] != "Satellite":
            continue
        orbit = int(obj["extra"]["OrbitIndex"])
        planes.setdefault(orbit, []).append(obj)

    # sort planes
    sorted_planes = sorted(planes.keys())

    for i, orbit in enumerate(sorted_planes):
        raan = 25.0 + 5.0 * i   # ⭐ KEY CHANGE

        sats = planes[orbit]

        for sat in sats:
            extra = sat["extra"]

            # --- parse existing values ---
            tle2 = extra["TLE_2"].split()

            satnum = int(tle2[1])
            inc = float(tle2[2])
            ecc = float("0." + tle2[4])
            argp = float(tle2[5])
            M = float(tle2[6])
            n = float(tle2[7])

            # --- rebuild TLEs ---
            extra["TLE_1"] = format_tle_line1(extra["TLE_1"])
            extra["TLE_2"] = format_tle_line2(
                satnum, inc, raan, ecc, argp, M, n
            )

    # write back
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    print(f"✔ Fixed RAAN spacing + TLE formatting + checksum: {filepath}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 fix_tle_raan_checksum.py <file.json>")
        sys.exit(1)

    main(sys.argv[1])