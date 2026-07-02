import React, { useEffect, useState, useRef } from 'react';
import { Button, Table, Upload, Modal, Input, Typography, message, Space, Popconfirm, Tag } from 'antd';
import { UploadOutlined, DeleteOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { dataSourceService } from '../services/dashboard';

const { Title } = Typography;

const DataSourcePage: React.FC = () => {
  const [sources, setSources] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [name, setName] = useState('');
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<File | null>(null);
  const navigate = useNavigate();

  const fetchSources = async () => {
    try { setSources(await dataSourceService.list()); } catch {}
    finally { setLoading(false); }
  };

  useEffect(() => {
    if (!useAuthStore.getState().token) {
      navigate('/login');
      return;
    }
    fetchSources();
  }, []);

  const handleUpload = async () => {
    if (!name.trim() || !fileRef.current) return;
    setUploading(true);
    try {
      await dataSourceService.upload(name, fileRef.current);
      message.success('上传成功');
      setModalOpen(false); setName(''); fileRef.current = null;
      fetchSources();
    } catch (err: any) { message.error(err.response?.data?.detail || '上传失败'); }
    finally { setUploading(false); }
  };

  const handleDelete = async (id: number) => {
    try { await dataSourceService.delete(id); message.success('已删除'); fetchSources(); }
    catch { message.error('删除失败'); }
  };

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '类型', dataIndex: 'source_type', key: 'type', render: (t: string) => <Tag>{t.toUpperCase()}</Tag> },
    { title: '创建时间', dataIndex: 'created_at', key: 'created', render: (d: string) => new Date(d).toLocaleDateString() },
    { title: '操作', key: 'actions', render: (_: any, record: any) => (
      <Space><Button size="small" onClick={() => message.info(`ID：${record.id}`)}>查看</Button>
      <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm></Space>
    )},
  ];

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: 24 }}>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/dashboards')}>返回</Button>
        <Title level={3} style={{ margin: 0 }}>数据源管理</Title>
      </Space>
      <Button type="primary" icon={<UploadOutlined />} onClick={() => setModalOpen(true)} style={{ marginBottom: 16 }}>上传CSV文件</Button>
      <Table dataSource={sources} columns={columns} rowKey="id" loading={loading} />

      <Modal title="上传CSV文件" open={modalOpen} onOk={handleUpload} onCancel={() => setModalOpen(false)} confirmLoading={uploading}>
        <Input placeholder="数据源名称" value={name} onChange={e => setName(e.target.value)} style={{ marginBottom: 12 }} />
        <Upload beforeUpload={file => { fileRef.current = file; return false; }} maxCount={1} accept=".csv">
          <Button icon={<UploadOutlined />}>选择CSV文件</Button>
        </Upload>
      </Modal>
    </div>
  );
};

export default DataSourcePage;
