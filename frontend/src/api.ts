export type Metric = { model: string; mae: number; rmse: number; source: string }
export type Prediction = { timestamp: string; actual: number; gcn_gru: number; naive: number; seasonal_24h?: number | null }
export type Station = { id: string; name: string; lat: number; lng: number; observations: number }
export type StationError = { station_id: string; activity: number; gcn_gru_mae: number; naive_mae: number }

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`/api${path}`)
  if (!response.ok) throw new Error(`API ${response.status}: ${await response.text()}`)
  return response.json()
}

export const api = {
  health: () => request<{ status: string; dataset_available: boolean; experiments_enabled: boolean }>('/health'),
  overview: () => request<{ stations: number; test_hours: number; models: number; comparisons: Metric[]; data_source: string }>('/overview'),
  metrics: () => request<Metric[]>('/metrics'),
  predictions: () => request<Prediction[]>('/predictions'),
  stations: () => request<Station[]>('/stations'),
  graph: () => request<{ nodes: Station[]; edges: { source: string; target: string; weight: number }[] }>('/graph?limit=10000'),
  station: (id: string) => request<{ station?: Station; evaluation?: StationError }>(`/stations/${encodeURIComponent(id)}`),
  stationPredictions: (id: string) => request<{ station: Station; predictions: Prediction[] }>(`/stations/${encodeURIComponent(id)}/predictions`),
  experiments: () => request<{ completed: Record<string, unknown>[]; tasks: Record<string, unknown>[] }>('/experiments'),
}
