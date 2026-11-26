export type PageId = 'overview' | 'data' | 'models' | 'xgboost' | 'playground' | 'cases' | 'experiment'

export interface Metrics {
  pr_auc: number | null
  roc_auc: number | null
  precision: number
  recall: number
  f1: number
  false_alarm_rate: number | null
  accuracy: number
  tn: number
  fp: number
  fn: number
  tp: number
  positive_support: number
  negative_support: number
  threshold: number
}

export interface ModelResult {
  name: string
  validation: Metrics
  test: Metrics
  parameters: number
  training_seconds: number
  inference_seconds: number
  feature_importances: Record<string, number>
  hardware: Record<string, string>
}

export interface DashboardData {
  data_source: string
  config: {
    lookback: number
    horizon: number
    pm25_threshold: number
    xgb_estimators: number
    xgb_max_depth: number
    xgb_learning_rate: number
    hidden_size: number
    epochs: number
    seed: number
  }
  cleaning: {
    rows_after_alignment: number
    duplicate_rows_aggregated: number
    start: string
    end: string
    missing_rates: Record<string, number>
    interpolation: string
  }
  dataset: {
    partitions: Record<string, { samples: number; positive: number; negative: number; start: string; end: string }>
  }
  models: ModelResult[]
  monthly: Array<{ month: number; mean: number; median: number; max: number }>
  events: Array<{ metric: string; value: number | null }>
  run: ExperimentStatus
}

export interface EdaData {
  data_source: string
  missing: Record<string, number>
  monthly: DashboardData['monthly']
  heating: Array<{ heating_season: string; mean: number; median: number; max: number }>
  lags: Array<{ variable: string; lag_hours: number; correlation: number | null }>
  events: DashboardData['events']
  series: Array<{ time: string; pm25: number; temperature?: number; wind_speed?: number }>
}

export interface ModelsData {
  data_source: string
  models: ModelResult[]
  curves: Record<string, Array<{ precision: number; recall: number }>>
}

export interface CaseItem {
  label: string
  available: boolean
  time?: string
  score?: number
  actual?: number
  threshold?: number
  series: Array<{ time: string; pm25: number; phase: 'history' | 'future' }>
}

export interface CasesData {
  data_source: string
  model: string
  pm25_threshold: number
  lookback: number
  horizon: number
  cases: Record<'tp' | 'fn' | 'fp', CaseItem>
}

export interface ExperimentStatus {
  run_id: string | null
  status: 'idle' | 'queued' | 'running' | 'complete' | 'failed'
  message: string
  output: string | null
  data_source?: string
}

export interface ExperimentRequest {
  air_path: string
  weather_path: string | null
  data_source: 'observed' | 'synthetic'
  lookback: number
  horizon: number
  pm25_threshold: number
  epochs: number
  xgb_estimators: number
}

export interface ThresholdPoint {
  threshold: number
  precision: number
  recall: number
  f1: number
  false_alarm_rate: number | null
  accuracy: number
  tp: number
  fp: number
  tn: number
  fn: number
}

export interface ThresholdData {
  data_source: string
  model: string
  partition: 'validation' | 'test'
  validation_threshold: number
  points: ThresholdPoint[]
}

export interface SimulationValues {
  pm25: number
  temperature: number
  humidity: number
  wind_speed: number
}

export interface SimulationContext {
  data_source: string
  sample_index: number
  sample_count: number
  time: string
  actual: number
  threshold: number
  baseline_score: number
  values: SimulationValues
}

export interface SimulationResult extends Omit<SimulationContext, 'values'> {
  score: number
  delta: number
  predicted: number
}
