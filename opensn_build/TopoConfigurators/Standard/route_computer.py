"""
route_computer.py — call write_topology() once per tick after all link params updated.

Python side is now topology-only. No Dijkstra, no ut_routes.
Each Go container runs one Dijkstra from itself to find next-hops
toward all UTs and the anchor in a single pass.
"""

import json, os, tempfile
from address_type import LINK_V4_ADDR_KEY
from instance_types import TYPE_GROUND_TERMINAL, TYPE_ANCHOR_NODE
from opensn.const.dict_fields import PARAMETER_KEY_CONNECT, PARAMETER_KEY_DELAY
from loguru import logger

_tick = 0


def _collect_nodes(all_instance_map):
    nodes = {}
    for instance_id, instance in all_instance_map.items():
        node = {"type": instance.type}
        # Embed UT fixed IP directly in node info so containers
        # know the route destination without any extra lookup
        if instance.type == TYPE_GROUND_TERMINAL:
            node["ip"] = instance.extra.get("ip", "")
        nodes[instance_id] = node
    return nodes


def _collect_links(node_link_map):
    links = []
    seen = set()
    for node_index, link_map in node_link_map.items():
        for link_id, link_info in link_map.items():
            if link_id in seen:
                continue
            seen.add(link_id)
            end0 = link_info.end_infos[0]
            end1 = link_info.end_infos[1]
            if not end0.instance_id or not end1.instance_id:
                continue
            if not getattr(link_info, 'enable', True):
                continue
            param = link_info.parameter or {}
            if param.get(PARAMETER_KEY_CONNECT, 1) == 0:
                continue
            ai = link_info.address_infos
            if not ai or len(ai) < 2 or not ai[0] or not ai[1]:
                continue
            if LINK_V4_ADDR_KEY not in ai[0] or LINK_V4_ADDR_KEY not in ai[1]:
                continue
            weight = param.get(PARAMETER_KEY_DELAY, 1)
            if weight <= 0:
                weight = 1
            links.append({
                "a":      end0.instance_id,
                "b":      end1.instance_id,
                "a_ip":   ai[0][LINK_V4_ADDR_KEY].split('/')[0],
                "b_ip":   ai[1][LINK_V4_ADDR_KEY].split('/')[0],
                "weight": weight
            })
    return links


def _write_topo(topo, topo_path):
    dir_name = os.path.dirname(topo_path) or "."
    os.makedirs(dir_name, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=dir_name, delete=False, suffix='.tmp') as f:
        json.dump(topo, f)
        tmp = f.name
    os.replace(tmp, topo_path)


def write_topology(all_instance_map, node_link_map, topo_path="/routes/topology.json"):
    global _tick
    _tick += 1
    nodes = _collect_nodes(all_instance_map)
    links = _collect_links(node_link_map)
    _write_topo({"tick": _tick, "nodes": nodes, "links": links}, topo_path)
    logger.debug(
        f"[RouteComputer] tick={_tick} nodes={len(nodes)} links={len(links)}"
    )
