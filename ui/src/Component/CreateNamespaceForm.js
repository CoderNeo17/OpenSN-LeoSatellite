
import { Tabs, Typography, Divider, Button, notification} from "antd";
import React, { useState, useRef } from "react";
import { ConfigNamespaceBasic } from "./ConfigNamesapceBasic";
import { ConfigNamespaceInstance } from "./ConfigNamespaceInstance";
import { ConfigNamespaceLink } from "./ConfigNamespaceLink";

export function CreateNamespaceForm() {
    const [dataBuf,setDataBuf] = useState({});

    const [api, contextHolder] = notification.useNotification();
    const NotificationWithIcon = (type,msg,detail) => {
        api[type]({
            message: msg,
            description:detail,
        });
    };
    const inputRef = useRef(null);
    return (
        <div style={{height:"100%",overflowY:"scroll"}}>
            {contextHolder}
            <Typography.Title level={2}>Create Namespace</Typography.Title>
            <Divider dashed />
            <Tabs defaultActiveKey="1" 
                tabPosition="left" 
                tabBarExtraContent={{
                        "left" : 
                            <div>
                                <div>
                                    <input
                                        style={{display: 'none'}}
                                        ref={inputRef}
                                        type="file"
                                        onChange={(e) => {
                                            try {
                                                const fileObj = e.target.files && e.target.files[0];
                                                console.log(fileObj);
                                                const reader = new FileReader();
                                                reader.onload = function (e) {
                                                    try {
                                                        dataBuf = JSON.parse(e.target.result)
                                                        setDataBuf(dataBuf);
                                                    }catch (e) {
                                                        console.error(e);
                                                        NotificationWithIcon("error","Import Failed","Error:"+e.toString());
                                                    }
                                                };
                                                reader.readAsText(fileObj);
                                                NotificationWithIcon("success","Import Successful","Successfully Imported Configuration File");
                                            } catch (e) {
                                                console.error(e);
                                                NotificationWithIcon("error","Import Failed","Error:"+e.toString());
                                            }
                                        }}
                                    />
                                    <Button 
                                        style={{marginBottom:"15px"}}
                                        onClick={() => {
                                            inputRef.current.click();
                                        }}
                                    >
                                        Import
                                    </Button>
                                </div>
                                <div>
                                    <Button 
                                        style={{marginBottom:"15px"}}
                                        onClick={() => {
                                            const blob = new Blob([JSON.stringify(dataBuf)], {
                                                type: 'application/json'
                                            })
                                            const objectURL = URL.createObjectURL(blob)
                                            const domElement = document.createElement('a')
                                            domElement.href = objectURL
                                            domElement.download = "namespace_"+dataBuf.name+"_" + Date.now() + ".json"
                                            domElement.click()
                                            URL.revokeObjectURL(objectURL)
                                        }}
                                    >
                                        Export
                                    </Button>
                                </div>
                            </div>,
                    "right":<Button onClick={()=>{
                        
                            NotificationWithIcon("success","Creation Successful","Successfully Created Namespace")
                        
                    }}> 
                        Confirm
                    </Button>  
                   }}
                items = {[
                    {
                        key :"Basic",
                        label :"Basic Configuration",
                        children : <div >
                            <ConfigNamespaceBasic  dataBuf={dataBuf} setDataBuf={setDataBuf}/>
                        </div> 
                    },
                    {
                        key :"Instance",
                        label :"Container Instance Configuration",
                        children : <div >
                            <ConfigNamespaceInstance  dataBuf={dataBuf} setDataBuf={setDataBuf}/>
                        </div> 
                    },
                    {
                        key :"Link",
                        label :"Link Instance Configuration",
                        children : <div >
                            <ConfigNamespaceLink  dataBuf={dataBuf} setDataBuf={setDataBuf}/>
                        </div> 
                    }
                ]
            }/>
        </div>     
    )
}