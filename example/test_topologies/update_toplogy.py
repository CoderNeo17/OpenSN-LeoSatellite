import json, sys, datetime

def tle_checksum(line):
    total = 0
    for c in line[:68]:
        if c.isdigit():
            total += int(c)
        elif c == '-':
            total += 1
    return total % 10

def get_tle_epoch_today():
    now = datetime.datetime.now(datetime.timezone.utc)
    year_2digit = now.year % 100
    day_of_year = now.timetuple().tm_yday
    fractional_day = (now.hour * 3600 + now.minute * 60 + now.second) / 86400
    return f"{year_2digit:02d}{day_of_year + fractional_day:012.8f}"

def update_config(input_path, output_path=None):
    with open(input_path) as f:
        data = json.load(f)
    new_epoch = get_tle_epoch_today()
    updated = 0
    for inst in data.get('instances', []):
        if inst.get('type') == 'Satellite':
            old_tle1 = inst['extra']['TLE_1']
            new_tle1 = old_tle1[:18] + f'{new_epoch:<14}' + old_tle1[32:68]
            inst['extra']['TLE_1'] = new_tle1 + str(tle_checksum(new_tle1))
            updated += 1
    out = output_path or input_path
    with open(out, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Updated {updated} satellites with epoch: {new_epoch}")
    print(f"Saved to: {out}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 update_tle_epoch.py <config.json> [output.json]")
        sys.exit(1)
    update_config(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
