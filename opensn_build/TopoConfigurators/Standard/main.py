import time

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
from config import ADDR,PORT
from datetime import datetime, timedelta
from trajectory import calculate_postion,distance_meter,select_closest_satellite,get_propagation_delay_s
from instance_types import *
from address_type import LINK_V4_ADDR_KEY
from time import sleep
from address_allocator import alloc_ipv4,format_ipv4
from link_model import *
from loguru import logger
import json, math
from route_computer import write_topology
step_second = 1
from trace import IperfTrace

polar_threshold = dec2ra(66.5)

import subprocess

def flush_orphan_veths():
    result = subprocess.run(
        ["ip", "-j", "link", "show"],
        capture_output=True, text=True
    )
    links = json.loads(result.stdout)
    for link in links:
        if link.get("operstate") == "DOWN" and \
           link.get("link_type") == "ether" and \
           "link_index" in link and \
           link["ifindex"] != link.get("link_index"):
            # peer index exists in json but actual peer ns is gone
            name = link["ifname"]
            subprocess.run(["ip", "link", "del", name])

def genenrate_config(cli:EmulatorOperator,node_index:int,instance_id:str):
    instance_info = cli.get_instance(node_index,instance_id)
    config_map = {
        "instance_id": instance_id,
        "type": instance_info.type,   # included so container daemon knows its role
        "link_infos": {},
        "end_infos": {},
    }
    if instance_info.type == TYPE_SATELLITE:
        config_map['area'] = instance_info.extra[EX_AREA_KEY]
    for k,v in instance_info.connections.items():
        instance_index = -1
        link_info = cli.get_link(node_index,k)
        for end_index in range(len(link_info.end_infos)):
            if link_info.end_infos[end_index].instance_id == instance_id:
                instance_index = end_index
        if instance_index < 0:
            return {}
        another_instance_info = cli.get_instance(link_info.end_infos[1-instance_index].end_node_index,link_info.end_infos[1-instance_index].instance_id)
        config_map["link_infos"][k] = {
            **link_info.address_infos[instance_index],
            "delay_ms": link_info.parameter.get(PARAMETER_KEY_DELAY, 0) / 1000  # µs → ms
        }
        config_map["end_infos"][k] = {
            "instance_id": v.instance_id,
            "type": v.instance_type,
        }
        if another_instance_info.type == TYPE_SATELLITE:
            config_map["end_infos"][k]['area'] = another_instance_info.extra[EX_AREA_KEY]
    return config_map


def handle_gsl_handover(cli, node, node_type_label, position_map, all_instance_map):
    """
    Shared handover logic for both GroundStation and UserTerminal.
    Finds the nearest satellite and switches the GSL if it has changed.
    """
    if not node.start:
        return

    satellite_id, change = select_closest_satellite(
        node,
        position_map,
        all_instance_map
    )
    if not change:
        return

    address1 = {}
    address2 = {}

    old_sat_node_index = None
    new_sat_node_index = None

    old_link_id = ""
    for key in node.connections.keys():
        other_node_type = node.connections[key].instance_type
        if other_node_type == TYPE_SATELLITE:
            old_link_id = key
            old_sat_node_index = node.connections[key].end_node_index
            break

    if old_link_id != "":
        old_link = cli.disable_link_between(
            node.node_index,
            node.instance_id,
            node.connections[old_link_id].end_node_index,
            node.connections[old_link_id].instance_id
        )
        logger.info("[%s] Switch %s from %s to %s" % (
            node_type_label,
            node.instance_id,
            node.connections[old_link_id].instance_id,
            satellite_id
        ))
        old_sat_config = genenrate_config(
            cli,
            node.connections[old_link_id].end_node_index,
            node.connections[old_link_id].instance_id
        )
        cli.put_instance_config(
            node.connections[old_link_id].end_node_index,
            node.connections[old_link_id].instance_id,
            json.dumps(old_sat_config)
        )
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
            node_type_label,
            node.instance_id,
            satellite_id
        ))

    cli.enable_link_between(
        node.node_index,
        node.instance_id,
        all_instance_map[satellite_id].node_index,
        all_instance_map[satellite_id].instance_id,
        address_info1=address1,
        address_info2=address2,
    )
    new_sat_node_index = all_instance_map[satellite_id].node_index
    # Fresh fetch of only affected nodes — 2-3 etcd calls
    # Updates node_link_map in place for these nodes only
    affected_node_indexes = {node.node_index, new_sat_node_index}
    if old_sat_node_index is not None:
        affected_node_indexes.add(old_sat_node_index)
    for ni in affected_node_indexes:
        if ni is None:
            continue
        fresh = cli.get_link_map(ni)
        node_link_map[ni] = {
            link_id: li for link_id, li in fresh.items()
            if li.address_infos
            and li.address_infos[0] is not None
            and LINK_V4_ADDR_KEY in li.address_infos[0]
        }

    node_config = genenrate_config(cli, node.node_index, node.instance_id)
    cli.put_instance_config(node.node_index, node.instance_id, json.dumps(node_config))
    sat_config = genenrate_config(cli, all_instance_map[satellite_id].node_index, all_instance_map[satellite_id].instance_id)
    cli.put_instance_config(all_instance_map[satellite_id].node_index, all_instance_map[satellite_id].instance_id, json.dumps(sat_config))


