import csv
from datetime import datetime, timedelta

class IperfTrace:
    """
    Loads an iperf CSV trace and provides bandwidth lookups by relative time.
    Loops the trace if the simulation outlasts it.
    """
    def __init__(self, csv_path: str):
        self.rows = []  # list of (rel_seconds, download_bps, upload_bps)
        self._load(csv_path)
        self._sim_start: datetime | None = None

    def _load(self, path: str):
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            base_time = None
            for row in reader:
                # Skip rows with missing bandwidth values
                if not row["download"].strip() or not row["upload"].strip():
                    continue
                ts = datetime.strptime(row["timestamp_start"], "%Y-%m-%d %H:%M:%S")
                if base_time is None:
                    base_time = ts
                rel = (ts - base_time).total_seconds()
                self.rows.append((rel, float(row["download"]), float(row["upload"])))
        if not self.rows:
            raise ValueError("iperf CSV is empty or has no valid rows")
        self._trace_duration = self.rows[-1][0]

    def start(self):
        """Call once at simulation start to anchor relative time."""
        self._sim_start = datetime.now()

    def get_bandwidth(self, now: datetime | None = None) -> tuple[int, int]:
        if self._sim_start is None:
            self.start()
        if now is None:
            now = datetime.now()

        sim_elapsed = (now - self._sim_start).total_seconds()

        # Loop: wrap within trace duration
        if self._trace_duration > 0:
            sim_elapsed = sim_elapsed % self._trace_duration

        # Find the last row whose relative timestamp <= sim_elapsed
        selected = self.rows[0]
        for row in self.rows:
            if row[0] <= sim_elapsed:
                selected = row
            else:
                break

        _, download_bps, upload_bps = selected
        return int(download_bps), int(upload_bps)