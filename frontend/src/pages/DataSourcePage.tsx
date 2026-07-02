import React, { useEffect, useState, useRef } from 'react';
import { Button, Table, Upload, Modal, Input, Typography, message, Space, Popconfirm, Tag } from 'antd';
import { UploadOutlined, DeleteOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
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

  useEffect(() => { fetchSources(); }, []);

  const handleUpload = async () => {
    if (!name.trim() || !fileRef.current) return;
    setUploading(true);
    try {
      await dataSourceService.upload(name, fileRef.current);
      message.success('Uploaded');
      setModalOpen(false); setName(''); fileRef.current = null;
      fetchSources();
    } catch (err: any) { message.error(err.response?.data?.detail || 'Upload failed'); }
    finally { setUploading(false); }
  };

  const handleDelete = async (id: number) => {
    try { await dataSourceService.delete(id); message.success('Deleted'); fetchSources(); }
    catch { message.error('Delete failed'); }
  };

  const columns = [
    { title: 'Name', dataIndex: 'name', key: 'name' },
    { title: 'Type', dataIndex: 'source_type', key: 'type', render: (t: string) => <Tag>{t.toUpperCase()}</Tag> },
    { title: 'Created', dataIndex: 'created_at', key: 'created', render: (d: string) => new Date(d).toLocaleDateString() },
    { title: 'Actions', key: 'actions', render: (_: any, record: any) => (
      <Space><Button size="small" onClick={() => message.info(`ID: ${record.id}`)}>View</Button>
      <Popconfirm title="Delete?" onConfirm={() => handleDelete(record.id)}><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm></Space>
    )},
  ];

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: 24 }}>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/dashboards')}>Back</Button>
        <Title level={3} style={{ margin: 0 }}>Data Sources</Title>
      </Space>
      <Button type="primary" icon={<UploadOutlined />} onClick={() => setModalOpen(true)} style={{ marginBottom: 16 }}>Upload CSV</Button>
      <Table dataSource={sources} columns={columns} rowKey="id" loading={loading} />

      <Modal title="Upload CSV" open={modalOpen} onOk={handleUpload} onCancel={() => setModalOpen(false)} confirmLoading={uploading}>
        <Input placeholder="Data source name" value={name} onChange={e => setName(e.target.value)} style={{ marginBottom: 12 }} />
        <Upload beforeUpload={file => { fileRef.current = file; return false; }} maxCount={1} accept=".csv">
          <Button icon={<UploadOutlined />}>Select CSV File</Button>
        </Upload>
      </Modal>
    </div>
  );
};

export default DataSourcePage;
