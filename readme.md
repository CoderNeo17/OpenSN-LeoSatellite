# OpenSN-VideoStream

LEO satellite network emulation framework extended for **video streaming experiments over dynamic satellite topologies**.

This project modifies **OpenSN**, an open-source emulator for Low Earth Orbit (LEO) satellite networks, to support **end-to-end video streaming workloads**, enabling evaluation of streaming performance under dynamic satellite routing conditions.

## Overview

This repository extends OpenSN with support for:

* Video streaming applications running inside emulated network nodes
* Streaming traffic generation across LEO satellite topologies
* Evaluation of streaming performance under changing link conditions
* End-to-end experiments involving satellites, ground stations, and streaming endpoints
* Network measurements such as latency, throughput, interruptions, and route changes during video transmission

The emulator enables experimentation with real application traffic instead of only synthetic network workloads.


## Attribution

This project is based on **OpenSN**, introduced in:

```bibtex
@ARTICLE{11021408,
  author={Lu, Wenhao and Wang, Zhiyuan and Zhang, Hefan and Zhang, Shan and Luo, Hongbin},
  journal={IEEE Transactions on Parallel and Distributed Systems},
  title={OpenSN: An Open Source Library for Emulating LEO Satellite Networks},
  year={2025},
  volume={36},
  number={8},
  pages={1574-1590},
  doi={10.1109/TPDS.2025.3575920}
}
```

Original project: OpenSN

Our work extends the framework toward **video streaming over emulated LEO networks**.


## Environment Setup

Install Docker:

```bash
sudo apt install docker.io
```

Recommended version:

```text
Docker version 24.0.5
```

Required dependency services:

* Etcd
* InfluxDB
* CodeServer (optional)


## Running the Emulator

Start dependency services.

Run daemon:

```bash
sudo ./NodeDaemon
```

Open the web console:

```text
http://<master_ip>:8080
```

Upload topology and experiment configuration files.

Start the topology controller and launch video streaming workloads inside the selected nodes.


## Example Workflow

1. Deploy LEO constellation topology
2. Launch satellite and ground station containers
3. Start video sender node
4. Start receiver node
5. Stream video through emulated satellite paths
6. Measure:

* Throughput
* Delay
* Packet loss
* Route transitions
* Stream interruptions


## Research Applications

This framework can be used for:

* Video delivery over satellite constellations
* QoS analysis in LEO networks
* Adaptive streaming evaluation
* Routing impact on media transmission
* Ground station handoff analysis
* Application-level testing over dynamic topologies