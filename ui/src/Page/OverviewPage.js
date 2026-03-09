import { Button, Descriptions, Divider, List } from "antd";
import { useEffect,useState, useRef} from "react"
import { Card, Typography, Badge, message } from "antd"
import { Cartesian3, Color,Cartesian2 } from "cesium"
import { Entity, PolylineGraphics, Viewer,PointGraphics, Label, LabelGraphics } from "resium";
import { AddTopology, GetEmulationConfig, ResetEmulation, StartEmulation, StopEmulation, UpdateInstanceType } from "../Request/emulation";
import { GetInstanceList } from "../Request/instance";
import { GetColorLink, GetLinkList, GetLinkParameterList } from "../Request/link";
import { GetNodeList } from "../Request/node";
import { GetAllPosition } from "../Request/position";
import { GetAllLinkLastResource, GetAllNodeResource } from "../Request/metrics";

  
export const Overview = () => {
    const typeInputRef = useRef(null);
    const topoInputRef = useRef(null);
    const [messageApi, contextHolder] = message.useMessage();
    const [running,setRunning] = useState(false)
    const [typeConfig,setTypeConfig] = useState({})
    const [resourcePercent,setResourcePercent] = useState("CPU:0% Memroy:0MB SwapMemory:0MB")
    const [instanceList,setInstanceList] = useState([])
    const [linkList,setLinkList] = useState([])
    const [nodeList,setNodeList] = useState([])
    const [instancePosition,setInstancePosition] = useState({})
    const [linkParameter,setLinkParameter] = useState({})
    const [linkColor,setColor] = useState({})
    useEffect(()=>{
        GetEmulationConfig((response)=>{
            setRunning(response.data.data.running)
            setTypeConfig(response.data.data.type_config?response.data.data.type_config:{})
        })
        GetNodeList((response)=>{
            setNodeList(response.data.data?response.data.data:[])
        })
        GetInstanceList((response)=>{
            setInstanceList(response.data.data?response.data.data:[])
        })
        GetLinkList((response)=>{
            setLinkList(response.data.data?response.data.data:[])
        })
        GetAllNodeResource((response)=>{
            let allCPU = 0
            let allMem = 0
            let allSwapMem = 0
            let resourceList = response.data.data
            resourceList.forEach((item)=>{
                allCPU += item.cpu_usage;
                allMem += item.mem_byte;
                allSwapMem += item.swap_mem_byte;
            })
            setResourcePercent(`CPU:${(allCPU*100).toFixed(2)}%\n Memory:${(allMem / (1<<20)).toFixed(2)}MB\n Swap Memory:${(allSwapMem / (1<<20)).toFixed(2)}MB`)
        })
        GetAllPosition((response)=>{
            setInstancePosition(response.data.data?response.data.data:{})
        })
        GetLinkParameterList((response)=>{
            setLinkParameter(response.data.data?response.data.data:{})
        })
        GetAllLinkLastResource((response)=>{
            let resourceList = response.data.data
            let maxThroughput = 0
            Object.keys(resourceList).forEach((item)=>{
                if (resourceList[item].send_bps + resourceList[item].recv_bps > maxThroughput) {
                    maxThroughput = resourceList[item].send_bps + resourceList[item].recv_bps
                }
            })
            let colorMap = {}
            Object.keys(resourceList).forEach((item)=>{
                let percent = maxThroughput===0?0:(resourceList[item].send_bps + resourceList[item].recv_bps) / maxThroughput
                let red = Math.floor(255 * percent)
                let green = 255 - red
                let color = Color.fromBytes(red,green,0,255)
                colorMap[item] = color
            })
            setColor(colorMap)
        })
        setInterval(()=>{
            GetEmulationConfig((response)=>{
                setRunning(response.data.data.running)
                setTypeConfig(response.data.data.type_config?response.data.data.type_config:{})
            })
            GetNodeList((response)=>{
                setNodeList(response.data.data?response.data.data:[])
            })
            GetInstanceList((response)=>{
                setInstanceList(response.data.data?response.data.data:[])
            })
            GetLinkList((response)=>{
                setLinkList(response.data.data?response.data.data:[])
            })
            GetAllNodeResource((response)=>{
                let allCPU = 0
                let allMem = 0
                let allSwapMem = 0
                let resourceList = response.data.data
                resourceList.forEach((item)=>{
                    allCPU += item.cpu_usage;
                    allMem += item.mem_byte;
                    allSwapMem += item.swap_mem_byte;
                })
                setResourcePercent(`CPU:${allCPU.toFixed(3)}%\n Memory:${(allMem / (1<<20)).toFixed(2)}MB\n Swap Memory:${(allSwapMem / (1<<20)).toFixed(2)}MB`)
            })
            GetAllPosition((response)=>{
                setInstancePosition(response.data.data?response.data.data:{})
            })
            GetLinkParameterList((response)=>{
                setLinkParameter(response.data.data?response.data.data:{})
            })
            
        },10000)
        setInterval(()=>{
            GetAllLinkLastResource((response)=>{
                let resourceList = response.data.data
                let maxThroughput = 0
                Object.keys(resourceList).forEach((item)=>{
                    if (resourceList[item].send_bps + resourceList[item].recv_bps > maxThroughput) {
                        maxThroughput = resourceList[item].send_bps + resourceList[item].recv_bps
                    }
                })
                let colorMap = {}
                Object.keys(resourceList).forEach((item)=>{
                    let percent = maxThroughput===0?0:(resourceList[item].send_bps + resourceList[item].recv_bps) / maxThroughput
                    let red = Math.floor(255 * percent)
                    let green = 255 - red
                    let color = Color.fromBytes(red,green,0,255)
                    colorMap[item] = color
                })
                setColor(colorMap)
            })
        },6000)
    },[])

    const items = [
        {
          key: 'emulation_status',
          label: 'Running Status',
          children: <p>
                {running?
                    <Badge status="success" text="Started" />:
                    <Badge status="default" text="Not Started" />    
                }
            </p>,
        },
        {
          key: 'cluster_num',
          label: 'Cluster Machine Count',
          children: <p>{nodeList?nodeList.length:0}</p>,
        },
        {
          key: 'instance_num',
          label: 'Simulated Network Node Count',
          children: <p>{instanceList?instanceList.length:0}</p>,
        },
        {
          key: 'link_num',
          label: 'Link Count',
          children: <p>{linkList?linkList.length:0}</p>,
        },
        {
          key: 'resource',
          label: 'Resource Utilization',
          children: <p>{resourcePercent}</p>,
        },
        {
            key: 'operation',
            label: 'Configuration Operations',
            children: <p>
                    <input
                        style={{display: 'none'}}
                        ref={typeInputRef}
                        type="file"
                        onChange={(e) => {
                            try {
                                const fileObj = e.target.files && e.target.files[0];
                                const reader = new FileReader();
                                reader.onload = function (e) {
                                    try {
                                        let dataBuf = JSON.parse(e.target.result)
                                        UpdateInstanceType(dataBuf,(response)=>{
                                            GetEmulationConfig((response)=>{
                                                setTypeConfig(response.data.data.type_config?response.data.data.type_config:{})
                                            })
                                        })
                                    }catch (e) {
                                        console.error(e);
                                        messageApi.open({
                                            type: "error",
                                            content: "Import Failed:"+e.toString(),
                                        })
                                    }
                                };
                                reader.readAsText(fileObj);
                                messageApi.open({
                                    type: "success",
                                    content: "Successfully Imported Node Type Configuration File",
                                })
                            } catch (e) {
                                console.error(e);
                                messageApi.open({
                                    type: "error",
                                    content: "Import Failed:"+e.toString(),
                                })
                            }
                        }}
                    />
                    <Button style={{marginLeft:"5px",marginRight:"5px"}}
                        onClick={()=>{
                            typeInputRef.current.click()
                        }}
                    >
                        Upload Type Configuration
                    </Button>
                    <input
                        style={{display: 'none'}}
                        ref={topoInputRef}
                        type="file"
                        onChange={(e) => {
                            try {
                                const fileObj = e.target.files && e.target.files[0];
                                const reader = new FileReader();
                                reader.onload = function (e) {
                                    try {
                                        let dataBuf = JSON.parse(e.target.result)
                                        AddTopology(dataBuf,(response)=>{
                                            GetInstanceList((response)=>{
                                                setInstanceList(response.data.data?response.data.data:[])
                                            })
                                            GetLinkList((response)=>{
                                                setLinkList(response.data.data?response.data.data:[])
                                            })
                                        })
                                    } catch (e) {
                                        console.error(e);
                                        messageApi.open({
                                            type: "error",
                                            content: "Import Failed:"+e.toString(),
                                        })
                                    }
                                };
                                reader.readAsText(fileObj);
                                messageApi.open({
                                    type: "success",
                                    content: "Successfully Imported Topology Configuration File",
                                })
                            } catch (e) {
                                console.error(e);
                                messageApi.open({
                                    type: "error",
                                    content: "Import Failed:"+e.toString(),
                                })
                            }
                        }}
                    />
                    <Button style={{marginLeft:"5px",marginRight:"5px"}}
                        onClick={()=>{
                            topoInputRef.current.click()
                        }}
                    >
                        Upload Topology Configuration
                    </Button>
                    <Button style={{marginLeft:"5px",marginRight:"5px"}}
                        onClick={running?
                            ()=>{
                                StopEmulation((response)=>{
                                    setRunning(!running)
                                    messageApi.open({
                                        type: "success",
                                        content: "Stop Successful",
                                    })
                                })
                            }:
                            ()=>{
                                
                                StartEmulation((response)=>{
                                    setRunning(!running)
                                    messageApi.open({
                                        type: "success",
                                        content: "Start Successful",
                                    })
                                })
                            }
                        }
                    >
                        {running?"Stop Simulation":"Start Simulation"}
                    </Button>
                    <Button style={{marginLeft:"5px",marginRight:"5px"}}
                        onClick={()=>{
                            ResetEmulation((response)=>{
                                GetInstanceList((response)=>{
                                    setInstanceList(response.data.data?response.data.data:[])
                                })
                                GetLinkList((response)=>{
                                    setLinkList(response.data.data?response.data.data:[])
                                })
                                messageApi.open({
                                    type: "success",
                                    content: "Reset Successful",
                                })
                            })
                        }}
                    >
                        Reset Simulation Environment
                    </Button>
            </p>,
        }
      ];

    const instanceTypeData = Object.keys(typeConfig).map((item,index)=>{
        return {
            type_name:item,
            image:typeConfig[item].image,
            resource:"CPU:"+typeConfig[item].resource_limit.nano_cpu/1e7+"% Memory:"+(typeConfig[item].resource_limit.memory_byte/ (1<<20)).toFixed(1)+" MB"
        }
    })

    return (
        <div>
        {contextHolder}
        <Card style={{width:"100%"}}>
        <Typography.Title level={4}>Running Status</Typography.Title>
        <Descriptions bordered items={items} />
        </Card>
        <Divider/>
        <Card>
        <List
            grid={{
            gutter: 16,
            column: 4,
            }}
            dataSource={instanceTypeData}
            header={
                <Typography.Title level={4}>
                    Node Type Configuration
                    <Button>Add Node Type</Button>
                </Typography.Title>
                }
            renderItem={(item) => (
            <List.Item>
                <Card title={"Type: " + item.type_name}>
                    <p>Corresponding Image: {item.image}</p>
                    <p>Resource Quota: {item.resource}</p>
                </Card>
            </List.Item>
            )}
        />
        </Card>
        <Divider/>
        <Card style={{width:"100%"}}>
            <Typography.Title level={4}>3D Visualization Display</Typography.Title>
            <Viewer timeline={false} homeButton={false} geocoder={false} animation={false} navigationHelpButton={false} fullscreenButton={false}>
                {   
                    
                    instanceList.map((item,index) => {
                        return (
                            <Entity
                                key={index}
                                name={item.instance_id}
                                description={JSON.stringify(item.extra, null, '\t')}
                                position={instancePosition[item.instance_id]?Cartesian3.fromRadians(
                                    instancePosition[item.instance_id].longitude, 
                                    instancePosition[item.instance_id].latitude,
                                    instancePosition[item.instance_id].altitude
                                ):Cartesian3.fromRadians(0,0,0)}
                                onDoubleClick={(e)=>{
                                    const w = window.open('_black')
                                    let url = `/instance/${item.node_index}/${item.instance_id}`
                                    w.location.href = url
                                }}
                            >
                                <PointGraphics
                                    pixelSize={10}
                                />
                                {
                                    <LabelGraphics text={item.name} font="30px sans-serif" showBackground={true} pixelOffset={new Cartesian2(0, 15)}/>
                                }
                            </Entity>
                        )
                    })
                    
                }
                {
                    
                    linkList.map((item,index) => {
                        if (!running || !linkParameter[item.link_id]) {
                            return null;
                        }
                        
                        if (linkParameter[item.link_id]["connect"]===1 && instancePosition[item.connect_instance[0]]!==undefined && instancePosition[item.connect_instance[1]]!==undefined) {
                            const array = [
                                instancePosition[item.connect_instance[0]].longitude, 
                                instancePosition[item.connect_instance[0]].latitude,
                                instancePosition[item.connect_instance[0]].altitude,
                                instancePosition[item.connect_instance[1]].longitude, 
                                instancePosition[item.connect_instance[1]].latitude,
                                instancePosition[item.connect_instance[1]].altitude,
                            ]
                            return (
                                <Entity key={item.link_id} name={item.link_id} description={`${item.connect_instance[0]}-${item.connect_instance[1]}`} 
                                    onDoubleClick={(e)=>{
                                        const w = window.open('_black')
                                        let url = `/link/${item.node_index}/${item.link_id}`
                                        w.location.href = url
                                    }}
                                >
                                    <PolylineGraphics
                                        positions={Cartesian3.fromRadiansArrayHeights(array)}
                                        width={1}
                                        material={linkColor[item.link_id]}
                                        
                                    />
                                    
                                </Entity>
                            )
                        } else {
                            if (linkParameter[item.link_id]["connect"]===1) {
                                console.log(`${item.link_id} not draw`)
                                console.log(`connect ${linkParameter[item.link_id]["connect"]}`)
                                console.log(`instance ${instancePosition[item.connect_instance[0]]!==undefined} ${instancePosition[item.connect_instance[1]]!==undefined}`)
                            }
                            return null
                        }
                    })

                }
                
            </Viewer>
        </Card>
        </div>
    )
}