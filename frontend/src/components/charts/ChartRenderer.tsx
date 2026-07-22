import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { Table, Statistic, Card } from 'antd';
import type { ChartData, ChartType } from '../../services/dashboard';

interface ChartRendererProps {
  chartType: ChartType;
  title: string;
  data?: ChartData;
  queryConfig?: { xColumn?: string; yColumn?: string; nameColumn?: string; valueColumn?: string };
  configJson?: string;
  width?: number | string;
  height?: number | string;
}

const numericValue = (value: unknown) => Number.parseFloat(String(value ?? '')) || 0;
const EMPTY_ROWS: ChartData['rows'] = [];
const EMPTY_COLUMNS: string[] = [];

const ChartRenderer: React.FC<ChartRendererProps> = React.memo(({ chartType, title, data, queryConfig, configJson, width = '100%', height = '100%' }) => {
  const rows = data?.rows || EMPTY_ROWS;
  const columns = data?.columns || EMPTY_COLUMNS;

  const yCol = queryConfig?.yColumn || columns[1] || '数值';

  // ECharts 图表
  const option = useMemo(() => {
    const customConfig = configJson ? (() => { try { return JSON.parse(configJson); } catch { return {}; } })() : {};
    const xCol = queryConfig?.xColumn || columns[0] || '分类';
    const nameCol = queryConfig?.nameColumn || columns[0] || '分类';
    const valueCol = queryConfig?.valueColumn || columns[1] || '数值';

    const xData = rows.map(r => r[xCol] || '');
    const yData = rows.map(r => numericValue(r[yCol]));

    const dataPointCount = rows.length;

    const baseOption: any = {
      title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
      ...customConfig,
    };

    switch (chartType) {
      case 'bar':
        return {
          ...baseOption,
          tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: (params: any) => {
              const p = Array.isArray(params) ? params[0] : params;
              return `${xCol}：${p.name}<br/>${yCol}：${p.value}`;
            },
          },
          xAxis: { type: 'category', data: xData, name: xCol, nameLocation: 'center', nameGap: 30 },
          yAxis: { type: 'value', name: yCol },
          series: [{ type: 'bar', data: yData, itemStyle: { color: '#1677ff' } }],
        };

      case 'line': {
        const sampling = dataPointCount > 500 ? { sampling: 'lttb' } : {};
        return {
          ...baseOption,
          tooltip: {
            trigger: 'axis',
            formatter: (params: any) => {
              const p = Array.isArray(params) ? params[0] : params;
              return `${xCol}：${p.name}<br/>${yCol}：${p.value}`;
            },
          },
          xAxis: { type: 'category', data: xData, name: xCol, nameLocation: 'center', nameGap: 30 },
          yAxis: { type: 'value', name: yCol },
          series: [{ type: 'line', data: yData, smooth: true, sampling: sampling.sampling as any, itemStyle: { color: '#1677ff' } }],
        };
      }

      case 'pie': {
        const pieData = rows.map(r => ({ name: r[nameCol] || '', value: numericValue(r[valueCol]) }));
        return {
          ...baseOption,
          tooltip: {
            trigger: 'item',
            formatter: (params: any) => `${nameCol}：${params.name}<br/>${valueCol}：${params.value} (${params.percent}%)`,
          },
          series: [{
            type: 'pie', data: pieData, radius: ['30%', '65%'],
            label: { formatter: `{b}\n${valueCol}: {c}` },
            emphasis: { label: { fontSize: 16, fontWeight: 'bold' } },
          }],
        };
      }

      case 'scatter': {
        const useLarge = dataPointCount > 1000;
        const scatterData = rows.map(r => [numericValue(r[xCol]), numericValue(r[valueCol])]);
        return {
          ...baseOption,
          tooltip: {
            trigger: 'item',
            formatter: (params: any) => `${xCol}：${params.value[0]}<br/>${valueCol}：${params.value[1]}`,
          },
          xAxis: { type: 'value', name: xCol, nameLocation: 'center', nameGap: 30 },
          yAxis: { type: 'value', name: valueCol },
          series: [{
            type: 'scatter', data: scatterData,
            symbolSize: 10,
            large: useLarge,
            largeThreshold: 1000,
            itemStyle: { color: '#1677ff' },
          }],
        };
      }

      case 'heatmap': {
        // 用 xCol 做 x 轴分类，yCol 做 y 轴分类，valueCol 做值
        const xCategories = [...new Set(rows.map(r => r[xCol] || ''))];
        const yCategories = [...new Set(rows.map(r => r[yCol] || ''))];
        const heatData: [number, number, number][] = [];
        rows.forEach(r => {
          const xi = xCategories.indexOf(r[xCol] || '');
          const yi = yCategories.indexOf(r[yCol] || '');
          if (xi >= 0 && yi >= 0) {
            heatData.push([xi, yi, numericValue(r[valueCol])]);
          }
        });
        return {
          ...baseOption,
          tooltip: { position: 'top' as const },
          grid: { left: 100, bottom: 60 },
          xAxis: { type: 'category', data: xCategories, name: xCol, nameLocation: 'center', nameGap: 35, splitArea: { show: true } },
          yAxis: { type: 'category', data: yCategories, name: yCol, nameLocation: 'center', nameGap: 50, splitArea: { show: true } },
          visualMap: { min: Math.min(...heatData.map(d => d[2])), max: Math.max(...heatData.map(d => d[2])), calculable: true, orient: 'horizontal', left: 'center', bottom: 0 },
          series: [{ type: 'heatmap', data: heatData, label: { show: true }, emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' } } }],
        };
      }

      case 'radar': {
        // 每行作为雷达图的一项指标：nameCol 为指标名，valueCol 为指标值
        const indicators = rows.map(r => ({ name: r[nameCol] || '', max: Math.max(...rows.map(r2 => numericValue(r2[valueCol]))) * 1.2 }));
        const radarData = [{ name: title, value: rows.map(r => numericValue(r[valueCol])) }];
        return {
          ...baseOption,
          tooltip: { trigger: 'item' as const },
          radar: { indicator: indicators, center: ['50%', '55%'], radius: '65%' },
          series: [{ type: 'radar', data: radarData, areaStyle: { opacity: 0.3 }, itemStyle: { color: '#1677ff' } }],
        };
      }

      case 'funnel': {
        const funnelData = rows.map(r => ({ name: r[nameCol] || '', value: numericValue(r[valueCol]) }));
        return {
          ...baseOption,
          tooltip: { trigger: 'item' as const, formatter: (params: any) => `${params.name}：${params.value}` },
          series: [{
            type: 'funnel', data: funnelData, left: '10%', right: '10%', top: 60, bottom: 30,
            minSize: '0%', maxSize: '100%',
            sort: 'descending' as const,
            gap: 2,
            label: { show: true, position: 'inside' as const },
            emphasis: { label: { fontSize: 16 } },
          }],
        };
      }

      default:
        return baseOption;
    }
  }, [chartType, title, rows, columns, yCol, queryConfig, configJson]);

  if (!data || !rows.length) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#999', border: '1px dashed #d9d9d9', borderRadius: 4 }}>
        <span>{title} - 暂无数据，请绑定数据源</span>
      </div>
    );
  }

  if (chartType === 'card') {
    const total = rows.map(r => numericValue(r[yCol])).reduce((a, b) => a + b, 0);
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', padding: 16 }}>
        <Card style={{ textAlign: 'center', width: '100%' }} bordered={false}>
          <Statistic title={title} value={total} suffix={yCol} valueStyle={{ color: '#1677ff', fontSize: 36, fontWeight: 'bold' }} />
        </Card>
      </div>
    );
  }

  if (chartType === 'table') {
    const cols = columns.map(c => ({ title: c, dataIndex: c, key: c }));
    return (
      <div style={{ padding: 12, overflow: 'auto', height: '100%' }}>
        <div style={{ textAlign: 'center', fontWeight: 'bold', marginBottom: 8, fontSize: 14 }}>{title}</div>
        <Table columns={cols} dataSource={rows.map((r, i) => ({ ...r, _key: i }))} rowKey="_key" size="small" pagination={rows.length > 10 ? { pageSize: 10 } : false} />
      </div>
    );
  }

  return <ReactECharts option={option} style={{ width, height }} opts={{ renderer: 'canvas' }} />;
});

export default ChartRenderer;
