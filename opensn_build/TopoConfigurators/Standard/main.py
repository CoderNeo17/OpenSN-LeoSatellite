from opensn.operator.emulator_operator import EmulatorOperator
from opensn.model.instance import Instance
from opensn.model.position import Position
from opensn.const.dict_fields import (
    PARAMETER_KEY_CONNECT, PARAMETER_KEY_DELAY,
    PARAMETER_KEY_BANDWIDTH, PARAMETER_KEY_LOSS,
    PARAMETER_KEY_UPLINK_BANDWIDTH, PARAMETER_KEY_DOWNLINK_BANDWIDTH
)
from opensn.model.link import LinkBase
from opensn.utils.tools import dec2ra
from config import ADDR, PORT
from datetime import datetime, timedelta
from trajectory import calculate_postion, distance_meter, select_closest_satellite, get_propagation_delay_s
from instance_types import *
from address_type import LINK_V4_ADDR_KEY
from address_allocator import alloc_ipv4, format_ipv4
from link_model import *
from route_computer import write_topology
from loguru import logger
from concurrent.futures import ThreadPoolExecutor
import json, math, time
import os

STEP_SECOND = 0.5
TOPO_PATH   = "/home/psbabhishek/OpenSN-Library/opensn_build/opensn-daemon/topo/topology.json"

polar_threshold = dec2ra(66.5)
fetch_pool = ThreadPoolExecutor(max_workers=32)


# ---------------------------------------------------------------------------
# Cache refresh helpers — surgical etcd reads for only affected instances
# ---------------------------------------------------------------------------

os.makedirs(os.path.dirname(TOPO_PATH), exist_ok=True)

def refresh_instance(cli, instance_id, all_instance_map):
    """Re-fetch one instance from etcd and update the cache in place."""
    node_index = all_instance_map[instance_id].node_index
    updated = cli.get_instance(node_index, instance_id)
    all_instance_map[instance_id] = updated
    return updated


def refresh_links_for_node(cli, node_index, node_link_map):
    """Re-fetch all links for one node and update the cache in place."""
    link_map = cli.get_link_map(node_index)
    node_link_map[node_index] = {
        link_id: link_info
        for link_id, link_info in link_map.items()
        if link_info.address_infos
        and link_info.address_infos[0] is not None
        and LINK_V4_ADDR_KEY in link_info.address_infos[0]
        and LINK_V4_ADDR_KEY in link_info.address_infos[1]
    }


# ---------------------------------------------------------------------------
# Config generation — uses in-memory cache, zero etcd reads.
# Only call this AFTER the relevant entries in all_instance_map and
# node_link_map have been refreshed to reflect current etcd state.
# ---------------------------------------------------------------------------

def generate_config(instance_id, all_instance_map, node_link_map):
    instance_info = all_instance_map[instance_id]
    config_map = {
        "instance_id": instance_id,
        "type":        instance_info.type,
        "link_infos":  {},
        "end_infos":   {},
    }
    if instance_info.type == TYPE_SATELLITE:
        config_map['area'] = instance_info.extra[EX_AREA_KEY]

    node_links = node_link_map.get(instance_info.node_index, {})
    # logger.debug(f"[GENCONFIG] {instance_id} node_index={instance_info.node_index} "
    #              f"connections={list(instance_info.connections.keys())} "
    #              f"node_links available={list(node_links.keys())}")

    for link_id, conn in instance_info.connections.items():
        if link_id not in node_links:
            # logger.debug(f"[GENCONFIG] {instance_id} link {link_id} not in node_link_map — skipping")
            continue
        link_info = node_links[link_id]
        instance_index = next(
            (i for i, e in enumerate(link_info.end_infos)
             if e.instance_id == instance_id), -1
        )
        if instance_index < 0:
            # logger.debug(f"[GENCONFIG] {instance_id} not found in end_infos for link {link_id} — skipping")
            continue
        other_id = link_info.end_infos[1 - instance_index].instance_id
        other_instance = all_instance_map.get(other_id)
        if other_instance is None:
            # logger.debug(f"[GENCONFIG] other instance {other_id} not in all_instance_map — skipping")
            continue

        config_map["link_infos"][link_id] = {
            **link_info.address_infos[instance_index],
            "delay_ms": link_info.parameter.get(PARAMETER_KEY_DELAY, 0) / 1000
        }
        config_map["end_infos"][link_id] = {
            "instance_id": conn.instance_id,
            "type":        conn.instance_type,
        }
        if other_instance.type == TYPE_SATELLITE:
            config_map["end_infos"][link_id]['area'] = other_instance.extra[EX_AREA_KEY]

    # logger.debug(f"[GENCONFIG] {instance_id} result link_infos={list(config_map['link_infos'].keys())}")
    return config_map


