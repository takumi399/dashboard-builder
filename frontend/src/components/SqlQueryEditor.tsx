import React, { useEffect, useState, useCallback } from 'react';
import { Select, Button, Table, Typography, Space, App, Card, Tag, Empty } from 'antd';
import { PlayCircleOutlined, ThunderboltOutlined } from '@ant-design/icons';
import Editor from '@monaco-editor/react';
import { dataSourceService } from '../services/dashboard';
import type { SQLExecuteResult } from '../services/dashboard';
import type { DataSource } from '../services/dashboard';

const { Text } = Typography;

interface Props {
  /** 当用户点击"应用到图表"时回调，返回查询结果的 columns/rows */
  onApplyToChart?: (result: SQLExecuteResult) => void;
}

const SqlQueryEditor: React.FC<Props> = ({ onApplyToChart }) => {
  const { message } = App.useApp();
  const [sqlSources, setSqlSources] = useState<DataSource[]>([]);
  const [selectedDsId, setSelectedDsId] = useState<number | undefined>(undefined);
  const [query, setQuery] = useState<string>('SELECT 1');
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState<SQLExecuteResult | null>(null);

  // 加载所有 SQL 类型的数据源
  const loadSqlSources = useCallback(async () => {
    try {
      const all = await dataSourceService.list();
      setSqlSources(all.filter(ds => ds.source_type === 'sql'));
    } catch {
      // 静默
    }
  }, []);

  useEffect(() => {
    loadSqlSources();
  }, [loadSqlSources]);

  const handleExecute = async () => {
    if (!selectedDsId) {
      message.warning('请先选择数据源');
      return;
    }
    if (!query.trim()) {
      message.warning('请输入 SQL 查询');
      return;
    }
    setExecuting(true);
    try {
      const res = await dataSourceService.executeSql(selectedDsId, query.trim());
      setResult(res);
      message.success(`查询成功，返回 ${res.row_count} 行`);
    } catch (err: any) {
      setResult(null);
      message.error(err.response?.data?.detail || '查询执行失败');
    }
    finally {
      setExecuting(false);
    }
  };

  const handleApplyToChart = () => {
    if (result && onApplyToChart) {
      onApplyToChart(result);
      message.success('查询结果已应用到图表');
    }
  };

  // 构建 Ant Design Table 的列定义
  const tableColumns = result?.columns.map(col => ({
    title: col,
    dataIndex: col,
    key: col,
    ellipsis: true,
  })) || [];

  return (
    <Card
      title={<Space><ThunderboltOutlined /><span>SQL 查询编辑器</span></Space>}
      size="small"
      style={{ marginBottom: 16 }}
    >
      {/* 数据源选择 */}
      <div style={{ marginBottom: 12 }}>
        <Text strong style={{ display: 'block', marginBottom: 4 }}>数据源</Text>
        <Select
          value={selectedDsId}
          onChange={v => { setSelectedDsId(v); setResult(null); }}
          placeholder="选择 SQL 数据源"
          style={{ width: '100%' }}
          allowClear
          notFoundContent={<Empty description="暂无 SQL 数据源，请先在数据源管理中添加" />}
        >
          {sqlSources.map(ds => (
            <Select.Option key={ds.id} value={ds.id}>
              <Space>
                <Tag color="blue">SQL</Tag>
                {ds.name}
              </Space>
            </Select.Option>
          ))}
        </Select>
      </div>

      {/* Monaco 编辑器 */}
      <div style={{ marginBottom: 12, border: '1px solid #d9d9d9', borderRadius: 6, overflow: 'hidden' }}>
        <Editor
          height="200px"
          language="sql"
          theme="vs-dark"
          value={query}
          onChange={v => setQuery(v || '')}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            automaticLayout: true,
          }}
        />
      </div>

      {/* 操作按钮 */}
      <Space style={{ marginBottom: 12 }}>
        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          onClick={handleExecute}
          loading={executing}
          disabled={!selectedDsId}
        >
          执行查询
        </Button>
        {result && onApplyToChart && (
          <Button icon={<ThunderboltOutlined />} onClick={handleApplyToChart}>
            应用到图表
          </Button>
        )}
      </Space>

      {/* 查询结果 */}
      {result && (
        <div>
          <div style={{ marginBottom: 8 }}>
            <Text type="secondary">
              共 {result.row_count} 行 · {result.columns.length} 列
            </Text>
          </div>
          <Table
            columns={tableColumns}
            dataSource={result.rows.map((row, i) => ({ ...row, _key: i }))}
            rowKey="_key"
            size="small"
            bordered
            scroll={{ x: 'max-content', y: 300 }}
            pagination={result.row_count > 50 ? { pageSize: 50 } : false}
          />
        </div>
      )}
    </Card>
  );
};

export default SqlQueryEditor;
