import math
import random


# -----------------------------
# CONFIG (tune these)
# -----------------------------
MAX_BW_UP = 15e6        # 15 Mbps peak
MAX_BW_DOWN = 150e6      # 150 Mbps peak
MIN_ELEV_DEG = 10     # cutoff
NOISE_LEVEL = 0.1     # ±10% variation


# -----------------------------
# BANDWIDTH MODEL
# -----------------------------
def gsl_bandwidth_up(elev_rad, distance_m):
    """
    Continuous bandwidth model for Ground-Satellite Links

    Args:
        elev_rad (float): elevation angle (radians)
        distance_m (float): distance (meters)

    Returns:
        int: bandwidth in bits per second
    """

    elev_deg = math.degrees(elev_rad)

    # --- cutoff ---
    if elev_deg < MIN_ELEV_DEG:
        return 0

    # --- elevation factor (dominant) ---
    elev_factor = math.sin(elev_rad)  # 0 → 1

    # --- distance factor (smooth decay) ---
    # scale ~2000 km
    dist_factor = 1 / (1 + (distance_m / 2e6) ** 2)

    # --- raw capacity ---
    capacity = MAX_BW_UP * elev_factor * dist_factor

    # --- saturation (prevents unrealistic scaling) ---
    capacity = capacity / (1 + capacity / MAX_BW_UP)

    # --- small randomness (time variation) ---
    noise = random.uniform(1 - NOISE_LEVEL, 1 + NOISE_LEVEL)

    return int(capacity * noise)

def gsl_bandwidth_down(elev_rad, distance_m):
    """
    Continuous bandwidth model for Ground-Satellite Links

    Args:
        elev_rad (float): elevation angle (radians)
        distance_m (float): distance (meters)

    Returns:
        int: bandwidth in bits per second
    """

    elev_deg = math.degrees(elev_rad)

    # --- cutoff ---
    if elev_deg < MIN_ELEV_DEG:
        return 0

    # --- elevation factor (dominant) ---
    elev_factor = math.sin(elev_rad)  # 0 → 1

    # --- distance factor (smooth decay) ---
    # scale ~2000 km
    dist_factor = 1 / (1 + (distance_m / 2e6) ** 2)

    # --- raw capacity ---
    capacity = MAX_BW_DOWN * elev_factor * dist_factor

    # --- saturation (prevents unrealistic scaling) ---
    capacity = capacity / (1 + capacity / MAX_BW_DOWN)

    # --- small randomness (time variation) ---
    noise = random.uniform(1 - NOISE_LEVEL, 1 + NOISE_LEVEL)

    return int(capacity * noise)


# -----------------------------
# OPTIONAL: TIME-CORRELATED NOISE
# (use this instead of random if you want smoother variation)
# -----------------------------
def smooth_noise(t, scale=0.1):
    """
    Smooth sinusoidal variation over time
    """
    return 1 + scale * math.sin(t / 30.0)


def gsl_bandwidth_smooth(elev_rad, distance_m, time_s):
    elev_deg = math.degrees(elev_rad)

    if elev_deg < MIN_ELEV_DEG:
        return 0

    elev_factor = math.sin(elev_rad)
    dist_factor = 1 / (1 + (distance_m / 2e6) ** 2)

    capacity = MAX_BW_UP * elev_factor * dist_factor
    capacity = capacity / (1 + capacity / MAX_BW_UP)

    return int(capacity * smooth_noise(time_s))


EARTH_RADIUS = 6371000  # meters


def elevation_angle(gs_pos, sat_pos):
    """
    Approximate elevation angle

    gs_pos, sat_pos: Position objects with lat, lon (rad), altitude (m)
    """

    # convert spherical to Cartesian
    def to_xyz(pos):
        r = EARTH_RADIUS + pos.altitude
        x = r * math.cos(pos.latitude) * math.cos(pos.longitude)
        y = r * math.cos(pos.latitude) * math.sin(pos.longitude)
        z = r * math.sin(pos.latitude)
        return (x, y, z)

    gx, gy, gz = to_xyz(gs_pos)
    sx, sy, sz = to_xyz(sat_pos)

    # vector GS → SAT
    vx, vy, vz = sx - gx, sy - gy, sz - gz

    # normalize
    v_mag = math.sqrt(vx*vx + vy*vy + vz*vz)
    vx, vy, vz = vx / v_mag, vy / v_mag, vz / v_mag

    # GS normal vector
    nx, ny, nz = gx, gy, gz
    n_mag = math.sqrt(nx*nx + ny*ny + nz*nz)
    nx, ny, nz = nx / n_mag, ny / n_mag, nz / n_mag

    # elevation = angle between LOS and local horizon
    dot = vx*nx + vy*ny + vz*nz
    elev = math.asin(dot)

    return elev

def gsl_loss(elev_rad, distance_m):
    """
    Continuous loss model (ppm = parts per million)
    """

    elev_deg = math.degrees(elev_rad)

    # --- cutoff ---
    if elev_deg < 10:
        return 1000000  # effectively dead link

    # --- base loss (very low) ---
    loss = 20  # 0.002%

    # --- elevation penalty (dominant) ---
    # sharp degradation near horizon
    loss += int(2000 / (math.sin(elev_rad) + 0.05))

    # --- distance penalty ---
    loss += int(distance_m / 10000)

    # --- mild randomness (not too noisy) ---
    loss = int(loss * random.uniform(0.85, 1.15))

    return loss