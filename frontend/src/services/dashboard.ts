import api from './api';

interface Dashboard {
  id: number; name: string; description: string; is_published: boolean;
  share_token: string | null; created_at: string; updated_at: string; charts: Chart[];
  chart_count?: number;
}

interface Chart {
  id: number; dashboard_id: number; chart_type: string; title: string;
  position_x: number; position_y: number; width: number; height: number;
  data_source_id: number | null; config_json: string; query_config: string; sort_order: number;
}

export const dashboardService = {
  list: () => api.get<Dashboard[]>('/dashboards').then(r => r.data),
  get: (id: number) => api.get<Dashboard>(`/dashboards/${id}`).then(r => r.data),
  create: (data: { name: string; description?: string }) => api.post<Dashboard>('/dashboards', data).then(r => r.data),
  update: (id: number, data: { name?: string; description?: string }) => api.put<Dashboard>(`/dashboards/${id}`, data).then(r => r.data),
  delete: (id: number) => api.delete(`/dashboards/${id}`),
  publish: (id: number) => api.post<Dashboard>(`/dashboards/${id}/publish`).then(r => r.data),
};

export const chartService = {
  list: (dashboardId: number) => api.get<Chart[]>(`/dashboards/${dashboardId}/charts`).then(r => r.data),
  create: (dashboardId: number, data: Partial<Chart>) => api.post<Chart>(`/dashboards/${dashboardId}/charts`, data).then(r => r.data),
  update: (chartId: number, data: Partial<Chart>) => api.put<Chart>(`/dashboards/charts/${chartId}`, data).then(r => r.data),
  delete: (chartId: number) => api.delete(`/dashboards/charts/${chartId}`),
};

export interface SQLConnectionConfig {
  db_type: string;   // "mysql" | "postgresql" | "sqlite"
  host?: string;
  port?: number;
  database?: string;
  username?: string;
  password?: string;
}

export interface SQLExecuteResult {
  columns: string[];
  rows: Record<string, any>[];
  row_count: number;
}

export const dataSourceService = {
  list: () => api.get<any[]>('/datasources').then(r => r.data),
  create: (data: { name: string; source_type: string; connection_config?: string; config_json?: string; raw_data?: string }) =>
    api.post<any>('/datasources', data).then(r => r.data),
  upload: (name: string, file: File) => { const fd = new FormData(); fd.append('file', file); return api.post(`/datasources/upload?name=${encodeURIComponent(name)}`, fd).then(r => r.data); },
  getData: (id: number) => api.get<any>(`/datasources/${id}/data`).then(r => r.data),
  executeSql: (datasourceId: number, query: string) =>
    api.post<SQLExecuteResult>('/datasources/sql/execute', { datasource_id: datasourceId, query }).then(r => r.data),
  delete: (id: number) => api.delete(`/datasources/${id}`),
};

export const publicService = {
  getDashboard: (token: string) => api.get<Dashboard>(`/public/dashboards/${token}`).then(r => r.data),
};
