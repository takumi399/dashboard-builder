import React, { useEffect, useState, useRef } from 'react';
import { Button, Table, Upload, Modal, Input, Typography, Space, Popconfirm, Tag, App, Tabs, Select, InputNumber, Form, Card } from 'antd';
import { UploadOutlined, DeleteOutlined, ArrowLeftOutlined, DatabaseOutlined, FileTextOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { dataSourceService } from '../services/dashboard';

const { Title } = Typography;

const DataSourcePage: React.FC = () => {
  const { message } = App.useApp();
  const [sources, setSources] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [name, setName] = useState('');
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<File | null>(null);
  const navigate = useNavigate();

  // ── SQL 连接表单状态 ──
  const [sqlForm] = Form.useForm();
  const [submittingSql, setSubmittingSql] = useState(false);

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

  const handleSqlSubmit = async () => {
    try {
      const values = await sqlForm.validateFields();
      setSubmittingSql(true);
      const connectionConfig = {
        db_type: values.db_type,
        host: values.host || undefined,
        port: values.port || undefined,
        database: values.database || undefined,
        username: values.username || undefined,
        password: values.password || undefined,
      };
      await dataSourceService.create({
        name: values.name,
        source_type: 'sql',
        connection_config: JSON.stringify(connectionConfig),
      });
      message.success('数据库连接已添加');
      sqlForm.resetFields();
      fetchSources();
    } catch (err: any) {
      if (err.errorFields) return; // 表单校验错误，不提示
      message.error(err.response?.data?.detail || '添加失败');
    }
    finally { setSubmittingSql(false); }
  };

  const handleDelete = async (id: number) => {
    try { await dataSourceService.delete(id); message.success('已删除'); fetchSources(); }
    catch { message.error('删除失败'); }
  };

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '类型', dataIndex: 'source_type', key: 'type', render: (t: string) => <Tag color={t === 'sql' ? 'blue' : 'green'}>{t.toUpperCase()}</Tag> },
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

      <Tabs
        defaultActiveKey="create"
        items={[
          {
            key: 'create',
            label: '添加数据源',
            children: (
              <Tabs
                items={[
                  {
                    key: 'csv',
                    label: <span><FileTextOutlined /> CSV 上传</span>,
                    children: (
                      <Card style={{ maxWidth: 500 }}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Input
                            placeholder="数据源名称"
                            value={name}
                            onChange={e => setName(e.target.value)}
                          />
                          <Upload
                            beforeUpload={file => { fileRef.current = file; return false; }}
                            maxCount={1}
                            accept=".csv"
                            fileList={fileRef.current ? [{ uid: '-1', name: fileRef.current.name, status: 'done' } as any] : []}
                            onRemove={() => { fileRef.current = null; }}
                          >
                            <Button icon={<UploadOutlined />}>选择CSV文件</Button>
                          </Upload>
                          <Button
                            type="primary"
                            onClick={handleUpload}
                            loading={uploading}
                            disabled={!name.trim() || !fileRef.current}
                          >
                            上传
                          </Button>
                        </Space>
                      </Card>
                    ),
                  },
                  {
                    key: 'sql',
                    label: <span><DatabaseOutlined /> 数据库连接</span>,
                    children: (
                      <Card style={{ maxWidth: 500 }}>
                        <Form form={sqlForm} layout="vertical" onFinish={handleSqlSubmit}>
                          <Form.Item name="name" label="数据源名称" rules={[{ required: true, message: '请输入名称' }]}>
                            <Input placeholder="例如：生产数据库" />
                          </Form.Item>
                          <Form.Item name="db_type" label="数据库类型" rules={[{ required: true, message: '请选择数据库类型' }]}>
                            <Select placeholder="选择数据库类型">
                              <Select.Option value="sqlite">SQLite</Select.Option>
                              <Select.Option value="mysql">MySQL</Select.Option>
                              <Select.Option value="postgresql">PostgreSQL</Select.Option>
                            </Select>
                          </Form.Item>
                          <Form.Item noStyle shouldUpdate={(prev, cur) => prev.db_type !== cur.db_type}>
                            {({ getFieldValue }) => {
                              const dbType = getFieldValue('db_type');
                              const showNetwork = dbType === 'mysql' || dbType === 'postgresql';
                              return (
                                <>
                                  {showNetwork && (
                                    <>
                                      <Form.Item name="host" label="主机">
                                        <Input placeholder="localhost" />
                                      </Form.Item>
                                      <Form.Item name="port" label="端口">
                                        <InputNumber
                                          placeholder={dbType === 'mysql' ? '3306' : '5432'}
                                          min={1} max={65535}
                                          style={{ width: '100%' }}
                                        />
                                      </Form.Item>
                                      <Form.Item name="username" label="用户名">
                                        <Input placeholder="用户名" />
                                      </Form.Item>
                                      <Form.Item name="password" label="密码">
                                        <Input.Password placeholder="密码" />
                                      </Form.Item>
                                    </>
                                  )}
                                  <Form.Item
                                    name="database"
                                    label={dbType === 'sqlite' ? '数据库文件路径' : '数据库名'}
                                    rules={[{ required: true, message: '请输入数据库名或路径' }]}
                                  >
                                    <Input placeholder={dbType === 'sqlite' ? ':memory: 或 /path/to/db.sqlite' : '数据库名'} />
                                  </Form.Item>
                                </>
                              );
                            }}
                          </Form.Item>
                          <Form.Item>
                            <Button type="primary" htmlType="submit" loading={submittingSql} icon={<DatabaseOutlined />}>
                              添加数据库连接
                            </Button>
                          </Form.Item>
                        </Form>
                      </Card>
                    ),
                  },
                ]}
              />
            ),
          },
          {
            key: 'list',
            label: `已有数据源 (${sources.length})`,
            children: (
              <Table dataSource={sources} columns={columns} rowKey="id" loading={loading} />
            ),
          },
        ]}
      />
    </div>
  );
};

export default DataSourcePage;
