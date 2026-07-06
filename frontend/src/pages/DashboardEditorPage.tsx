import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button, Space, Typography, Spin, Select, Input, InputNumber, Empty, App, Drawer } from 'antd';
import { SaveOutlined, EyeOutlined, ArrowLeftOutlined, BarChartOutlined, LineChartOutlined, PieChartOutlined, NumberOutlined, TableOutlined, CodeOutlined } from '@ant-design/icons';
import { DndContext, useDraggable, useDroppable, useSensor, useSensors, PointerSensor } from '@dnd-kit/core';
import type { DragEndEvent } from '@dnd-kit/core';
import { Rnd } from 'react-rnd';
import ChartRenderer from '../components/charts/ChartRenderer';
import SqlQueryEditor from '../components/SqlQueryEditor';
import { dashboardService, chartService, dataSourceService, SQLExecuteResult } from '../services/dashboard';

const { Title, Text } = Typography;

interface ChartItem {
  id: number; dashboard_id: number; chart_type: string; title: string;
  position_x: number; position_y: number; width: number; height: number;
  data_source_id: number | null; config_json: string; query_config: string; sort_order: number;
}

// --- 面板项 ---
const PaletteItem: React.FC<{ type: string; icon: React.ReactNode; label: string }> = ({ type, icon, label }) => {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({ id: `palette-${type}`, data: { chartType: type } });
  const style: React.CSSProperties = {
    transform: transform ? `translate(${transform.x}px, ${transform.y}px)` : undefined,
    padding: '12px 16px', marginBottom: 8, background: '#fff', borderRadius: 6, border: '1px solid #d9d9d9',
    cursor: 'grab', display: 'flex', alignItems: 'center', gap: 8, userSelect: 'none',
  };
  return <div ref={setNodeRef} style={style} {...listeners} {...attributes}>{icon} {label}</div>;
};

// --- 画布 ---
const Canvas: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { setNodeRef } = useDroppable({ id: 'canvas' });
  return (
    <div ref={setNodeRef} style={{ flex: 1, minHeight: 600, background: '#f5f5f5', borderRadius: 8, position: 'relative', overflow: 'auto', border: '2px dashed #d9d9d9' }}>
      {children}
    </div>
  );
};

// --- 画布上的图表 (使用 react-rnd 支持拖拽+缩放) ---
const DraggableChart: React.FC<{
  chart: ChartItem;
  dataSourceData: any;
  onClick: () => void;
  onResize: (id: number, width: number, height: number, x?: number, y?: number) => void;
  onMove: (id: number, x: number, y: number) => void;
}> = ({ chart, dataSourceData, onClick, onResize, onMove }) => {
  return (
    <Rnd
      position={{ x: chart.position_x, y: chart.position_y }}
      size={{ width: chart.width, height: chart.height }}
      minWidth={200}
      minHeight={150}
      bounds="parent"
      enableResizing={{
        top: false, right: false, bottom: false, left: false,
        topRight: false, bottomRight: true, bottomLeft: false, topLeft: false,
      }}
      onDragStop={(_e, d) => {
        onMove(chart.id, d.x, d.y);
      }}
      onResizeStop={(_e, _direction, ref, _delta, position) => {
        onResize(
          chart.id,
          parseInt(ref.style.width, 10),
          parseInt(ref.style.height, 10),
          position.x,
          position.y,
        );
      }}
      onClick={onClick}
      style={{
        background: '#fff',
        borderRadius: 8,
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        overflow: 'hidden',
      }}
    >
      <div style={{ width: '100%', height: '100%', position: 'relative' }}>
        <ChartRenderer
          chartType={chart.chart_type as any}
          title={chart.title}
          data={dataSourceData}
          queryConfig={JSON.parse(chart.query_config || '{}')}
          configJson={chart.config_json}
        />
      </div>
    </Rnd>
  );
};

