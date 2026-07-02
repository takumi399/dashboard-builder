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
    } catch { message.error('加载看板失败'); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    if (!useAuthStore.getState().token) {
      navigate('/login');
      return;
    }
    fetchDashboards();
  }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await dashboardService.create({ name: newName, description: newDesc });
      message.success('看板创建成功');
      setModalOpen(false); setNewName(''); setNewDesc('');
      fetchDashboards();
    } catch { message.error('创建失败'); }
    finally { setCreating(false); }
  };

  const handleDelete = async (id: number) => {
    try { await dashboardService.delete(id); message.success('已删除'); fetchDashboards(); }
    catch { message.error('删除失败'); }
  };

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>我的看板</Title>
        <Space>
          <Text>欢迎，{user?.username}</Text>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建看板</Button>
          <Button icon={<LogoutOutlined />} onClick={() => { logout(); navigate('/login'); }}>退出登录</Button>
        </Space>
      </div>

      <List grid={{ gutter: 16, xs: 1, sm: 2, md: 3 }} loading={loading}
        dataSource={dashboards}
        locale={{ emptyText: <Empty description="还没有看板，创建第一个吧！" /> }}
        renderItem={d => (
          <List.Item>
            <Card
              hoverable
              actions={[
                <EyeOutlined key="view" onClick={() => navigate(`/editor/${d.id}`)} />,
                <Popconfirm key="del" title="确定删除此看板？" onConfirm={() => handleDelete(d.id)}><DeleteOutlined /></Popconfirm>,
              ]}
            >
              <Card.Meta
                title={<Space>{d.name}{d.is_published && <Tag color="green">已发布</Tag>}</Space>}
                description={
                  <div>
                    <Text type="secondary">{d.description || '暂无描述'}</Text>
                    <br /><Text type="secondary">{d.chart_count} 个图表</Text>
                  </div>
                }
              />
            </Card>
          </List.Item>
        )}
      />

      <Modal title="新建看板" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} confirmLoading={creating}>
        <Input placeholder="看板名称" value={newName} onChange={e => setNewName(e.target.value)} style={{ marginBottom: 12 }} />
        <Input.TextArea placeholder="描述（可选）" value={newDesc} onChange={e => setNewDesc(e.target.value)} rows={2} />
      </Modal>
    </div>
  );
};

export default DashboardListPage;
