import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

interface ChartRendererProps {
  chartType: 'bar' | 'line' | 'pie';
  title: string;
  data?: { columns: string[]; rows: Record<string, string>[] };
  queryConfig?: { xColumn?: string; yColumn?: string; nameColumn?: string; valueColumn?: string };
  configJson?: string;
  width?: number | string;
  height?: number | string;
}

const ChartRenderer: React.FC<ChartRendererProps> = ({ chartType, title, data, queryConfig, configJson, width = '100%', height = '100%' }) => {
  const option = useMemo(() => {
    const customConfig = configJson ? JSON.parse(configJson) : {};
    const rows = data?.rows || [];
    const columns = data?.columns || [];

    const xCol = queryConfig?.xColumn || columns[0] || '分类';
    const yCol = queryConfig?.yColumn || columns[1] || '数值';
    const nameCol = queryConfig?.nameColumn || columns[0] || '分类';
    const valueCol = queryConfig?.valueColumn || columns[1] || '数值';

    const xData = rows.map(r => r[xCol] || '');
    const yData = rows.map(r => parseFloat(r[yCol]) || 0);

    // 通用 tooltip：显示字段名 + 值
    const tooltipFormatter = (params: any) => {
      if (Array.isArray(params)) params = params[0];
      return `${xCol}：${params.name}<br/>${yCol}：${params.value}`;
    };

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
          xAxis: {
            type: 'category',
            data: xData,
            name: xCol,
            nameLocation: 'center',
            nameGap: 30,
          },
          yAxis: {
            type: 'value',
            name: yCol,
          },
          series: [{ type: 'bar', data: yData, itemStyle: { color: '#1677ff' } }],
        };
      case 'line':
        return {
          ...baseOption,
          tooltip: {
            trigger: 'axis',
            formatter: (params: any) => {
              const p = Array.isArray(params) ? params[0] : params;
              return `${xCol}：${p.name}<br/>${yCol}：${p.value}`;
            },
          },
          xAxis: {
            type: 'category',
            data: xData,
            name: xCol,
            nameLocation: 'center',
            nameGap: 30,
          },
          yAxis: {
            type: 'value',
            name: yCol,
          },
          series: [{ type: 'line', data: yData, smooth: true, itemStyle: { color: '#1677ff' } }],
        };
      case 'pie':
        const pieData = rows.map(r => ({ name: r[nameCol] || '', value: parseFloat(r[valueCol]) || 0 }));
        return {
          ...baseOption,
          tooltip: {
            trigger: 'item',
            formatter: (params: any) => {
              return `${nameCol}：${params.name}<br/>${valueCol}：${params.value} (${params.percent}%)`;
            },
          },
          series: [{
            type: 'pie',
            data: pieData,
            radius: ['30%', '65%'],
            label: {
              formatter: `{b}\n${valueCol}: {c}`,
            },
            emphasis: {
              label: {
                fontSize: 16,
                fontWeight: 'bold',
              },
            },
          }],
        };
      default:
        return baseOption;
    }
  }, [chartType, title, data, queryConfig, configJson]);

  if (!data || !data.rows?.length) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#999', border: '1px dashed #d9d9d9', borderRadius: 4 }}>
        <span>{title} - 暂无数据，请绑定数据源</span>
      </div>
    );
  }

  return <ReactECharts option={option} style={{ width, height }} opts={{ renderer: 'canvas' }} />;
};

export default ChartRenderer;
