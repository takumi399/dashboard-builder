import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Typography, Spin } from 'antd';
import ChartRenderer from '../components/charts/ChartRenderer';
import { publicService, dataSourceService } from '../services/dashboard';

const { Title } = Typography;

const DashboardViewPage: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const [dashboard, setDashboard] = useState<any>(null);
  const [dataSourceData, setDataSourceData] = useState<Record<number, any>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const d = await publicService.getDashboard(token!);
        setDashboard(d);
        const dataMap: Record<number, any> = {};
        for (const chart of d.charts || []) {
          if (chart.data_source_id && !dataMap[chart.data_source_id]) {
            try { dataMap[chart.data_source_id] = await dataSourceService.getData(chart.data_source_id); } catch {}
          }
        }
        setDataSourceData(dataMap);
      } catch {}
      finally { setLoading(false); }
    };
    if (token) load();
  }, [token]);

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 100 }}><Spin size="large" /></div>;
  if (!dashboard) return <div style={{ textAlign: 'center', padding: 100 }}><Title level={4}>Dashboard not found</Title></div>;

  return (
    <div style={{ padding: 24 }}>
      <Title level={3} style={{ textAlign: 'center', marginBottom: 24 }}>{dashboard.name}</Title>
      {dashboard.description && <p style={{ textAlign: 'center', color: '#666', marginBottom: 24 }}>{dashboard.description}</p>}
      <div style={{ position: 'relative', minHeight: 500, background: '#f5f5f5', borderRadius: 8 }}>
        {(dashboard.charts || []).map((chart: any) => (
          <div key={chart.id} style={{ position: 'absolute', left: chart.position_x, top: chart.position_y, width: chart.width, height: chart.height, background: '#fff', borderRadius: 8, boxShadow: '0 2px 8px rgba(0,0,0,0.1)', overflow: 'hidden' }}>
            <ChartRenderer chartType={chart.chart_type} title={chart.title} data={dataSourceData[chart.data_source_id]}
              queryConfig={JSON.parse(chart.query_config || '{}')} configJson={chart.config_json} />
          </div>
        ))}
      </div>
    </div>
  );
};

export default DashboardViewPage;