# ---------------------------------------------------------------------------
# Handover
# ---------------------------------------------------------------------------

# ----------------------------------------------------------------
# GSL handover — returns affected ids, does NOT write configs
# ----------------------------------------------------------------
def handle_gsl_handover(cli, node, node_type_label, position_map,
                        all_instance_map, node_link_map) -> set:
    if not node.start:
        return set()

    satellite_id, change = select_closest_satellite(node, position_map, all_instance_map)
    if not change:
        return set()

    address1 = {}
    address2 = {}
    old_sat_id = ""
    old_sat_node_index = None

    old_link_id = ""
    for key in node.connections.keys():
        if node.connections[key].instance_type == TYPE_SATELLITE:
            old_link_id = key
            break

    if old_link_id != "":
        old_sat_id = node.connections[old_link_id].instance_id
        old_sat_node_index = node.connections[old_link_id].end_node_index
        old_link = cli.disable_link_between(
            node.node_index, node.instance_id,
            old_sat_node_index, old_sat_id
        )
        logger.info("[%s] Switch %s from %s to %s" % (
            node_type_label, node.instance_id, old_sat_id, satellite_id
        ))
        if len(old_link) > 0:
            address1 = old_link[old_link_id].address_infos[0]
            address2 = old_link[old_link_id].address_infos[1]
    else:
        subnet = None
        if node.type == TYPE_GROUND_STATION:
            subnet = alloc_ipv4(30, pool="gsl")
        elif node.type == TYPE_GROUND_TERMINAL:
            subnet = alloc_ipv4(30, pool="ut")
        address1 = {LINK_V4_ADDR_KEY: format_ipv4(subnet[1], 30)}
        address2 = {LINK_V4_ADDR_KEY: format_ipv4(subnet[2], 30)}
        logger.info("[%s] Switch %s from None to %s" % (
            node_type_label, node.instance_id, satellite_id
        ))

    new_sat_node_index = all_instance_map[satellite_id].node_index
    cli.enable_link_between(
        node.node_index, node.instance_id,
        new_sat_node_index, satellite_id,
        address_info1=address1,
        address_info2=address2,
    )

    affected_ids = {node.instance_id, satellite_id}
    affected_node_indexes = {node.node_index, new_sat_node_index}
    if old_sat_id:
        affected_ids.add(old_sat_id)
        affected_node_indexes.add(old_sat_node_index)

    inst_futures = [
        fetch_pool.submit(refresh_instance, cli, iid, all_instance_map)
        for iid in affected_ids
    ]
    link_futures = [
        fetch_pool.submit(refresh_links_for_node, cli, ni, node_link_map)
        for ni in affected_node_indexes
    ]
    for f in inst_futures + link_futures:
        f.result()

    return affected_ids  # caller writes configs after link params are updated


