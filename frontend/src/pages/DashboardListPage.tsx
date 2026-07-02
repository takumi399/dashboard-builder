import React, { useEffect, useState } from 'react';
import { Button, Card, List, Modal, Input, Typography, message, Empty, Space, Tag, Popconfirm } from 'antd';
import { PlusOutlined, DeleteOutlined, EyeOutlined, LogoutOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { dashboardService } from '../services/dashboard';

const { Title, Text } = Typography;

interface Dashboard {
  id: number; name: string; description: string; is_published: boolean;
  share_token: string | null; created_at: string; updated_at: string; chart_count?: number;
}

const DashboardListPage: React.FC = () => {
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [creating, setCreating] = useState(false);
  const user = useAuthStore(s => s.user);
  const logout = useAuthStore(s => s.logout);
  const navigate = useNavigate();

  const fetchDashboards = async () => {
    try {
      const data = await dashboardService.list();
      setDashboards(data);
    } catch { message.error('Failed to load dashboards'); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchDashboards(); }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await dashboardService.create({ name: newName, description: newDesc });
      message.success('Dashboard created');
      setModalOpen(false); setNewName(''); setNewDesc('');
      fetchDashboards();
    } catch { message.error('Failed to create'); }
    finally { setCreating(false); }
  };

  const handleDelete = async (id: number) => {
    try { await dashboardService.delete(id); message.success('Deleted'); fetchDashboards(); }
    catch { message.error('Delete failed'); }
  };

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>My Dashboards</Title>
        <Space>
          <Text>Welcome, {user?.username}</Text>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>New Dashboard</Button>
          <Button icon={<LogoutOutlined />} onClick={() => { logout(); navigate('/login'); }}>Logout</Button>
        </Space>
      </div>

      <List grid={{ gutter: 16, xs: 1, sm: 2, md: 3 }} loading={loading}
        dataSource={dashboards}
        locale={{ emptyText: <Empty description="No dashboards yet. Create your first one!" /> }}
        renderItem={d => (
          <List.Item>
            <Card
              hoverable
              actions={[
                <EyeOutlined key="view" onClick={() => navigate(`/editor/${d.id}`)} />,
                <Popconfirm key="del" title="Delete this dashboard?" onConfirm={() => handleDelete(d.id)}><DeleteOutlined /></Popconfirm>,
              ]}
            >
              <Card.Meta
                title={<Space>{d.name}{d.is_published && <Tag color="green">Published</Tag>}</Space>}
                description={
                  <div>
                    <Text type="secondary">{d.description || 'No description'}</Text>
                    <br /><Text type="secondary">{d.chart_count} charts</Text>
                  </div>
                }
              />
            </Card>
          </List.Item>
        )}
      />

      <Modal title="New Dashboard" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} confirmLoading={creating}>
        <Input placeholder="Dashboard name" value={newName} onChange={e => setNewName(e.target.value)} style={{ marginBottom: 12 }} />
        <Input.TextArea placeholder="Description (optional)" value={newDesc} onChange={e => setNewDesc(e.target.value)} rows={2} />
      </Modal>
    </div>
  );
};

export default DashboardListPage;
