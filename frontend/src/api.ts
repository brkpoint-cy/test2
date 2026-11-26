import type { CasesData, DashboardData, EdaData, ExperimentRequest, ExperimentStatus, ModelsData, SimulationContext, SimulationResult, SimulationValues, ThresholdData } from './types'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: `请求失败（${response.status}）` }))
    throw new Error(typeof body.detail === 'string' ? body.detail : '请求参数不正确')
  }
  return response.json() as Promise<T>
}

export const api = {
  dashboard: () => request<DashboardData>('/api/dashboard'),
  eda: () => request<EdaData>('/api/eda'),
  models: () => request<ModelsData>('/api/models'),
  cases: (model = 'xgboost') => request<CasesData>(`/api/cases?model=${model}`),
  thresholdAnalysis: (model: string, partition: 'validation' | 'test') => request<ThresholdData>(`/api/threshold-analysis?model=${model}&partition=${partition}`),
  simulationContext: (sampleIndex: number) => request<SimulationContext>(`/api/simulation-context?sample_index=${sampleIndex}`),
  simulate: (sampleIndex: number, values: SimulationValues) => request<SimulationResult>('/api/simulate', {
    method: 'POST', body: JSON.stringify({ sample_index: sampleIndex, ...values }),
  }),
  experimentStatus: () => request<ExperimentStatus>('/api/experiments'),
  startExperiment: (payload: ExperimentRequest) => request<ExperimentStatus>('/api/experiments', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
}
