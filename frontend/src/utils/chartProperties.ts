export interface EditableChartProperties {
  title: string;
  width: number;
  height: number;
  data_source_id: number | null;
  query_config: string;
  config_json: string;
}

export type ChartPropertyUpdate =
  | [field: 'title', value: string]
  | [field: 'width' | 'height', value: number | null]
  | [field: 'data_source_id', value: number | null]
  | [field: 'query_config' | 'config_json', value: string];

export const chartPropertyPatch = (
  ...[field, value]: ChartPropertyUpdate
): Partial<EditableChartProperties> | null => {
  if ((field === 'width' || field === 'height') && value === null) return null;
  return { [field]: value };
};
