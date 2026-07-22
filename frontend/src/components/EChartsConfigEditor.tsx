import React, { useState, useMemo, useEffect } from 'react';
import { Modal, Button, Space, App, Tabs } from 'antd';
import { CodeOutlined, EyeOutlined } from '@ant-design/icons';
import Editor from '@monaco-editor/react';
import ReactECharts from 'echarts-for-react';
import type { ChartData } from '../services/dashboard';

const numericValue = (value: unknown) => Number.parseFloat(String(value ?? '')) || 0;

interface EChartsConfigEditorProps {
  open: boolean;
  onClose: () => void;
  title: string;
  chartType: string;
  configJson: string;
  data?: ChartData;
  queryConfig?: { xColumn?: string; yColumn?: string; nameColumn?: string; valueColumn?: string };
  onSave: (newConfigJson: string) => void;
}

const EChartsConfigEditor: React.FC<EChartsConfigEditorProps> = ({
  open, onClose, title, chartType, configJson, data, queryConfig, onSave,
}) => {
  const { message } = App.useApp();

  // 生成当前图表的默认 ECharts option（不含用户自定义覆盖）
  const defaultOption = useMemo(() => {
    const rows = data?.rows || [];
    const columns = data?.columns || [];
    const xCol = queryConfig?.xColumn || columns[0] || '分类';
    const nameCol = queryConfig?.nameColumn || columns[0] || '分类';
    const valueCol = queryConfig?.valueColumn || columns[1] || '数值';

    const xData = rows.map(r => r[xCol] || '');
    const yData = rows.map(r => numericValue(r[valueCol]));

    const base: any = {
      title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
      tooltip: {},
    };

    if (chartType === 'bar') {
      return { ...base, xAxis: { type: 'category', data: xData }, yAxis: { type: 'value' }, series: [{ type: 'bar', data: yData }] };
    }
    if (chartType === 'line') {
      return { ...base, xAxis: { type: 'category', data: xData }, yAxis: { type: 'value' }, series: [{ type: 'line', data: yData, smooth: true }] };
    }
    if (chartType === 'pie') {
      return { ...base, series: [{ type: 'pie', data: rows.map(r => ({ name: r[nameCol], value: numericValue(r[valueCol]) })) }] };
    }
    if (chartType === 'scatter') {
      return { ...base, xAxis: { type: 'value' }, yAxis: { type: 'value' }, series: [{ type: 'scatter', data: rows.map(r => [numericValue(r[xCol]), numericValue(r[valueCol])]) }] };
    }
    if (chartType === 'heatmap') {
      const xCats = [...new Set(rows.map(r => r[xCol] || ''))];
      const yCats = [...new Set(rows.map(r => r[valueCol] || ''))];
      const hd: [number, number, number][] = [];
      rows.forEach(r => { const xi = xCats.indexOf(r[xCol] || ''); const yi = yCats.indexOf(r[valueCol] || ''); if (xi >= 0 && yi >= 0) hd.push([xi, yi, numericValue(r[columns[1]])]); });
      return { ...base, xAxis: { type: 'category', data: xCats }, yAxis: { type: 'category', data: yCats }, visualMap: { min: 0, max: 100 }, series: [{ type: 'heatmap', data: hd }] };
    }
    if (chartType === 'radar') {
      const inds = rows.map(r => ({ name: r[nameCol] || '', max: Math.max(...rows.map(r2 => numericValue(r2[valueCol]))) * 1.2 }));
      return { ...base, radar: { indicator: inds }, series: [{ type: 'radar', data: [{ value: rows.map(r => numericValue(r[valueCol])) }] }] };
    }
    if (chartType === 'funnel') {
      return { ...base, series: [{ type: 'funnel', data: rows.map(r => ({ name: r[nameCol], value: numericValue(r[valueCol]) })) }] };
    }
    return base;
  }, [chartType, title, data, queryConfig]);

  // 用户编辑的 JSON 文本
  const [editorText, setEditorText] = useState('');

  // 合并选项：默认配置 + 用户自定义覆盖
  const mergedOption = useMemo(() => {
    if (!editorText.trim()) return defaultOption;
    try {
      const custom = JSON.parse(editorText);
      return { ...defaultOption, ...custom };
    } catch {
      return defaultOption;
    }
  }, [defaultOption, editorText]);

  // 解析后的 JSON 是否有效
  const isValidJson = useMemo(() => {
    if (!editorText.trim()) return true;
    try { JSON.parse(editorText); return true; } catch { return false; }
  }, [editorText]);

  // 打开弹窗时，用 configJson 初始化编辑器
  useEffect(() => {
    if (open) {
      try {
        const parsed = JSON.parse(configJson || '{}');
        setEditorText(JSON.stringify(parsed, null, 2));
      } catch {
        setEditorText(configJson || '{}');
      }
    }
  }, [open, configJson]);

  const handleSave = () => {
    if (!isValidJson) {
      message.error('JSON 格式无效，请修正后再保存');
      return;
    }
    onSave(editorText);
    message.success('高级配置已保存');
    onClose();
  };

  const tabItems = [
    {
      key: 'editor',
      label: <span><CodeOutlined /> JSON 编辑</span>,
      children: (
        <div style={{ height: 450 }}>
          <Editor
            height="100%"
            defaultLanguage="json"
            value={editorText}
            onChange={(val) => setEditorText(val || '')}
            theme="vs-dark"
            options={{
              minimap: { enabled: false },
              fontSize: 13,
              tabSize: 2,
              formatOnPaste: true,
              formatOnType: true,
              scrollBeyondLastLine: false,
            }}
          />
          {!isValidJson && (
            <div style={{ color: '#ff4d4f', marginTop: 4, fontSize: 12 }}>⚠ JSON 格式无效</div>
          )}
        </div>
      ),
    },
    {
      key: 'preview',
      label: <span><EyeOutlined /> 预览</span>,
      children: (
        <div style={{ height: 450, padding: 8, background: '#fafafa', borderRadius: 6 }}>
          <ReactECharts option={mergedOption} style={{ width: '100%', height: '100%' }} opts={{ renderer: 'canvas' }} />
        </div>
      ),
    },
  ];

  return (
    <Modal
      title={`高级配置 - ${title}`}
      open={open}
      onCancel={onClose}
      width={800}
      footer={
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" onClick={handleSave} disabled={!isValidJson}>保存配置</Button>
        </Space>
      }
      destroyOnClose
    >
      <div style={{ marginBottom: 12 }}>
        <span style={{ color: '#666', fontSize: 12 }}>
          编辑 ECharts option JSON 来覆盖默认图表配置。编辑后的配置会与默认配置合并。
        </span>
      </div>
      <Tabs items={tabItems} />
    </Modal>
  );
};

export default EChartsConfigEditor;
