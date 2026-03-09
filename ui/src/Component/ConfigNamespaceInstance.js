import {Card,List,Button,Typography} from "antd";
export function ConfigNamespaceInstance({dataBuf,setDataBuf}) {
    return (
        <Card title={"Namespace Initial Node Configuration"}>
            <List
                bordered
                header={<div style={{height:"30px"}}>
                        <Typography.Text strong style={{float:"left"}}>Namespace Container Instance List</Typography.Text>
                        <Button style={{float:"right"}}>Add</Button>
                        </div>}
                dataSource={dataBuf.inst_config}
                renderItem={(item,index) => 
                    <List.Item>
                    <List.Item.Meta
                        title={<Typography.Text>Index:{index}-Type:{item.type}</Typography.Text>}
                        description={<div>
                            <Typography.Text>Additional Information</Typography.Text>
                            <div>
                                {JSON.stringify(item.extra)}
                            </div>
                        </div>}
                    />
                    <div>
                        <Button>Edit</Button> 
                        <Button>Delete</Button>
                    </div>
                    </List.Item>}
            />
        </Card>
    )
}