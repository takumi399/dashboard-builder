import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button, Space, Typography, message, Spin, Select, Input, InputNumber, Empty } from 'antd';
import { SaveOutlined, EyeOutlined, ArrowLeftOutlined, BarChartOutlined, LineChartOutlined, PieChartOutlined } from '@ant-design/icons';
import { DndContext, useDraggable, useDroppable } from '@dnd-kit/core';
import type { DragEndEvent } from '@dnd-kit/core';
import ChartRenderer from '../components/charts/ChartRenderer';
import { dashboardService, chartService, dataSourceService } from '../services/dashboard';

const { Title, Text } = Typography;

interface ChartItem {
  id: number; dashboard_id: number; chart_type: string; title: string;
  position_x: number; position_y: number; width: number; height: number;
  data_source_id: number | null; config_json: string; query_config: string; sort_order: number;
}

// --- Palette item ---
const PaletteItem: React.FC<{ type: string; icon: React.ReactNode; label: string }> = ({ type, icon, label }) => {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({ id: `palette-${type}`, data: { chartType: type } });
  const style: React.CSSProperties = {
    transform: transform ? `translate(${transform.x}px, ${transform.y}px)` : undefined,
    padding: '12px 16px', marginBottom: 8, background: '#fff', borderRadius: 6, border: '1px solid #d9d9d9',
    cursor: 'grab', display: 'flex', alignItems: 'center', gap: 8, userSelect: 'none',
  };
  return <div ref={setNodeRef} style={style} {...listeners} {...attributes}>{icon} {label}</div>;
};

// --- Canvas ---
const Canvas: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { setNodeRef } = useDroppable({ id: 'canvas' });
  return (
    <div ref={setNodeRef} style={{ flex: 1, minHeight: 600, background: '#f5f5f5', borderRadius: 8, position: 'relative', overflow: 'auto', border: '2px dashed #d9d9d9' }}>
      {children}
    </div>
  );
};

// --- Draggable Chart on Canvas ---
const DraggableChart: React.FC<{ chart: ChartItem; dataSourceData: any; onClick: () => void }> = ({ chart, dataSourceData, onClick }) => {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({ id: `chart-${chart.id}` });
  const style: React.CSSProperties = {
    position: 'absolute', left: chart.position_x, top: chart.position_y, width: chart.width, height: chart.height,
    transform: transform ? `translate(${transform.x}px, ${transform.y}px)` : undefined,
    background: '#fff', borderRadius: 8, boxShadow: '0 2px 8px rgba(0,0,0,0.1)', overflow: 'hidden', cursor: 'move',
  };
  return (
    <div ref={setNodeRef} style={style} {...listeners} {...attributes} onClick={onClick}>
      <ChartRenderer chartType={chart.chart_type as any} title={chart.title} data={dataSourceData}
        queryConfig={JSON.parse(chart.query_config || '{}')} configJson={chart.config_json} />
    </div>
  );
};

