import {Card,List,Button,Typography} from "antd";

export function ConfigNamespaceLink({dataBuf,setDataBuf}) {
    return (
        <Card title={"Namespace Initial Link Configuration"}>
            <List
                bordered
                header={<div style={{height:"30px"}}>
                        <Typography.Text strong style={{float:"left"}}>Namespace Link List</Typography.Text>
                        <Button style={{float:"right"}}>Add</Button>
                        </div>}
                dataSource={dataBuf.link_config}
                renderItem={(item,index) => 
                    <List.Item>
                    <List.Item.Meta
                        title={<Typography.Text>Index:{index}-Type:{item.type}</Typography.Text>}
                        description={<div>
                            <div>
                                <Typography.Text>
                                    {`Connection Information:${item.instance_index[0]}<-->${item.instance_index[1]}`}
                                </Typography.Text>
                            </div>
                            <Typography.Text>Parameters</Typography.Text>
                            <div>
                                {JSON.stringify(item.parameter)}
                            </div>
                        </div>}
                    />
                    <div>
                        <Button>Edit</Button> 
                        <Button>Delete</Button>
                    </div>
                    </List.Item>
                }
            />
        </Card>
    )
}