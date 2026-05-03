"""
route_computer.py

Single function: write_topology(all_instance_map, node_link_map, topo_path)

Call this AFTER link parameter updates, BEFORE config writes.
Writes a single topology JSON file. Each container's Go daemon reads it
and runs Dijkstra from itself to find routes to all UTs and anchor.

node_link_map may be stale on handover ticks — this is acceptable.
The container daemon will get fresh routes on the next tick (~1s).
The handover itself is handled by the container's interface watcher
reacting to the topo config file, which is written synchronously
via genenrate_config + put_instance_config inside handle_gsl_handover.
So interface comes up correctly even if route lags by one tick.
"""

import json, os, tempfile
from address_type import LINK_V4_ADDR_KEY
from opensn.const.dict_fields import PARAMETER_KEY_CONNECT, PARAMETER_KEY_DELAY
from loguru import logger

_tick = 0


def write_topology(all_instance_map, node_link_map, topo_path="/routes/topology.json"):
    global _tick
    _tick += 1

    # Nodes — just type, no IP (IPs are in links)
    nodes = {iid: {"type": inst.type} for iid, inst in all_instance_map.items()}

    # Links — only active, enabled, addressed links
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
            if not link_info.enable:
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

    topo = {"tick": _tick, "nodes": nodes, "links": links}

    dir_name = os.path.dirname(topo_path) or "."
    os.makedirs(dir_name, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=dir_name, delete=False, suffix='.tmp') as f:
        json.dump(topo, f)
        tmp = f.name
    os.replace(tmp, topo_path)

    # logger.debug(f"[RouteComputer] tick={_tick} nodes={len(nodes)} links={len(links)}")
