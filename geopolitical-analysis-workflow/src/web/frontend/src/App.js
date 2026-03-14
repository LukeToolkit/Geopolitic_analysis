import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { Layout, Menu, ConfigProvider, theme } from 'antd';
import {
  DashboardOutlined,
  LineChartOutlined,
  GlobalOutlined,
  DatabaseOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import './App.css';

const { Header, Sider, Content } = Layout;

// 页面组件
const Dashboard = () => (
  <div>
    <h1>地缘政治分析仪表板</h1>
    <p>欢迎使用地缘政治分析AI工作流系统</p>
  </div>
);

const DataView = () => <div><h1>数据视图</h1></div>;
const AnalysisView = () => <div><h1>分析视图</h1></div>;
const PredictionsView = () => <div><h1>预测视图</h1></div>;
const SettingsView = () => <div><h1>系统设置</h1></div>;

function App() {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#1890ff',
        },
      }}
    >
      <Router>
        <Layout style={{ minHeight: '100vh' }}>
          <Sider collapsible>
            <div className="logo">
              <h2 style={{ color: 'white', textAlign: 'center', padding: '16px' }}>
                地缘分析
              </h2>
            </div>
            <Menu theme="dark" mode="inline" defaultSelectedKeys={['1']}>
              <Menu.Item key="1" icon={<DashboardOutlined />}>
                <Link to="/">仪表板</Link>
              </Menu.Item>
              <Menu.Item key="2" icon={<DatabaseOutlined />}>
                <Link to="/data">数据管理</Link>
              </Menu.Item>
              <Menu.Item key="3" icon={<GlobalOutlined />}>
                <Link to="/analysis">地缘分析</Link>
              </Menu.Item>
              <Menu.Item key="4" icon={<LineChartOutlined />}>
                <Link to="/predictions">预测结果</Link>
              </Menu.Item>
              <Menu.Item key="5" icon={<SettingOutlined />}>
                <Link to="/settings">系统设置</Link>
              </Menu.Item>
            </Menu>
          </Sider>
          <Layout>
            <Header style={{ background: '#001529', padding: '0 24px' }}>
              <h1 style={{ color: 'white', margin: 0 }}>地缘政治分析AI工作流系统</h1>
            </Header>
            <Content style={{ margin: '24px 16px', padding: 24, background: '#fff', minHeight: 280 }}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/data" element={<DataView />} />
                <Route path="/analysis" element={<AnalysisView />} />
                <Route path="/predictions" element={<PredictionsView />} />
                <Route path="/settings" element={<SettingsView />} />
              </Routes>
            </Content>
          </Layout>
        </Layout>
      </Router>
    </ConfigProvider>
  );
}

export default App;