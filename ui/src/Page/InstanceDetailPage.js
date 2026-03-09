
import { Card, Col, Descriptions, Divider, List, Row, Typography, Badge, Button,Tabs,Select} from "antd"
import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import ReactECharts from 'echarts-for-react'
import { GetPeriodInstanceResource } from "../Request/metrics"
import { GetInstanceDetail } from "../Request/instance"
import { StartInstanceWebshell } from "../Request/webshell"

export const InstanceDetailPage = () => {
    const instanceID = useParams().instance_id
    const nodeIndex = useParams().node_index
    const [instanceResource,setInstanceResource] = useState({})
    const [resourcePeriod,setResourcePeriod] = useState("10m")
    const [instanceInfo,setInstanceInfo] = useState({})
    const [items, setItems] = useState([
    ]);
    const [activeKey, setActiveKey] = useState("");
    useEffect(()=>{
        GetPeriodInstanceResource(instanceID,resourcePeriod,(response)=>{
            setInstanceResource(response.data.data)
        })
        GetInstanceDetail(nodeIndex,instanceID,(response)=>{
            setInstanceInfo(response.data.data)
        })
        setInterval(()=>{
            GetPeriodInstanceResource(instanceID,resourcePeriod,(response)=>{
                setInstanceResource(response.data.data)
            })
            GetInstanceDetail(nodeIndex,instanceID,(response)=>{
                setInstanceInfo(response.data.data)
            })
        },1000)
    },[])
    
    const descriptionDetail = [
        {
            key:"instance_id",
            label:"Node ID",
            children:instanceID,
        },
        {
            key:"instance_name",
            label:"Node Name",
            children:instanceInfo.name,
        },
        {
            key:"instance_start",
            label:"Node Start Status",
            children:instanceInfo.start?
                <Badge status="success" text="Started" />:
                <Badge status="default" text="Not Started" />    
            ,
        },
        {
            key:"instance_type",
            label:"Node Type",
            children:instanceInfo.type,
        },
        {
            key:"instance_image",
            label:"Node Image",
            children:instanceInfo.image,
        },
        {
            key:"node_index",
            label:"Node Deployment Machine Number",
            children:nodeIndex,
        },
        {
            key:"instance_resource",
            label:"Node Resource Limit",
            children:<div>
                <p>
                    CPU Limit (Nano): {instanceInfo?.resource_limit?.nano_cpu}
                </p>
                <p>
                    Memory (Byte): {instanceInfo?.resource_limit?.memory_byte}
                </p>
            </div>,
        },
        {
            key:"instance_connections",
            label:"Node Connection Information",
            children:<List>
                {instanceInfo.connections?Object.keys(instanceInfo.connections).map((item,index)=>{
                    return (
                        <List.Item key={index}>
                            <List.Item.Meta title={<Typography.Link href={`/link/${instanceInfo.node_index}/${item}`} target="_blank">{item}</Typography.Link>}/>
                            <p>
                                {`Connected to node of type ${instanceInfo.connections[item].instance_type} deployed on machine ${instanceInfo.connections[item].end_node_index}`}
                                <Typography.Link  href={`/instance/${instanceInfo.connections[item].end_node_index}/${instanceInfo.connections[item].instance_id}`} target="_blank">{instanceInfo.connections[item].instance_id} </Typography.Link>
                            </p>
                        </List.Item>
                    )
                }):[]}
            </List>,
        },
    ]

    const cpuChartOption = {
        title: {
            text: 'Node CPU Usage'
        },
        tooltip: {},
        legend: {
            data:['CPU Usage Rate']
        },
        xAxis: {
            data: instanceResource[instanceID]?instanceResource[instanceID].map((item)=>{
                const time = Date.parse(item.Time)
                return `${new Date(time).getHours()}:${new Date(time).getMinutes()}:${new Date(time).getSeconds()}`
            }):[]
        },
        yAxis: {},
        series: [{
            name: 'CPU Usage Rate',
            type:'line',
            data: instanceResource[instanceID]?instanceResource[instanceID].map((item)=>item.cpu_usage):[]
        }]
    }

    const memChartOption = {
        title: {
            text: 'Node Memory Usage'
        },
        tooltip: {},
        legend: {
            data:['Memory Usage','Swap Memory Usage']
        },
        xAxis: {
            data: instanceResource[instanceID]?instanceResource[instanceID].map((item)=>{
                const time = Date.parse(item.Time)
                return `${new Date(time).getHours()}:${new Date(time).getMinutes()}:${new Date(time).getSeconds()}`
            }):[]
        },
        yAxis: {},
        series: [
            {
                name: 'Memory Usage',
                type:'line',
                data: instanceResource[instanceID]?instanceResource[instanceID].map((item)=>item.mem_byte):[]
            },
            {
                name: 'Swap Memory Usage',
                type:'line',
                data: instanceResource[instanceID]?instanceResource[instanceID].map((item)=>item.swap_mem_byte):[]
            }
        ]
        
    }

    return (
        <div>
            <Row justify="center">
                <Col>
                    <Typography.Title level={2} >Instance Details:{instanceID}</Typography.Title>
                </Col>
            </Row>
            <Row justify="center">
                <Card>
                    <Col>
                    <Descriptions bordered items={descriptionDetail} />
                    </Col>
                </Card>
                
            </Row>
            <Divider/>
            <Row justify="center"> <Typography.Title level={4}>Resource Monitoring</Typography.Title> </Row>
            <Row justify="center"> 
            <Select
                defaultValue={resourcePeriod}
                style={{ width: 120 }}
                onChange={(value)=>{
                    setResourcePeriod(value)
                    GetPeriodInstanceResource(instanceID,resourcePeriod,(response)=>{
                        setInstanceResource(response.data.data)
                    })
                }}
                options={[
                    { value: '1m', label: 'Last 1 Minute' },
                    { value: '5m', label: 'Last 5 Minutes' },
                    { value: '10m', label: 'Last 10 Minutes' },
                    { value: '30m', label: 'Last 30 Minutes' },
                    { value: '1h', label: 'Last 1 Hour' },
                    { value: '3h', label: 'Last 3 Hours' },
                    { value: '6h', label: 'Last 6 Hours' },
                    { value: '12h', label: 'Last 12 Hours' },
                    { value: '24h', label: 'Last 24 Hours' },
                ]}
            />
            {/* <Button onClick={()=>{
                GetPeriodInstanceResource(instanceID,resourcePeriod,(response)=>{
                    setInstanceResource(response.data.data)
                })
            }
            }>Refresh</Button> */}
            </Row>
            <Row justify="space-between">

                    <Col style={{marginLeft:"5vw"}}>
                        <Card>
                            <ReactECharts
                                option={cpuChartOption}
                                style={{ height: "30vh",width:"40vw" }}
                            />
                        </Card>
                    </Col>
                    <Col style={{marginRight:"5vw"}}>
                        <Card>
                            <ReactECharts
                                option={memChartOption}
                                style={{ height: "30vh",width:"40vw" }}
                            />
                        </Card>
                    </Col>
                
            </Row>
            <Divider/>
            
            <Row justify="center" >
            <Typography.Title level={4}>WebShell</Typography.Title>
            <Card style={{width:"90vw",marginLeft:"5vw",marginRight:"5vw"}}>
                <Tabs
                    type="editable-card"
                    onChange={(newActiveKey) => {
                        setActiveKey(newActiveKey);
                    }}
                    style={{width:"100%"}}
                    activeKey={activeKey}
                    onEdit={(targetKey, action)=>{
                        if (action === 'add') {
                            StartInstanceWebshell(nodeIndex,instanceID,(response)=>{
                                const webshellInfo = response.data.data
                                const newKey = `${instanceID}-${items.length}`;
                                const url = `http://${webshellInfo.addr}:${webshellInfo.port}`
                                setItems([...items, { 
                                    key: newKey,
                                    label: newKey,
                                    children: <Row justify="center" ><iframe style={{width:"80vw",height:"720px"}} src={url}/></Row>
                                }]);
                                setActiveKey(newKey);
                            })
                        } else {
                            const targetIndex = items.findIndex((pane) => pane.key === targetKey);
                            const newPanes = items.filter((pane) => pane.key !== targetKey);
                            if (newPanes.length && targetKey === activeKey) {
                            const { key } = newPanes[targetIndex === newPanes.length ? targetIndex - 1 : targetIndex];
                            setActiveKey(key);
                            }
                            setItems(newPanes);
                        }
                    }}
                    items={items}
                />
                </Card>
            </Row>
        </div>
    )
}