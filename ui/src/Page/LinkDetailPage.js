
import { Card, Col, Descriptions, Divider, List, Row, Typography, Badge, Button,Select} from "antd"
import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import ReactECharts from 'echarts-for-react'
import { GetPeriodInstanceResource, GetPeriodLinkResource } from "../Request/metrics"
import { GetInstanceDetail } from "../Request/instance"
import { StartLinkWebshell } from "../Request/webshell"
import { GetLinkInfo, GetLinkParameter } from "../Request/link"

export const LinkDetailPage = () => {
    const linkID = useParams().link_id
    const nodeIndex = useParams().node_index
    const [linkResource,setLinkResource] = useState({})
    const [linkParameter,setLinkParameter] = useState({})
    const [resourcePeriod,setResourcePeriod] = useState("10m")
    const [linkInfo,setLinkInfo] = useState({})
    const [linkDumpUrl,setLinkDumpUrl] = useState("")
    useEffect(()=>{
        GetLinkInfo(nodeIndex,linkID,(response)=>{
            setLinkInfo(response.data.data)
        })
        GetPeriodLinkResource(linkID,resourcePeriod,(response)=>{
            setLinkResource(response.data.data)
        })
        GetLinkParameter(nodeIndex,linkID,(response)=>{
            setLinkParameter(response.data.data)
        })
        setInterval(()=>{
            GetLinkInfo(nodeIndex,linkID,(response)=>{
                setLinkInfo(response.data.data)
            })
            GetPeriodLinkResource(linkID,resourcePeriod,(response)=>{
                setLinkResource(response.data.data)
            })
            GetLinkParameter(nodeIndex,linkID,(response)=>{
                setLinkParameter(response.data.data)
            })
        },1000)
    },[])
    
    const descriptionDetail = [
        {
            key:"link_id",
            label:"Link ID",
            children:linkID,
        },
        {
            key:"link_enable",
            label:"Link Enable Status",
            children:linkInfo.enable?
                <Badge status="success" text="Started" />:
                <Badge status="default" text="Not Started" />    
            ,
        },
        {
            key:"link_type",
            label:"Link Type",
            children:linkInfo.type,
        },
        {
            key:"node_index",
            label:"Link Deployment Machine Number",
            children:nodeIndex,
        },
        {
            key:"link_parameter",
            label:"Link Parameters",
            children:<List>
                {Object.keys(linkParameter).map((key)=>{
                    return (
                        <List.Item key={key}>
                            <List.Item.Meta
                                title={key}
                                description={linkParameter[key]}
                            />
                        </List.Item>
                    )
                })}
            </List>,
        },
        {
            key:"link_end_infos",
            label:"Link End Information",
            children:<List>
                {linkInfo.end_infos?linkInfo.end_infos.map((item,index)=>{
                    return (
                        <List.Item key={index}>
                            <List.Item.Meta
                                title={<Typography.Link href={`/instance/${item.end_node_index}/${item.instance_id}`} target="_blank">{item.instance_id}</Typography.Link>}
                                description={`Node of type ${item.instance_type} deployed on machine ${item.node_index}`}
                            />
                        </List.Item>
                    )
                }):[]}
            </List>,
        },
        {
            key:"link_addr_infos",
            label:"Link End Address Information",
            children:<List bordered>
                {linkInfo.address_infos?linkInfo.address_infos.map((item,index)=>{
                    return (
                        <List.Item key={index}>
                            {Object.keys(item).map((key)=>{
                                return (
                                    <p key={key}>
                                        {`${key}= ${item[key]}`}
                                    </p>
                                )
                            })}
                        </List.Item>
                    )
                }):[]}
            </List>,
        }
    ]

    const cpuChartOption = {
        title: {
            text: 'Link Send/Receive Throughput (Bps)'
        },
        tooltip: {},
        legend: {
            data:['Received Data','Sent Data']
        },
        xAxis: {
            data: linkResource[linkID]?linkResource[linkID].map((item)=>{
                const time = Date.parse(item.Time)
                return `${new Date(time).getHours()}:${new Date(time).getMinutes()}:${new Date(time).getSeconds()}`
            }):[]
        },
        yAxis: {},
        series: [
            {
                name: 'Sent Data Volume',
                type:'line',
                data: linkResource[linkID]?linkResource[linkID].map((item)=>item.send_bps):[]
            },
            {
                name: 'Received Data Volume',
                type:'line',
                data: linkResource[linkID]?linkResource[linkID].map((item)=>item.recv_bps):[]
            }
        ]
    }

    const memChartOption = {
        title: {
            text: 'Link Packet Statistics'
        },
        tooltip: {},
        legend: {
            data:['Sent Packets','Received Packets','Sent Packet Loss','Received Packet Loss','Sent Error Packets','Received Error Packets']
        },
        xAxis: {
            data: linkResource[linkID]?linkResource[linkID].map((item)=>{
                const time = Date.parse(item.Time)
                return `${new Date(time).getHours()}:${new Date(time).getMinutes()}:${new Date(time).getSeconds()}`
            }):[]
        },
        yAxis: {},
        series: [
            {
                name: 'Sent Packets',
                type:'line',
                data: linkResource[linkID]?linkResource[linkID].map((item)=>item.send_pps):[]
            },
            {
                name: 'Received Packets',
                type:'line',
                data: linkResource[linkID]?linkResource[linkID].map((item)=>item.recv_pps):[]
            },
            {
                name: 'Sent Packet Loss',
                type:'line',
                data: linkResource[linkID]?linkResource[linkID].map((item)=>item.send_drop_pps):[]
            },
            {
                name: 'Received Packet Loss',
                type:'line',
                data: linkResource[linkID]?linkResource[linkID].map((item)=>item.recv_drop_pps):[]
            },
            {
                name: 'Sent Error Packets',
                type:'line',
                data: linkResource[linkID]?linkResource[linkID].map((item)=>item.send_err_pps):[]
            },
            {
                name: 'Received Error Packets',
                type:'line',
                data: linkResource[linkID]?linkResource[linkID].map((item)=>item.recv_err_pps):[]
            }
        ]
        
    }

    return (
        <div>
            <Row justify="center">
                <Col>
                    <Typography.Title level={2} >Link Details:{linkID}</Typography.Title>
                </Col>
            </Row>
            <Row justify="center">
                <Card>
                    <Col>
                    <Descriptions style={{width:"90vw"}} bordered items={descriptionDetail} />
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
                    GetPeriodLinkResource(linkID,resourcePeriod,(response)=>{
                        setLinkResource(response.data.data)
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
            </Row>
            <Row justify="space-between">
                    <Col style={{marginLeft:"5vw"}}>
                        <Card>
                            <ReactECharts
                                option={cpuChartOption}
                                style={{ height: "40vh",width:"40vw" }}
                            />
                        </Card>
                    </Col>
                    <Col style={{marginRight:"5vw"}}>
                        <Card>
                            <ReactECharts
                                option={memChartOption}
                                style={{ height: "40vh",width:"40vw" }}
                            />
                        </Card>
                    </Col>
                
            </Row>
            <Divider/>
            
            <Row justify="center" >
            <Typography.Title level={4}>Packet Capture Information</Typography.Title>
            </Row>
            <Row justify="center">
            <Button enable={linkDumpUrl===""} onClick={()=>{
                StartLinkWebshell(linkID,nodeIndex,(response)=>{
                    const linkWebshellInfo = response.data.data
                    const webShellUrl = `http://${linkWebshellInfo.addr}:${linkWebshellInfo.port}`
                    setLinkDumpUrl(webShellUrl)
                })
            }}>Start Packet Capture</Button>
            </Row>
            <Card style={{width:"90vw",marginLeft:"5vw",marginRight:"5vw"}}>
            <Row justify="center" ><iframe style={{width:"80vw",height:"720px"}} enable={linkDumpUrl!==""} src={linkDumpUrl===""?"":linkDumpUrl}/></Row>
            </Card>
        </div>
    )
}