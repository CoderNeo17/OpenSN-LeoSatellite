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
from datetime import datetime
from trajectory import calculate_postion,distance_meter,select_closest_satellite,get_propagation_delay_s
from instance_types import TYPE_GROUND_STATION, TYPE_SATELLITE, TYPE_GROUND_TERMINAL, EX_ORBIT_INDEX,EX_ALTITUDE_KEY,EX_LATITUDE_KEY,EX_LONGITUDE_KEY, EX_AREA_KEY
from address_type import LINK_V4_ADDR_KEY
from time import sleep
from address_allocator import alloc_ipv4,format_ipv4
from loguru import logger
import json, math
step_second = 5

polar_threshold = dec2ra(66.5)

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
        config_map["link_infos"][k] = link_info.address_infos[instance_index]
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

    old_link_id = ""
    for key in node.connections.keys():
        old_link_id = key
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
        subnet = alloc_ipv4(30)
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
    node_config = genenrate_config(cli, node.node_index, node.instance_id)
    cli.put_instance_config(node.node_index, node.instance_id, json.dumps(node_config))
    sat_config = genenrate_config(cli, all_instance_map[satellite_id].node_index, all_instance_map[satellite_id].instance_id)
    cli.put_instance_config(all_instance_map[satellite_id].node_index, all_instance_map[satellite_id].instance_id, json.dumps(sat_config))


if __name__ == "__main__":

    instance_config_updated:dict[str,str] = {}
    
    cli = EmulatorOperator(ADDR,PORT)

    while True:
        node_list = cli.get_node_map()
        all_instance_map: dict[str,Instance] = {}
        node_link_map: dict[int,dict[str,LinkBase]] = {}
        ground_station_list: list[Instance] = []
        user_terminal_list: list[Instance] = []          # NEW

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

        address_map = {}
        for node_index,node in node_list.items():
            node_link_map[node_index] = {}
            link_map = cli.get_link_map(node_index)
            for link_id,link_info in link_map.items():
                if LINK_V4_ADDR_KEY not in link_info.address_infos[0] or \
                    LINK_V4_ADDR_KEY not in link_info.address_infos[1] is None:
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

        position_map: dict[str,Position] = {"":Position()}
        time_now = datetime.now()
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
            else:
                new_postion = Position()
                cli.put_position(instance_id,new_postion)
            position_map[instance_id] = new_postion

        # Ground Station GSL handover
        for ground_station in ground_station_list:
            handle_gsl_handover(cli, ground_station, "GS", position_map, all_instance_map)

        # User Terminal GSL handover                       # NEW
        for user_terminal in user_terminal_list:
            handle_gsl_handover(cli, user_terminal, "UT", position_map, all_instance_map)

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
                link_info.parameter[PARAMETER_KEY_DELAY] = delay
                end0_type = link_info.end_infos[0].instance_type
                end1_type = link_info.end_infos[1].instance_type
                is_gsl = (end0_type == TYPE_SATELLITE and end1_type == TYPE_GROUND_STATION) or \
                        (end0_type == TYPE_GROUND_STATION and end1_type == TYPE_SATELLITE)

                if is_gsl:
                    # Example: 20 Mbps downlink (sat→ground), 5 Mbps uplink (ground→sat)
                    # End 0 is always satellite in your link model, so:
                    link_info.parameter[PARAMETER_KEY_UPLINK_BANDWIDTH]   = 5_000_000   # 5 Mbps
                    link_info.parameter[PARAMETER_KEY_DOWNLINK_BANDWIDTH] = 20_000_000  # 20 Mbps
                    link_info.parameter[PARAMETER_KEY_BANDWIDTH] = 0
                else:
                    # ISL: keep symmetric
                    link_info.parameter[PARAMETER_KEY_BANDWIDTH] = 1_000_000
                link_info.parameter[PARAMETER_KEY_LOSS] = 150
                cli.put_link_parameter(link_info.node_index,link_info.link_id,link_info.parameter)

        for instance_id,instance_info in all_instance_map.items():
            if not instance_info.start:
                continue
            config_map = genenrate_config(cli,instance_info.node_index,instance_id)
            cli.put_instance_config_if_not_exist(instance_info.node_index,instance_id,json.dumps(config_map))

        sleep(step_second)