// --- Main Editor Page ---
const DashboardEditorPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState<any>(null);
  const [charts, setCharts] = useState<ChartItem[]>([]);
  const [dataSources, setDataSources] = useState<any[]>([]);
  const [dataSourceData, setDataSourceData] = useState<Record<number, any>>({});
  const [loading, setLoading] = useState(true);
  const [selectedChart, setSelectedChart] = useState<ChartItem | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const d = await dashboardService.get(Number(id));
        setDashboard(d);
        setCharts(d.charts || []);
        const ds = await dataSourceService.list();
        setDataSources(ds);
        // Load data for charts
        const dataMap: Record<number, any> = {};
        for (const chart of d.charts || []) {
          if (chart.data_source_id && !dataMap[chart.data_source_id]) {
            try { dataMap[chart.data_source_id] = await dataSourceService.getData(chart.data_source_id); } catch {}
          }
        }
        setDataSourceData(dataMap);
      } catch { message.error('Failed to load dashboard'); navigate('/dashboards'); }
      finally { setLoading(false); }
    };
    load();
  }, [id]);

  const handleDragEnd = useCallback(async (event: DragEndEvent) => {
    const { active, over, delta } = event;
    if (!over) return;

    // Dropping from palette onto canvas
    if (String(active.id).startsWith('palette-') && over.id === 'canvas') {
      const chartType = active.data?.current?.chartType || 'bar';
      const names: Record<string,string> = { bar: 'Bar Chart', line: 'Line Chart', pie: 'Pie Chart' };
      try {
        const newChart = await chartService.create(Number(id), {
          chart_type: chartType, title: names[chartType] || 'New Chart',
          position_x: 50 + charts.length * 30, position_y: 50 + charts.length * 30,
          width: 400, height: 300,
        });
        setCharts(prev => [...prev, newChart]);
        message.success('Chart added');
      } catch { message.error('Failed to add chart'); }
      return;
    }

    // Moving existing chart
    if (String(active.id).startsWith('chart-')) {
      const chartId = Number(String(active.id).replace('chart-', ''));
      const chart = charts.find(c => c.id === chartId);
      if (!chart) return;
      const newX = Math.max(0, chart.position_x + delta.x);
      const newY = Math.max(0, chart.position_y + delta.y);
      setCharts(prev => prev.map(c => c.id === chartId ? { ...c, position_x: newX, position_y: newY } : c));
      try { await chartService.update(chartId, { position_x: newX, position_y: newY }); } catch {}
    }
  }, [charts, id]);

  const handleSave = async () => {
    setSaving(true);
    try {
      for (const chart of charts) {
        await chartService.update(chart.id, {
          position_x: chart.position_x, position_y: chart.position_y,
          width: chart.width, height: chart.height,
          data_source_id: chart.data_source_id, query_config: chart.query_config,
          config_json: chart.config_json, title: chart.title,
        });
      }
      message.success('Saved');
    } catch { message.error('Save failed'); }
    finally { setSaving(false); }
  };

  const handleChartPropertyUpdate = async (field: string, value: any) => {
    if (!selectedChart) return;
    const updated = { ...selectedChart, [field]: value };
    setSelectedChart(updated);
    setCharts(prev => prev.map(c => c.id === updated.id ? updated : c));
    try { await chartService.update(updated.id, { [field]: value }); } catch {}
  };

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 100 }}><Spin size="large" /></div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Toolbar */}
      <div style={{ padding: '8px 16px', borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#fff' }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/dashboards')}>Back</Button>
          <Title level={5} style={{ margin: 0 }}>{dashboard?.name}</Title>
        </Space>
        <Space>
          <Button icon={<SaveOutlined />} type="primary" onClick={handleSave} loading={saving}>Save</Button>
          <Button icon={<EyeOutlined />} onClick={async () => {
            try { const d = await dashboardService.publish(Number(id)); navigate(`/view/${d.share_token}`); }
            catch { message.error('Publish failed'); }
          }}>Publish</Button>
        </Space>
      </div>

      {/* Editor Body */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left Palette */}
        <div style={{ width: 160, padding: 12, borderRight: '1px solid #f0f0f0', background: '#fafafa' }}>
          <Text strong style={{ display: 'block', marginBottom: 8 }}>Charts</Text>
          <PaletteItem type="bar" icon={<BarChartOutlined />} label="Bar Chart" />
          <PaletteItem type="line" icon={<LineChartOutlined />} label="Line Chart" />
          <PaletteItem type="pie" icon={<PieChartOutlined />} label="Pie Chart" />
        </div>

        {/* Center Canvas */}
        <DndContext onDragEnd={handleDragEnd}>
          <Canvas>
            {charts.map(chart => (
              <DraggableChart key={chart.id} chart={chart} dataSourceData={dataSourceData[chart.data_source_id || 0]}
                onClick={() => setSelectedChart(chart)} />
            ))}
            {charts.length === 0 && (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#999' }}>
                <Empty description="Drag chart types from the left panel" />
              </div>
            )}
          </Canvas>
        </DndContext>

        {/* Right Property Panel */}
        <div style={{ width: 280, padding: 12, borderLeft: '1px solid #f0f0f0', background: '#fafafa', overflowY: 'auto' }}>
          {selectedChart ? (
            <>
              <Title level={5}>Chart Properties</Title>
              <div style={{ marginBottom: 12 }}>
                <Text>Title</Text>
                <Input value={selectedChart.title} onChange={e => handleChartPropertyUpdate('title', e.target.value)} style={{ marginTop: 4 }} />
              </div>
              <div style={{ marginBottom: 12 }}>
                <Text>Width</Text>
                <InputNumber value={selectedChart.width} onChange={v => handleChartPropertyUpdate('width', v)} min={200} max={1200} style={{ width: '100%', marginTop: 4 }} />
              </div>
              <div style={{ marginBottom: 12 }}>
                <Text>Height</Text>
                <InputNumber value={selectedChart.height} onChange={v => handleChartPropertyUpdate('height', v)} min={150} max={800} style={{ width: '100%', marginTop: 4 }} />
              </div>
              <div style={{ marginBottom: 12 }}>
                <Text>Data Source</Text>
                <Select value={selectedChart.data_source_id} onChange={v => handleChartPropertyUpdate('data_source_id', v)}
                  style={{ width: '100%', marginTop: 4 }} placeholder="Select data source" allowClear>
                  {dataSources.map(ds => <Select.Option key={ds.id} value={ds.id}>{ds.name}</Select.Option>)}
                </Select>
              </div>
              {selectedChart.data_source_id && (
                <>
                  <div style={{ marginBottom: 12 }}>
                    <Text>X / Category Column</Text>
                    <Select value={JSON.parse(selectedChart.query_config || '{}').xColumn}
                      onChange={v => handleChartPropertyUpdate('query_config', JSON.stringify({ ...JSON.parse(selectedChart.query_config || '{}'), xColumn: v }))}
                      style={{ width: '100%', marginTop: 4 }} placeholder="Select column">
                      {(dataSourceData[selectedChart.data_source_id]?.columns || []).map((col: string) => <Select.Option key={col} value={col}>{col}</Select.Option>)}
                    </Select>
                  </div>
                  <div style={{ marginBottom: 12 }}>
                    <Text>Y / Value Column</Text>
                    <Select value={JSON.parse(selectedChart.query_config || '{}').yColumn}
                      onChange={v => handleChartPropertyUpdate('query_config', JSON.stringify({ ...JSON.parse(selectedChart.query_config || '{}'), yColumn: v }))}
                      style={{ width: '100%', marginTop: 4 }} placeholder="Select column">
                      {(dataSourceData[selectedChart.data_source_id]?.columns || []).map((col: string) => <Select.Option key={col} value={col}>{col}</Select.Option>)}
                    </Select>
                  </div>
                </>
              )}
              <Button danger block onClick={async () => {
                try { await chartService.delete(selectedChart.id); setCharts(prev => prev.filter(c => c.id !== selectedChart.id)); setSelectedChart(null); message.success('Deleted'); }
                catch { message.error('Delete failed'); }
              }}>Delete Chart</Button>
            </>
          ) : (
            <div style={{ color: '#999', textAlign: 'center', marginTop: 40 }}>
              <Text type="secondary">Select a chart on the canvas to edit its properties</Text>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DashboardEditorPage;
