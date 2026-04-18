#!/usr/bin/env python3

import sys
import os


def compute_checksum(line: str) -> int:
    total = 0
    for c in line[:68]:  # Only first 68 characters
        if c.isdigit():
            total += int(c)
        elif c == '-':
            total += 1
    return total % 10


def fix_line(line: str) -> str:
    line = line.rstrip("\n")

    # Ensure line is at least 69 chars
    if len(line) < 69:
        line = line.ljust(69)

    checksum = compute_checksum(line)

    # Replace last character (column 69)
    return line[:68] + str(checksum)


def fix_file_inplace(filepath: str):
    if not os.path.isfile(filepath):
        print(f"Error: File not found -> {filepath}")
        sys.exit(1)

    with open(filepath, "r") as f:
        lines = f.readlines()

    fixed_lines = []
    for line in lines:
        stripped = line.rstrip("\n")

        if stripped.startswith("1 ") or stripped.startswith("2 "):
            fixed_lines.append(fix_line(stripped))
        else:
            fixed_lines.append(stripped)

    # Write back (in-place)
    with open(filepath, "w") as f:
        for line in fixed_lines:
            f.write(line + "\n")

    print(f"✔ Checksums fixed in-place for: {filepath}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 fix_tle_checksum.py <tle_file>")
        sys.exit(1)

    filepath = sys.argv[1]
    fix_file_inplace(filepath)


if __name__ == "__main__":
    main()