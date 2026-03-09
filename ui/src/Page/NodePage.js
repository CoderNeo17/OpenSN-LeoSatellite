import { Button, Card, Divider, List,Typography } from "antd";
import { useEffect, useState } from "react";
import { GetNodeList } from "../Request/node";
export const NodeList = () => {
    let [nodeList,setNodeList] = useState([])
    useEffect(()=>{
        GetNodeList((response)=>{
            setNodeList(response.data.data==null?[]:response.data.data)
        })
    },[])
    return (
        <List
                bordered
                header={<div style={{height:"30px"}}>
                        <Typography.Text strong style={{float:"left"}}>Compute Node List</Typography.Text>
                        </div>}
                dataSource={nodeList}
                renderItem={(item,index) => 
                    <List.Item>
                    <Card>
                        <Card.Meta
                            title={`Node Number: ${item.node_index}-${item.is_master_node?"Master Node":"Slave Node"}`}
                        />
                        <Divider/>
                        <div>
                        <Typography.Paragraph>
                            <Typography.Text>
                                {`Remaining Allocatable Containers: ${item.free_instance}`}
                            </Typography.Text>
                        </Typography.Paragraph>
                        <Typography.Paragraph>
                            <Typography.Text>
                                {`IPv4 Address: ${item.l_3_addr_v_4}`}
                            </Typography.Text>
                        </Typography.Paragraph>
                        <Typography.Paragraph>
                            <Typography.Text>
                                {`IPv6 Address: ${item.l_3_addr_v_6}`}
                            </Typography.Text>
                        </Typography.Paragraph>
                        <Typography.Paragraph>
                            <Typography.Text>
                                {`MAC Address: ${item.l_2_addr}`}
                            </Typography.Text>
                        </Typography.Paragraph>
                        </div>
                        
                        {/* <div>
                            <Button>Details</Button>
                        </div> */}
                    </Card>
                   
                    </List.Item>}
            />
    )
}