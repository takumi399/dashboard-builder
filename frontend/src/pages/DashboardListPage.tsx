import React, { useCallback, useEffect, useState, useMemo } from 'react';
import { Button, Card, Row, Col, Modal, Input, Typography, Empty, Space, Tag, Popconfirm, App, Pagination, Skeleton } from 'antd';
import { PlusOutlined, DeleteOutlined, EyeOutlined, LogoutOutlined, DatabaseOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import DOMPurify from 'dompurify';
import { useAuthStore } from '../store/authStore';
import { dashboardService } from '../services/dashboard';

const { Title, Text } = Typography;

const PAGE_SIZE = 9;

interface Dashboard {
  id: number; name: string; description: string; is_published: boolean;
  share_token: string | null; created_at: string; updated_at: string; chart_count?: number;
  role?: string;  // RBAC
}

const ROLE_LABELS: Record<string, { color: string; text: string }> = {
  owner: { color: 'blue', text: '拥有者' },
  editor: { color: 'green', text: '编辑者' },
  viewer: { color: 'default', text: '查看者' },
};

const DashboardListPage: React.FC = () => {
  const { message } = App.useApp();
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [creating, setCreating] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const user = useAuthStore(s => s.user);
  const logout = useAuthStore(s => s.logout);
  const navigate = useNavigate();

  const fetchDashboards = useCallback(async () => {
    try {
      const data = await dashboardService.list();
      setDashboards(data);
    } catch { message.error('加载看板失败'); }
    finally { setLoading(false); }
  }, [message]);

  useEffect(() => {
    if (!useAuthStore.getState().token) {
      navigate('/login');
      return;
    }
    fetchDashboards();
  }, [fetchDashboards, navigate]);

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

  // 分页计算
  const totalDashboards = dashboards.length;
  const paginatedDashboards = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return dashboards.slice(start, start + PAGE_SIZE);
  }, [dashboards, currentPage]);

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>我的看板</Title>
        <Space>
          <Text>欢迎，{DOMPurify.sanitize(user?.username || '')}</Text>
          <Button icon={<DatabaseOutlined />} onClick={() => navigate('/datasources')}>数据源</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建看板</Button>
          <Button icon={<LogoutOutlined />} onClick={() => { logout(); navigate('/login'); }}>退出登录</Button>
        </Space>
      </div>

      {loading ? (
        <div>
          <Skeleton active paragraph={{ rows: 1 }} style={{ marginBottom: 16 }} />
          <Row gutter={[16, 16]}>
            {[1, 2, 3].map(i => (
              <Col xs={24} sm={12} md={8} key={i}>
                <Card><Skeleton active paragraph={{ rows: 2 }} /></Card>
              </Col>
            ))}
          </Row>
        </div>
      ) : dashboards.length === 0 ? (
        <Empty description="还没有看板，创建第一个吧！" />
      ) : (
        <>
          <Row gutter={[16, 16]}>
            {paginatedDashboards.map(d => (
              <Col xs={24} sm={12} md={8} key={d.id}>
                <Card
                  hoverable
                  actions={[
                    <EyeOutlined key="view" onClick={() => navigate(`/editor/${d.id}`)} />,
                    <Popconfirm key="del" title="确定删除此看板？" onConfirm={() => handleDelete(d.id)}><DeleteOutlined /></Popconfirm>,
                  ]}
                >
                  <Card.Meta
                    title={
                      <Space>
                        {DOMPurify.sanitize(d.name)}
                        {d.is_published && <Tag color="green">已发布</Tag>}
                        {d.role && ROLE_LABELS[d.role] && (
                          <Tag color={ROLE_LABELS[d.role].color}>{ROLE_LABELS[d.role].text}</Tag>
                        )}
                      </Space>
                    }
                    description={
                      <div>
                        <Text type="secondary">{d.description || '暂无描述'}</Text>
                        <br /><Text type="secondary">{d.chart_count ?? 0} 个图表</Text>
                      </div>
                    }
                  />
                </Card>
              </Col>
            ))}
          </Row>
          {totalDashboards > PAGE_SIZE && (
            <div style={{ textAlign: 'center', marginTop: 24 }}>
              <Pagination
                current={currentPage}
                pageSize={PAGE_SIZE}
                total={totalDashboards}
                onChange={(page) => setCurrentPage(page)}
                showSizeChanger={false}
                showTotal={(total) => `共 ${total} 个看板`}
              />
            </div>
          )}
        </>
      )}

      <Modal title="新建看板" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} confirmLoading={creating}>
        <Input placeholder="看板名称" value={newName} onChange={e => setNewName(e.target.value)} style={{ marginBottom: 12 }} />
        <Input.TextArea placeholder="描述（可选）" value={newDesc} onChange={e => setNewDesc(e.target.value)} rows={2} />
      </Modal>
    </div>
  );
};

export default DashboardListPage;
