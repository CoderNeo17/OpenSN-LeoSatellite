import { Button, Card, Divider, List,Typography } from "antd";
import { useEffect, useState } from "react";
export const NamespaceList = () => {
    let [namespaceList,setNamespaceList] = useState([])
    useEffect(()=>{
    },[])
    return (
        <List
                bordered
                header={<div style={{height:"30px"}}>
                        <Typography.Text strong style={{float:"left"}}>Namespace List</Typography.Text>
                        </div>}
                direction="vertical"
                dataSource={namespaceList}
                renderItem={(item,index) => 
                    <List.Item>
                    <Card>
                        <Card.Meta
                            title={`Namespace Name: ${item.name}-${item.running?"Running":"Stopped"}`}
                        />
                        <Divider/>
                        <div>
                        <Typography.Paragraph>
                            <Typography.Text>
                                {`Namespace Container Instance Count:${item.instance_num}`}
                            </Typography.Text>
                        </Typography.Paragraph>
                        <Typography.Paragraph>
                            <Typography.Text>
                                {`Namespace Link Count:${item.link_num}`}
                            </Typography.Text>
                        </Typography.Paragraph>
                        <Typography.Paragraph>
                            <Typography.Text>
                                {`Namespace Allocated Compute Node List:${item.running?JSON.stringify(item.alloc_node_index):"Not Running"}`}
                            </Typography.Text>
                        </Typography.Paragraph>
                       
                        </div>
                        
                        <div>
                            <Button
                                onClick={()=>{
                                    
                                }}
                            >
                                {item.running?"Stop":"Start"}
                            </Button>
                            <Button>Edit</Button>
                            <Button
                                onClick={()=>{
                                    window.open(`/namespace/${item.name}/detail`, "_blank")
                                }}
                            >Details</Button>
                        </div>
                    </Card>
                   
                    </List.Item>}
            />
    )
}