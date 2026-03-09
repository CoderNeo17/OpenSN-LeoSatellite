import { Button, Divider, Drawer, Input, Space, Typography} from 'antd';
import { useState } from 'react';
import { ResourceLimit } from '../Model/Namespace';
export const InstanceTypeDrawer = ({dataBuf,setDataBuf,open,setOpen}) => {

  const onClose = () => {
    setOpen(false)
  }

  const onConfirm = () => {
    dataBuf.ns_config.image_map[typeName] = imageName
    dataBuf.ns_config.resource_map[typeName] = resourceLimit
    setTypeName("")
    setImageName("")
    setResourceLimit(new ResourceLimit())
    setDataBuf(dataBuf)
    setOpen(false)
    console.log(dataBuf)
  }

  const [typeName,setTypeName] = useState("")
  const [imageName,setImageName] = useState("")
  const [resourceLimit,setResourceLimit] = useState(new ResourceLimit())

  return (
    <Drawer
        title="Add Instance Type"
        width={400}
        onClose={onClose}
        open={open}
        styles={{
          body: {
            paddingBottom: 80,
          },
        }}
        extra={
          <Space>
            <Button onClick={onClose}>Cancel</Button>
            <Button onClick={onConfirm} type="primary">
              Confirm
            </Button>
          </Space>
        }
      >
        <Typography.Paragraph>
          <Typography.Text strong>Instance Type: </Typography.Text>
          <Input type="text" style={{width:"200px"}} onChange={(e) => {
              setTypeName(e.target.value);
          }} />
        </Typography.Paragraph>
        <Divider/>
        <Typography.Paragraph>
          <Typography.Text strong>Image Name: </Typography.Text>
          <Input type="text" style={{width:"200px"}} onChange={(e) => {
              setImageName(e.target.value);
          }} />
        </Typography.Paragraph>
        <Divider/>
        <Typography.Paragraph>
          <div>
            <Typography.Text strong>CPU Limit (1e-9 Core): </Typography.Text>
            <Input type="text" style={{width:"200px"}} onChange={(e) => {
                resourceLimit.nano_cpu = e.target.value;
                setResourceLimit(resourceLimit);
            }} />
          </div>
          <div>
            <Typography.Text strong>Memory Limit (Byte): </Typography.Text>
            <Input type="text" style={{width:"200px"}} onChange={(e) => {
                resourceLimit.memory_byte = e.target.value;
                setResourceLimit(resourceLimit);
            }} />
          </div>
        </Typography.Paragraph>
        <Typography.Paragraph>
          "Limit must be an integer, can end with [K|M|G|T] units, case insensitive"
        </Typography.Paragraph>
      </Drawer>
  );
};