def anchor(gs,anc):
    subnet = alloc_ipv4(30, pool="anchor")
    cli.enable_link_between(
        anc.node_index,
        anc.instance_id,
        gs.node_index,
        gs.instance_id,
        address_info1={LINK_V4_ADDR_KEY: format_ipv4(subnet[1], 30)},
        address_info2={LINK_V4_ADDR_KEY: format_ipv4(subnet[2], 30)},
    )
    node_config = genenrate_config(cli, anc.node_index, anc.instance_id)
    cli.put_instance_config(anc.node_index, anc.instance_id, json.dumps(node_config))
    sat_config = genenrate_config(cli, gs.node_index, gs.instance_id)
    cli.put_instance_config(gs.node_index, gs.instance_id, json.dumps(sat_config))
    logger.info("Linked anchor %s <-> ground station %s" % (
        anc.instance_id, gs.instance_id
    ))

all_instance_map: dict[str,Instance] = {}
node_link_map: dict[int,dict[str,LinkBase]] = {}

if __name__ == "__main__":

    flush_orphan_veths()

    instance_config_updated:dict[str,str] = {}
    topo_path = "/home/psbabhishek/OpenSN-Library/opensn_build/opensn-daemon/topo/topology.json"
    cli = EmulatorOperator(ADDR,PORT)

    SIM_START = datetime(2026, 3, 1, 10, 58, 28)
    sim_elapsed = 0
    started = False
    anchored = False
    # trace = IperfTrace("trace.csv")
    # trace.start()
    t0 = time.perf_counter()
    while True:
        node_list = cli.get_node_map()
        all_instance_map = {}
        node_link_map = {}
        ground_station_list: list[Instance] = []
        user_terminal_list: list[Instance] = []          # NEW
        anchor_node : Instance = None

        for node_index,node in node_list.items():
            instance_map = cli.get_instance_map(node_index)
            for instance_id,instance in instance_map.items():
                all_instance_map[instance_id] = instance

                if instance.type == TYPE_GROUND_STATION:
                    ground_station_list.append(instance)
                    gs_position = Position()
                    gs_position.latitude = float(instance.extra[EX_LATITUDE_KEY]) / 180 * math.pi
                    gs_position.longitude = float(instance.extra[EX_LONGITUDE_KEY]) / 180 * math.pi
                    gs_position.altitude = float(instance.extra[EX_ALTITUDE_KEY])
                    cli.put_position(instance_id, gs_position)

                elif instance.type == TYPE_GROUND_TERMINAL:   # NEW
                    user_terminal_list.append(instance)
                    ut_position = Position()
                    ut_position.latitude = float(instance.extra[EX_LATITUDE_KEY]) / 180 * math.pi
                    ut_position.longitude = float(instance.extra[EX_LONGITUDE_KEY]) / 180 * math.pi
                    ut_position.altitude = float(instance.extra[EX_ALTITUDE_KEY])
                    cli.put_position(instance_id, ut_position)
                
                elif instance.type == TYPE_ANCHOR_NODE:   # NEW
                    anchor_node = instance
                    an_position = Position()
                    an_position.latitude = float(instance.extra[EX_LATITUDE_KEY]) / 180 * math.pi
                    an_position.longitude = float(instance.extra[EX_LONGITUDE_KEY]) / 180 * math.pi
                    an_position.altitude = float(instance.extra[EX_ALTITUDE_KEY])
                    cli.put_position(instance_id, an_position)

        position_map: dict[str,Position] = {"":Position()}
        time_now = SIM_START + timedelta(seconds=sim_elapsed)
        for instance_id,instance_info in all_instance_map.items():
            if instance_info.type in [TYPE_GROUND_STATION, TYPE_GROUND_TERMINAL]:   # NEW
                new_postion = Position()
                new_postion.latitude = float(instance_info.extra[EX_LATITUDE_KEY])/180 * math.pi if EX_LATITUDE_KEY in instance_info.extra.keys() else 0
                new_postion.longitude = float(instance_info.extra[EX_LONGITUDE_KEY])/180 * math.pi if EX_LONGITUDE_KEY in instance_info.extra.keys() else 0
                new_postion.altitude = float(instance_info.extra[EX_ALTITUDE_KEY]) if EX_ALTITUDE_KEY in instance_info.extra.keys() else 0
                cli.put_position(instance_id,new_postion)
            elif instance_info.start:
                new_postion = calculate_postion(instance_info,time_now)
                cli.put_position(instance_id,new_postion)
                started = True
            else:
                new_postion = Position()
                cli.put_position(instance_id,new_postion)
            position_map[instance_id] = new_postion

        if started and (not anchored) and (anchor_node is not None) :
            for gs in ground_station_list:
                anchor(gs,anchor_node)
            anchored = True

        address_map = {}
        for node_index,node in node_list.items():
            node_link_map[node_index] = {}
            link_map = cli.get_link_map(node_index)
            for link_id,link_info in link_map.items():
                if link_info.address_infos[0] is None:
                    continue
                if LINK_V4_ADDR_KEY not in link_info.address_infos[0] or \
                    LINK_V4_ADDR_KEY not in link_info.address_infos[1]:
                    if link_id not in address_map.keys():
                        address_map[link_id] = alloc_ipv4(30)
                    
                    subnet = address_map[link_id]
                    link_info.address_infos = [{
                        LINK_V4_ADDR_KEY: format_ipv4(subnet[1],30)
                    },
                    {
                        LINK_V4_ADDR_KEY: format_ipv4(subnet[2],30)
                    }]
                    cli.put_link(link_info)
                node_link_map[node_index][link_id] = link_info

        # Ground Station GSL handover
        for ground_station in ground_station_list:
            handle_gsl_handover(cli, ground_station, "GS", position_map, all_instance_map)

        # User Terminal GSL handover                       # NEW
        for user_terminal in user_terminal_list:
            handle_gsl_handover(cli, user_terminal, "UT", position_map, all_instance_map)

        # Write topology immediately — containers reroute within ~3ms
        write_topology(all_instance_map, node_link_map, topo_path)

        # Link parameter updates (delay, bandwidth, loss, polar cutoff)
        for node_index,link_map in node_link_map.items():
            for link_id,link_info in link_map.items():
                if link_info.parameter is None:
                    link_info.parameter = {}
                if link_info.end_infos[0].instance_id=="" or link_info.end_infos[1].instance_id == "":
                    continue
                if not link_info.enable:
                    continue
                if link_info.end_infos[0].instance_type == TYPE_SATELLITE and \
                    link_info.end_infos[1].instance_type == TYPE_SATELLITE and \
                    all_instance_map[link_info.end_infos[1].instance_id].extra[EX_ORBIT_INDEX] != \
                    all_instance_map[link_info.end_infos[0].instance_id].extra[EX_ORBIT_INDEX] and \
                    (abs(position_map[link_info.end_infos[0].instance_id].latitude) > polar_threshold or \
                    abs(position_map[link_info.end_infos[1].instance_id].latitude) > polar_threshold):
                        link_info.parameter[PARAMETER_KEY_CONNECT] = 0
                else:
                    link_info.parameter[PARAMETER_KEY_CONNECT] = 1

                if link_info.end_infos[0].instance_type == "":
                    continue

                distance = distance_meter(
                    position_map[link_info.end_infos[0].instance_id],
                    position_map[link_info.end_infos[1].instance_id]
                )
                delay = int(get_propagation_delay_s(distance)*1000000)
                if link_info.end_infos[0].instance_type == TYPE_ANCHOR_NODE or link_info.end_infos[1].instance_type == TYPE_ANCHOR_NODE:
                    delay = 0
                link_info.parameter[PARAMETER_KEY_DELAY] = delay
                pos1 = position_map[link_info.end_infos[0].instance_id]
                pos2 = position_map[link_info.end_infos[1].instance_id]

                # detect GSL
                elev = 0
                dist = 0
                if (
                    link_info.end_infos[0].instance_type != TYPE_SATELLITE or
                    link_info.end_infos[1].instance_type != TYPE_SATELLITE
                ):
                    # identify sat vs ground
                    if link_info.end_infos[0].instance_type == TYPE_SATELLITE:
                        sat_pos, gs_pos = pos1, pos2
                    else:
                        sat_pos, gs_pos = pos2, pos1

                    elev = elevation_angle(gs_pos, sat_pos)
                    dist = distance_meter(gs_pos, sat_pos)
                end0_type = link_info.end_infos[0].instance_type
                end1_type = link_info.end_infos[1].instance_type
                is_gsl_up = (end0_type == TYPE_GROUND_STATION and end1_type == TYPE_SATELLITE) or \
                        (end0_type == TYPE_GROUND_TERMINAL and end1_type == TYPE_SATELLITE)
                is_gsl_down = (end0_type == TYPE_SATELLITE and end1_type == TYPE_GROUND_STATION) or \
                        (end0_type == TYPE_SATELLITE and end1_type == TYPE_GROUND_TERMINAL)

                if is_gsl_up:
                    # Example: 20 Mbps downlink (sat→ground), 5 Mbps uplink (ground→sat)
                    # End 0 is always satellite in your link model, so:
                    downlink_bps = gsl_bandwidth_down(elev, dist)
                    uplink_bps   = gsl_bandwidth_up(elev, dist)
                    link_info.parameter[PARAMETER_KEY_UPLINK_BANDWIDTH]   = uplink_bps   # 5 Mbps
                    link_info.parameter[PARAMETER_KEY_DOWNLINK_BANDWIDTH] = downlink_bps  # 20 Mbps
                    loss_ppm = gsl_loss(elev, dist)
                    link_info.parameter[PARAMETER_KEY_LOSS] = min(loss_ppm, 500)  # cap at 0.05%
                    # logger.info(f"Updated GSL bandwidth for link {link_id}: uplink {uplink_bps} bps, downlink {downlink_bps} bps")
                elif is_gsl_down:
                    # Example: 20 Mbps downlink (sat→ground), 5 Mbps uplink (ground→sat)
                    # End 0 is always satellite in your link model, so:
                    downlink_bps = gsl_bandwidth_up(elev, dist)
                    uplink_bps   = gsl_bandwidth_down(elev, dist)
                    link_info.parameter[PARAMETER_KEY_UPLINK_BANDWIDTH]   = uplink_bps   # 5 Mbps
                    link_info.parameter[PARAMETER_KEY_DOWNLINK_BANDWIDTH] = downlink_bps  # 20 Mbps
                    loss_ppm = gsl_loss(elev, dist)
                    link_info.parameter[PARAMETER_KEY_LOSS] = min(loss_ppm, 500)  # cap at 0.05%
                    # logger.info(f"Updated GSL bandwidth for link {link_id}: uplink {uplink_bps} bps, downlink {downlink_bps} bps")
                else:
                    # ISL: keep symmetric
                    link_info.parameter[PARAMETER_KEY_BANDWIDTH] = 1_000_000_000
                    link_info.parameter[PARAMETER_KEY_LOSS] = 0
                cli.put_link_parameter(link_info.node_index,link_info.link_id,link_info.parameter)

        for instance_id,instance_info in all_instance_map.items():
            if not instance_info.start:
                continue
            config_map = genenrate_config(cli,instance_info.node_index,instance_id)
            cli.put_instance_config_if_not_exist(instance_info.node_index,instance_id,json.dumps(config_map))
        
        t1 = time.perf_counter()
        if started:
            sim_elapsed += t1 - t0
        t0 = t1

        # sleep(step_second)