def anchor_setup(cli, gs, anc, all_instance_map, node_link_map):
    subnet = alloc_ipv4(30, pool="anchor")
    cli.enable_link_between(
        anc.node_index, anc.instance_id,
        gs.node_index,  gs.instance_id,
        address_info1={LINK_V4_ADDR_KEY: format_ipv4(subnet[1], 30)},
        address_info2={LINK_V4_ADDR_KEY: format_ipv4(subnet[2], 30)},
    )

    logger.debug(f"Anchor setup: linked {anc.instance_id} to {gs.instance_id}, refreshing cache and writing configs")

    # Refresh cache for anchor and gs after link creation
    for iid in [gs.instance_id, anc.instance_id]:
        refresh_instance(cli, iid, all_instance_map)
    for ni in {gs.node_index, anc.node_index}:
        refresh_links_for_node(cli, ni, node_link_map)

    for iid, node_index in [(gs.instance_id, gs.node_index), (anc.instance_id, anc.node_index)]:
        config = generate_config(iid, all_instance_map, node_link_map)
        cli.put_instance_config_async(node_index, iid, json.dumps(config))

    logger.info("Linked anchor %s <-> ground station %s" % (anc.instance_id, gs.instance_id))


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    cli = EmulatorOperator(ADDR, PORT)

    SIM_START   = datetime(2026, 3, 1, 10, 58, 28)
    sim_elapsed = 0
    started     = False
    anchored    = False
    anchor_node: Instance = None
    address_map = {}
    config_written: set[str] = set()
    total = 0

    while True:
        t0 = time.perf_counter()

        # ----------------------------------------------------------------
        # Fetch node list, instance maps, link maps — all in parallel
        # ----------------------------------------------------------------
        node_list = cli.get_node_map()

        inst_futures = {ni: fetch_pool.submit(cli.get_instance_map, ni) for ni in node_list}
        link_futures = {ni: fetch_pool.submit(cli.get_link_map,     ni) for ni in node_list}

        all_instance_map:    dict[str, Instance]          = {}
        ground_station_list: list[Instance]               = []
        user_terminal_list:  list[Instance]               = []

        for node_index, fut in inst_futures.items():
            for instance_id, instance in fut.result().items():
                all_instance_map[instance_id] = instance
                if instance.type == TYPE_GROUND_STATION:
                    ground_station_list.append(instance)
                elif instance.type == TYPE_GROUND_TERMINAL:
                    user_terminal_list.append(instance)
                elif instance.type == TYPE_ANCHOR_NODE:
                    anchor_node = instance

        node_link_map: dict[int, dict[str, LinkBase]] = {}
        for node_index, fut in link_futures.items():
            node_link_map[node_index] = {}
            for link_id, link_info in fut.result().items():
                if link_info.address_infos[0] is None:
                    continue
                if LINK_V4_ADDR_KEY not in link_info.address_infos[0] or \
                   LINK_V4_ADDR_KEY not in link_info.address_infos[1]:
                    if link_id not in address_map:
                        address_map[link_id] = alloc_ipv4(30)
                    subnet = address_map[link_id]
                    link_info.address_infos = [
                        {LINK_V4_ADDR_KEY: format_ipv4(subnet[1], 30)},
                        {LINK_V4_ADDR_KEY: format_ipv4(subnet[2], 30)}
                    ]
                    cli.put_link_async(link_info)
                node_link_map[node_index][link_id] = link_info

        t_fetch = time.perf_counter()

        # ----------------------------------------------------------------
        # Positions — fire all async
        # ----------------------------------------------------------------
        position_map: dict[str, Position] = {"": Position()}
        time_now = SIM_START + timedelta(seconds=sim_elapsed)

        for instance_id, instance_info in all_instance_map.items():
            if instance_info.type in [TYPE_GROUND_STATION, TYPE_GROUND_TERMINAL, TYPE_ANCHOR_NODE]:
                new_pos = Position()
                new_pos.latitude  = float(instance_info.extra.get(EX_LATITUDE_KEY,  0)) / 180 * math.pi
                new_pos.longitude = float(instance_info.extra.get(EX_LONGITUDE_KEY, 0)) / 180 * math.pi
                new_pos.altitude  = float(instance_info.extra.get(EX_ALTITUDE_KEY,  0))
            elif instance_info.start:
                new_pos = calculate_postion(instance_info, time_now)
                started = True
            else:
                new_pos = Position()
            position_map[instance_id] = new_pos
            fetch_pool.submit(cli.put_position, instance_id, new_pos)

        if started:
            sim_elapsed += total

        t_pos = time.perf_counter()

        # ----------------------------------------------------------------
        # Anchor setup (once)
        # ----------------------------------------------------------------
        if started and not anchored and anchor_node is not None:
            for gs in ground_station_list:
                anchor_setup(cli, gs, anchor_node, all_instance_map, node_link_map)
            anchored = True

        # ----------------------------------------------------------------
        # GSL handover
        # ----------------------------------------------------------------
        handover_ids: set[str] = set()

        for gs in ground_station_list:
            handover_ids |= handle_gsl_handover(cli, gs, "GS", position_map, all_instance_map, node_link_map)

        for ut in user_terminal_list:
            handover_ids |= handle_gsl_handover(cli, ut, "UT", position_map, all_instance_map, node_link_map)

        t_handover = time.perf_counter()

        write_topology(all_instance_map, node_link_map, TOPO_PATH)

        t_topowrite = time.perf_counter()

        # ----------------------------------------------------------------
        # Link parameter updates
        # ----------------------------------------------------------------
        for node_index, link_map in node_link_map.items():
            for link_id, link_info in link_map.items():
                if link_info.parameter is None:
                    link_info.parameter = {}
                end0 = link_info.end_infos[0]
                end1 = link_info.end_infos[1]
                if not end0.instance_id or not end1.instance_id:
                    continue
                if not link_info.enable:
                    continue

                if end0.instance_type == TYPE_SATELLITE and \
                   end1.instance_type == TYPE_SATELLITE and \
                   all_instance_map[end1.instance_id].extra[EX_ORBIT_INDEX] != \
                   all_instance_map[end0.instance_id].extra[EX_ORBIT_INDEX] and \
                   (abs(position_map[end0.instance_id].latitude) > polar_threshold or
                    abs(position_map[end1.instance_id].latitude) > polar_threshold):
                    link_info.parameter[PARAMETER_KEY_CONNECT] = 0
                else:
                    link_info.parameter[PARAMETER_KEY_CONNECT] = 1

                if not end0.instance_type:
                    continue

                distance = distance_meter(
                    position_map[end0.instance_id],
                    position_map[end1.instance_id]
                )
                delay = int(get_propagation_delay_s(distance) * 1_000_000)
                if end0.instance_type == TYPE_ANCHOR_NODE or end1.instance_type == TYPE_ANCHOR_NODE:
                    delay = 0
                link_info.parameter[PARAMETER_KEY_DELAY] = delay

                elev = dist = 0
                if end0.instance_type != TYPE_SATELLITE or end1.instance_type != TYPE_SATELLITE:
                    sat_pos, gs_pos = (position_map[end0.instance_id], position_map[end1.instance_id]) \
                        if end0.instance_type == TYPE_SATELLITE \
                        else (position_map[end1.instance_id], position_map[end0.instance_id])
                    elev = elevation_angle(gs_pos, sat_pos)
                    dist = distance_meter(gs_pos, sat_pos)

                end0_type = end0.instance_type
                end1_type = end1.instance_type
                is_gsl_up   = (end0_type in [TYPE_GROUND_STATION, TYPE_GROUND_TERMINAL] and end1_type == TYPE_SATELLITE)
                is_gsl_down = (end0_type == TYPE_SATELLITE and end1_type in [TYPE_GROUND_STATION, TYPE_GROUND_TERMINAL])

                if is_gsl_up:
                    link_info.parameter[PARAMETER_KEY_UPLINK_BANDWIDTH]   = gsl_bandwidth_up(elev, dist)
                    link_info.parameter[PARAMETER_KEY_DOWNLINK_BANDWIDTH] = gsl_bandwidth_down(elev, dist)
                    link_info.parameter[PARAMETER_KEY_LOSS]               = gsl_loss(elev, dist)
                elif is_gsl_down:
                    link_info.parameter[PARAMETER_KEY_UPLINK_BANDWIDTH]   = gsl_bandwidth_down(elev, dist)
                    link_info.parameter[PARAMETER_KEY_DOWNLINK_BANDWIDTH] = gsl_bandwidth_up(elev, dist)
                    link_info.parameter[PARAMETER_KEY_LOSS]               = gsl_loss(elev, dist)
                else:
                    link_info.parameter[PARAMETER_KEY_BANDWIDTH] = 1_000_000_000
                    link_info.parameter[PARAMETER_KEY_LOSS]      = 20

                cli.put_link_parameter_async(link_info.node_index, link_info.link_id, link_info.parameter)

        t_linkparams = time.perf_counter()

        # ----------------------------------------------------------------
        # Instance configs
        # On first tick after start: write all instances once.
        # On handover ticks: write only the 3 affected nodes.
        # All other ticks: skip.
        # ----------------------------------------------------------------
        # ----------------------------------------------------------------
        # Instance configs
        # ----------------------------------------------------------------
        if started and not config_written:
            # logger.debug(f"[CONFIG] Initial write — {len(all_instance_map)} instances")
            for instance_id, instance_info in all_instance_map.items():
                if not instance_info.start and \
                   instance_info.type not in [TYPE_GROUND_STATION, TYPE_GROUND_TERMINAL, TYPE_ANCHOR_NODE]:
                    # logger.debug(f"[CONFIG] Skipping {instance_id} (not started, type={instance_info.type})")
                    continue
                config_map = generate_config(instance_id, all_instance_map, node_link_map)
                # logger.debug(f"[CONFIG] Writing initial config for {instance_id} type={instance_info.type} config={json.dumps(config_map)}")
                cli.put_instance_config_async(instance_info.node_index, instance_id, json.dumps(config_map))
            config_written = True
            # logger.debug(f"[CONFIG] Initial write done, config_written=True")

        elif handover_ids:
            # logger.debug(f"[CONFIG] Handover write — affected ids={handover_ids}")
            for instance_id in handover_ids:
                instance_info = all_instance_map.get(instance_id)
                if instance_info is None:
                    # logger.debug(f"[CONFIG] {instance_id} not found in all_instance_map, skipping")
                    continue
                config_map = generate_config(instance_id, all_instance_map, node_link_map)
                # logger.debug(f"[CONFIG] Writing handover config for {instance_id} type={instance_info.type} config={json.dumps(config_map)}")
                cli.put_instance_config_async(instance_info.node_index, instance_id, json.dumps(config_map))

        else:
            pass
            # logger.debug(f"[CONFIG] Skipping — started={started} config_written={config_written} handover_ids={handover_ids}")

        t_end = time.perf_counter()

        # ----------------------------------------------------------------
        # Timing breakdown
        # ----------------------------------------------------------------
        total = t_end - t0
        # logger.info(
        #     f"tick={sim_elapsed:.0f}s total={total*1000:.0f}ms | "
        #     f"fetch={(t_fetch - t0) * 1000:.0f}ms "
        #     f"pos={(t_pos - t_fetch) * 1000:.0f}ms "
        #     f"handover={(t_handover - t_pos) * 1000:.0f}ms "
        #     f"linkparams={(t_linkparams - t_handover) * 1000:.0f}ms "
        #     f"configs={(t_end - t_linkparams) * 1000:.0f}ms"
        # )

        remaining = STEP_SECOND - total
        if remaining > 0:
            time.sleep(remaining)
        else:
            pass
            # logger.warning(f"Tick overran by {-remaining*1000:.0f}ms")