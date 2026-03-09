import { Button, Drawer, Input, Space, Typography} from 'antd';
import { useState } from 'react';
export const ContainerEnvDrawer = ({dataBuf,setDataBuf,open,setOpen}) => {

  const onClose = () => {
    setOpen(false)
  }

  

  const [envKey,setEnvKey] = useState("")
  const [envValue,setEnvValue] = useState("")

  const onConfirm = () => {
    setEnvKey("")
    setEnvValue("")
    dataBuf.ns_config.container_envs[envKey] = envValue
    setDataBuf(dataBuf)
    setOpen(false)
    console.log(dataBuf)
  }

  return (
    <Drawer
        title="Add Initial Environment Variables"
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
          <Typography.Text strong>Environment Variable Key: </Typography.Text>
          <Input type="text" style={{width:"200px"}} onChange={(e) => {
              setEnvKey(e.target.value)
          }} />
        </Typography.Paragraph>
        <Typography.Paragraph>
          <Typography.Text strong>Environment Variable Value: </Typography.Text>
          <Input type="text" style={{width:"200px"}} onChange={(e) => {
              setEnvValue(e.target.value)
          }} />
        </Typography.Paragraph>
      </Drawer>
  );
}