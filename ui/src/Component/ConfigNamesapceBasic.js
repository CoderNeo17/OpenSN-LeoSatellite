import {Card,List,Button,Input,Typography,Divider} from "antd";
import { ContainerEnvDrawer } from "./ContainerEnvDrawer";
import { useState } from "react";
import { InstanceTypeDrawer } from "./InstanceTypeDrawer";
export function ConfigNamespaceBasic({dataBuf,setDataBuf}) {
    const [envMapOpen,setEnvMapOpen] = useState(false);
    const [instanceTypeOpen,setInstanceTypeOpen] = useState(false);
    return (

            <Card title={"Namespace Basic Information"}>
                <Typography.Text strong>Name: </Typography.Text>
                <Input type="text" style={{width:"200px"}} onChange={(e) => {
                    dataBuf.name = e.target.value;
                    setDataBuf(dataBuf);
                }} />
                <Divider dashed />
                
                <List
                    size="small"
                    bordered
                    header={<div style={{height:"30px"}}>
                        <Typography.Text strong style={{float:"left"}}>Instance Types and Images</Typography.Text>
                        <Button 
                            style={{float:"right"}}
                            onClick={()=>{setInstanceTypeOpen(true)}}
                        >
                            Add
                        </Button>
                        <InstanceTypeDrawer
                            dataBuf={dataBuf} setDataBuf={setDataBuf}
                            open={instanceTypeOpen} setOpen={setInstanceTypeOpen}
                        />
                        </div>}
                    dataSource={Object.keys(dataBuf.ns_config.image_map)}
                    style={{height:"320px",overflow:"auto"}}
                    renderItem={(item_key) => (
                    <List.Item key={item_key}>
                        <Card title={`Instance Type:${item_key}`}>
                            <Typography.Paragraph>
                                {`Image Name:${dataBuf.ns_config.image_map[item_key]}`}
                            </Typography.Paragraph>
                            <Typography.Paragraph>
                                {`CPU Quota (1e-9):${dataBuf.ns_config.resource_map[item_key].nano_cpu}`}
                            </Typography.Paragraph>
                            <Typography.Paragraph> 
                                {`Memory Quota (Byte):${dataBuf.ns_config.resource_map[item_key].memory_byte}`}
                            </Typography.Paragraph>
                            <Button 
                                style={{float:"right"}}
                                onClick={()=>{
                                    delete dataBuf.ns_config.image_map[item_key]
                                    delete dataBuf.ns_config.resource_map[item_key]
                                    // setDataBuf(dataBuf)
                                }}
                            >
                                Delete
                            </Button>
                            
                        </Card>
                    </List.Item>
                    )}
                />
                <Divider dashed />
                <List
                    size="small"
                    bordered
                    style={{height:"240px",overflow:"auto"}}
                    header={<div style={{height:"30px"}} >
                        <Typography.Text strong style={{float:"left"}}>Initial Environment Variables</Typography.Text>
                        <Button 
                            style={{float:"right"}}
                            onClick={()=>{setEnvMapOpen(true)}}
                        >
                            Add
                        </Button>
                        <ContainerEnvDrawer 
                            dataBuf={dataBuf} setDataBuf={setDataBuf}
                            open={envMapOpen} setOpen={setEnvMapOpen}
                        />
                    </div>}
                    dataSource={Object.keys(dataBuf.ns_config.container_envs)}
                    renderItem={(item) => <List.Item>
                        {`${item}=${dataBuf.ns_config.container_envs[item]}`} 
                        <Button style={{float:"right"}} >Delete</Button>
                        </List.Item>}
                />
                </Card>
        
    )
}