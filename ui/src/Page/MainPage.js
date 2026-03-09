import {React,useState} from 'react';
import {Layout, Menu, theme } from 'antd';
import { MdOutlineSatelliteAlt } from "react-icons/md";
import { CreateNamespaceForm } from '../Component/CreateNamespaceForm';
import { NamespaceList } from '../Component/GetNamespaceList';
import { NodeList } from './NodePage';
import { ConsoleItems } from './OverviewPage';
import { FileItems, FilePage } from './FilePage';
import { InstanceListPage } from './InstancePage';
import { LinkListPage } from './LinkPage';
import { Overview } from './OverviewPage';
import ExportOutlined from '@ant-design/icons/ExportOutlined';
import {Ion} from 'cesium';
import { DatabasePage } from './DatabasePage';
import { TopologyConfiguratorPage } from './TopologyConfiguratorPage';
const { Header, Content, Sider } = Layout;

Ion.defaultAccessToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiIyMTg2ODQwZC00NTJiLTQ0MmUtOTM1Mi0yYTk3YTE4OGVlNGMiLCJpZCI6MTkxNzA5LCJpYXQiOjE3MTEyODE2NDR9.1dM1b_tT7qiFajlKeK4kLUFAvYrBMWq4-DlenYtUtJs"

const topBarItems = [
    {
        key:"overview",
        label: `Overview`,
    },
    {
      key:"instances",
      label: `Nodes`,
    },
    {
      key:"links",
      label: `Links`,
    },
    {
      key:"topo_conf",
      label: `Run Configurator`,
    },
    {
        key:"mount_manager",
        label: `File Management`,
    },
    {
      key:"cluster",
      label: `Deployment Machines`,
    },
    {
      key:"database",
      label: `View Database`,
    },
    {
        key:"help",
        label: (<a href="/help" target="_blank">
                  Help Document<ExportOutlined />
                </a>),
    },
    {
        key:"about",
        label: (<a href="/about" target="_blank">
                  About<ExportOutlined />
                </a>),
    }
];

const componentPage = {
    "overview":<Overview/>,
    "instances":<InstanceListPage/>,
    "links":<LinkListPage/>,
    "mount_manager":<FilePage/>,
    "cluster":<NodeList/>,
    "topo_conf":<TopologyConfiguratorPage/>,
    "database":<DatabasePage/>,
}

const App = () => {
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();
  var [selectedTopBarItem,setSelectedTopBarItem] = useState("overview");
  return (
    <Layout style={{height: '100%'}}> 
      <Header
        style={{
          display: 'flex',
          alignItems: 'left',
          paddingLeft: 0
        }}
      >
        <MdOutlineSatelliteAlt style={{color:"white",height:"40px",width:"40px",marginLeft:"80px",marginRight:"80px",marginTop:"12px"}}/>
        
        <Menu
          theme="dark"
          mode="horizontal"
          defaultSelectedKeys={selectedTopBarItem}
          items={topBarItems}
          style={{flex: 1, minWidth: 0}}
          onSelect={({key}) => {
            console.log(key)
            if (Object.keys(componentPage).indexOf(key) !== -1){
              console.log(key)
              setSelectedTopBarItem(key);
            }
          }}
        />
      </Header>
      <Layout>
        <Layout
          style={{
            padding: '0 24px 24px',
          }}
        >
          <Content
            style={{
              padding: 24,
              margin: 0,
              minHeight: 280,
              background: colorBgContainer,
              borderRadius: borderRadiusLG,
              overflow: 'scroll'
            }}
          >
            {componentPage[selectedTopBarItem]}
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
};
export default App;