// --- 编辑器主页面 ---
const DashboardEditorPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState<any>(null);
  const [charts, setCharts] = useState<ChartItem[]>([]);
  const [dataSources, setDataSources] = useState<any[]>([]);
  const [dataSourceData, setDataSourceData] = useState<Record<number, any>>({});
  const [loading, setLoading] = useState(true);
  const [selectedChart, setSelectedChart] = useState<ChartItem | null>(null);
  const [saving, setSaving] = useState(false);

  // ── SQL 查询相关状态 ──
  const [sqlDrawerOpen, setSqlDrawerOpen] = useState(false);
  const [appliedSqlData, setAppliedSqlData] = useState<Record<number, SQLExecuteResult>>({});

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  useEffect(() => {
    const load = async () => {
      try {
        const d = await dashboardService.get(Number(id));
        setDashboard(d);
        setCharts(d.charts || []);
        const ds = await dataSourceService.list();
        setDataSources(ds);
        // 加载图表绑定的数据
        const dataMap: Record<number, any> = {};
        for (const chart of d.charts || []) {
          if (chart.data_source_id && !dataMap[chart.data_source_id]) {
            try { dataMap[chart.data_source_id] = await dataSourceService.getData(chart.data_source_id); } catch {}
          }
        }
        setDataSourceData(dataMap);
      } catch { message.error('加载看板失败'); navigate('/dashboards'); }
      finally { setLoading(false); }
    };
    load();
  }, [id]);

  const handleDragEnd = useCallback(async (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over) return;

    // 从面板拖到画布
    if (String(active.id).startsWith('palette-') && over.id === 'canvas') {
      const chartType = active.data?.current?.chartType || 'bar';
      const names: Record<string,string> = { bar: '柱状图', line: '折线图', pie: '饼图', card: '指标卡', table: '数据表' };
      try {
        const newChart = await chartService.create(Number(id), {
          chart_type: chartType, title: names[chartType] || '新图表',
          position_x: 50 + charts.length * 30, position_y: 50 + charts.length * 30,
          width: 400, height: 300,
        });
        setCharts(prev => [...prev, newChart]);
        message.success('图表已添加');
      } catch { message.error('添加图表失败'); }
      return;
    }

    // 注意: 图表拖拽/缩放现由 react-rnd 的 Rnd 组件处理, 不再走 @dnd-kit
  }, [charts, id]);

  const handleMove = useCallback((chartId: number, x: number, y: number) => {
    setCharts(prev => prev.map(c => c.id === chartId ? { ...c, position_x: x, position_y: y } : c));
    chartService.update(chartId, { position_x: x, position_y: y }).catch(() => {});
  }, []);

  const handleResize = useCallback((chartId: number, newW: number, newH: number, x?: number, y?: number) => {
    setCharts(prev => prev.map(c => {
      if (c.id !== chartId) return c;
      const updated = { ...c, width: newW, height: newH };
      if (x !== undefined) updated.position_x = x;
      if (y !== undefined) updated.position_y = y;
      return updated;
    }));
    const payload: any = { width: newW, height: newH };
    if (x !== undefined) payload.position_x = x;
    if (y !== undefined) payload.position_y = y;
    chartService.update(chartId, payload).catch(() => {});
  }, []);

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
      message.success('保存成功');
    } catch { message.error('保存失败'); }
    finally { setSaving(false); }
  };

  const handleChartPropertyUpdate = async (field: string, value: any) => {
    if (!selectedChart) return;
    const updated = { ...selectedChart, [field]: value };
    setSelectedChart(updated);
    setCharts(prev => prev.map(c => c.id === updated.id ? updated : c));
    try { await chartService.update(updated.id, { [field]: value }); } catch {}

    // 切换数据源时立即加载数据
    if (field === 'data_source_id' && value) {
      try {
        const data = await dataSourceService.getData(value);
        setDataSourceData(prev => ({ ...prev, [value]: data }));
      } catch {}
    }
  };

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 100 }}><Spin size="large" /></div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* 工具栏 */}
      <div style={{ padding: '8px 16px', borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#fff' }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/dashboards')}>返回</Button>
          <Title level={5} style={{ margin: 0 }}>{dashboard?.name}</Title>
        </Space>
        <Space>
          <Button icon={<CodeOutlined />} onClick={() => setSqlDrawerOpen(true)}>SQL 查询</Button>
          <Button icon={<SaveOutlined />} type="primary" onClick={handleSave} loading={saving}>保存</Button>
          <Button icon={<EyeOutlined />} onClick={async () => {
            try { const d = await dashboardService.publish(Number(id)); navigate(`/view/${d.share_token}`); }
            catch { message.error('发布失败'); }
          }}>发布</Button>
        </Space>
      </div>

      {/* 编辑器主体 */}
      <DndContext onDragEnd={handleDragEnd} sensors={sensors}>
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          {/* 左侧图表面板 */}
          <div style={{ width: 160, padding: 12, borderRight: '1px solid #f0f0f0', background: '#fafafa' }}>
            <Text strong style={{ display: 'block', marginBottom: 8 }}>图表类型</Text>
            <PaletteItem type="bar" icon={<BarChartOutlined />} label="柱状图" />
            <PaletteItem type="line" icon={<LineChartOutlined />} label="折线图" />
            <PaletteItem type="pie" icon={<PieChartOutlined />} label="饼图" />
            <PaletteItem type="card" icon={<NumberOutlined />} label="指标卡" />
            <PaletteItem type="table" icon={<TableOutlined />} label="数据表" />
          </div>

          {/* 中间画布 */}
          <Canvas>
            {charts.map(chart => {
              // 合并：优先使用 SQL 查询结果，其次使用数据源数据
              const sqlData = selectedChart?.id === chart.id ? appliedSqlData[chart.id] : undefined;
              const chartData = sqlData
                ? { columns: sqlData.columns, rows: sqlData.rows }
                : dataSourceData[chart.data_source_id || 0];
              return (
                <DraggableChart key={chart.id} chart={chart} dataSourceData={chartData}
                  onClick={() => setSelectedChart(chart)} onResize={handleResize} onMove={handleMove} />
              );
            })}
            {charts.length === 0 && (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#999' }}>
                <Empty description="从左侧拖拽图表到画布" />
              </div>
            )}
          </Canvas>

          {/* 右侧属性面板 */}
          <div style={{ width: 280, padding: 12, borderLeft: '1px solid #f0f0f0', background: '#fafafa', overflowY: 'auto' }}>
          {selectedChart ? (
            <>
              <Title level={5}>图表属性</Title>
              <div style={{ marginBottom: 12 }}>
                <Text>标题</Text>
                <Input value={selectedChart.title} onChange={e => handleChartPropertyUpdate('title', e.target.value)} style={{ marginTop: 4 }} />
              </div>
              <div style={{ marginBottom: 12 }}>
                <Text>宽度</Text>
                <InputNumber value={selectedChart.width} onChange={v => handleChartPropertyUpdate('width', v)} min={200} max={1200} style={{ width: '100%', marginTop: 4 }} />
              </div>
              <div style={{ marginBottom: 12 }}>
                <Text>高度</Text>
                <InputNumber value={selectedChart.height} onChange={v => handleChartPropertyUpdate('height', v)} min={150} max={800} style={{ width: '100%', marginTop: 4 }} />
              </div>
              <div style={{ marginBottom: 12 }}>
                <Text>数据源</Text>
                <Select value={selectedChart.data_source_id} onChange={v => handleChartPropertyUpdate('data_source_id', v)}
                  style={{ width: '100%', marginTop: 4 }} placeholder="选择数据源" allowClear>
                  {dataSources.map(ds => <Select.Option key={ds.id} value={ds.id}>{ds.name}</Select.Option>)}
                </Select>
              </div>
              {selectedChart.data_source_id && (() => {
                const dsColumns = dataSourceData[selectedChart.data_source_id]?.columns || [];
                const sqlColumns = appliedSqlData[selectedChart.id]?.columns || [];
                const allColumns = [...new Set([...dsColumns, ...sqlColumns])];
                return (
                <>
                  <div style={{ marginBottom: 12 }}>
                    <Text>X轴/分类字段</Text>
                    <Select value={JSON.parse(selectedChart.query_config || '{}').xColumn}
                      onChange={v => handleChartPropertyUpdate('query_config', JSON.stringify({ ...JSON.parse(selectedChart.query_config || '{}'), xColumn: v }))}
                      style={{ width: '100%', marginTop: 4 }} placeholder="选择字段">
                      {allColumns.map((col: string) => <Select.Option key={col} value={col}>{col}</Select.Option>)}
                    </Select>
                  </div>
                  <div style={{ marginBottom: 12 }}>
                    <Text>Y轴/数值字段</Text>
                    <Select value={JSON.parse(selectedChart.query_config || '{}').yColumn}
                      onChange={v => handleChartPropertyUpdate('query_config', JSON.stringify({ ...JSON.parse(selectedChart.query_config || '{}'), yColumn: v }))}
                      style={{ width: '100%', marginTop: 4 }} placeholder="选择字段">
                      {allColumns.map((col: string) => <Select.Option key={col} value={col}>{col}</Select.Option>)}
                    </Select>
                  </div>
                </>
                );
              })()}
              <Button danger block onClick={async () => {
                try { await chartService.delete(selectedChart.id); setCharts(prev => prev.filter(c => c.id !== selectedChart.id)); setSelectedChart(null); message.success('已删除'); }
                catch { message.error('删除失败'); }
              }}>删除图表</Button>
            </>
          ) : (
            <div style={{ color: '#999', textAlign: 'center', marginTop: 40 }}>
              <Text type="secondary">点击画布上的图表来编辑属性</Text>
            </div>
          )}
        </div>
        </div>
      </DndContext>

        {/* SQL 查询 Drawer */}
        <Drawer
          title="SQL 查询"
          open={sqlDrawerOpen}
          onClose={() => setSqlDrawerOpen(false)}
          width={700}
          destroyOnClose={false}
        >
          <SqlQueryEditor
            onApplyToChart={(sqlResult) => {
              if (selectedChart) {
                setAppliedSqlData(prev => ({ ...prev, [selectedChart.id]: sqlResult }));
                message.success(`已将查询结果应用到图表「${selectedChart.title}」`);
              } else {
                message.warning('请先在画布上选择一个图表');
              }
            }}
          />
        </Drawer>
      </div>
    </div>
  );
};

export default DashboardEditorPage;
