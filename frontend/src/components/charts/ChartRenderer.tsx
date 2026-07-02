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

    // Auto-detect columns if not specified
    const xCol = queryConfig?.xColumn || columns[0] || 'name';
    const yCol = queryConfig?.yColumn || columns[1] || 'value';
    const nameCol = queryConfig?.nameColumn || columns[0] || 'name';
    const valueCol = queryConfig?.valueColumn || columns[1] || 'value';

    const xData = rows.map(r => r[xCol] || '');
    const yData = rows.map(r => parseFloat(r[yCol]) || 0);

    const baseOption: any = {
      title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
      tooltip: {},
      ...customConfig,
    };

    switch (chartType) {
      case 'bar':
        return {
          ...baseOption,
          xAxis: { type: 'category', data: xData },
          yAxis: { type: 'value' },
          series: [{ type: 'bar', data: yData, itemStyle: { color: '#1677ff' } }],
        };
      case 'line':
        return {
          ...baseOption,
          xAxis: { type: 'category', data: xData },
          yAxis: { type: 'value' },
          series: [{ type: 'line', data: yData, smooth: true, itemStyle: { color: '#1677ff' } }],
        };
      case 'pie':
        const pieData = rows.map(r => ({ name: r[nameCol] || '', value: parseFloat(r[valueCol]) || 0 }));
        return {
          ...baseOption,
          series: [{ type: 'pie', data: pieData, radius: ['30%', '65%'], label: { formatter: '{b}: {c}' } }],
        };
      default:
        return baseOption;
    }
  }, [chartType, title, data, queryConfig, configJson]);

  if (!data || !data.rows?.length) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#999', border: '1px dashed #d9d9d9', borderRadius: 4 }}>
        <span>{title} - No data. Bind a data source.</span>
      </div>
    );
  }

  return <ReactECharts option={option} style={{ width, height }} opts={{ renderer: 'canvas' }} />;
};

export default ChartRenderer;
