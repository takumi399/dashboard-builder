import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, App as AntdApp } from 'antd';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardListPage from './pages/DashboardListPage';
import DataSourcePage from './pages/DataSourcePage';
import DashboardEditorPage from './pages/DashboardEditorPage';
import DashboardViewPage from './pages/DashboardViewPage';

const App: React.FC = () => {
  return (
    <ConfigProvider theme={{ token: { colorPrimary: '#1677ff' } }}>
      <AntdApp>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/dashboards" element={<DashboardListPage />} />
            <Route path="/datasources" element={<DataSourcePage />} />
            <Route path="/editor/:id" element={<DashboardEditorPage />} />
            <Route path="/view/:token" element={<DashboardViewPage />} />
            <Route path="/" element={<Navigate to="/dashboards" replace />} />
            <Route path="*" element={<Navigate to="/dashboards" replace />} />
          </Routes>
        </BrowserRouter>
      </AntdApp>
    </ConfigProvider>
  );
};

export default App;
