import { Button, Card, Divider, List,Typography } from "antd";
import { useEffect, useState } from "react";
import { GetNodeList } from "../Request/node";
import { GetInstanceList } from "../Request/instance";
import { Link } from "react-router-dom";
export const InstanceListPage = () => {
    let [instanceList,setInstanceList] = useState([])
    useEffect(()=>{
        GetInstanceList((response)=>{
        setInstanceList(response.data.data==null?[]:response.data.data)
    })
    },[])
    return (
        <List
            itemLayout="vertical"
            size="large"
            pagination={{
            onChange: (page) => {
                console.log(page);
            },
            pageSize: 16,
            }}
            header = {
                <div style={{height:"70px"}} >
                    <Typography.Title level={4}>Network Node List</Typography.Title>
                    <Button>Add Node</Button>
                </div>
                
            }
            dataSource={instanceList}
            renderItem={(item,index)=>{
                return (
                    <List.Item key={item.link_id} actions={[
                        
                        <Button
                            onClick={()=>{
                                const w = window.open('_black')
                                let url = `/instance/${item.node_index}/${item.instance_id}`
                                w.location.href = url
                            }}
                        >View Details</Button>,

                        <Button
                            onClick={item.enable?
                                ()=>{}:
                                ()=>{}
                            }
                        >{item.start?"Stop":"Start"}</Button>,,
                        <Button>Delete</Button>
                    ]}>
                        <List.Item.Meta title={`Machine Number ${item.node_index} ${item.type}-${item.instance_id}: ${item.start?"Started":"Stopped"}`}/>
                        
                    </List.Item>
                )
            }}
        />
    )
}