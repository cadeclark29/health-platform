// Type definitions for Health Platform - matched to actual API responses

export interface User {
  id: string;
  name: string;
  email: string;
  created_at: string;
  age?: number;
  sex?: 'male' | 'female' | 'other';
  height_feet?: number;
  height_inches?: number;
  weight_lbs?: number;
  region?: 'northern' | 'central' | 'southern' | 'gulf';
  activity_level?: 'sedentary' | 'light' | 'moderate' | 'active' | 'athlete';
  work_environment?: 'office' | 'outdoor' | 'shift' | 'remote';
  diet_type?: 'omnivore' | 'vegetarian' | 'vegan';
  bedtime?: string;
  wake_time?: string;
  chronotype?: 'early_bird' | 'night_owl' | 'neutral';
  health_goal?: 'sleep' | 'recovery' | 'energy' | 'wellness';
  onboarding_complete?: string;
  oura_token?: object;
  afternoon_stack_enabled?: boolean;
}

export interface HealthData {
  date: string;
  sleep_score?: number | null;
  hrv_score?: number | null;
  recovery_score?: number | null;
  strain_score?: number | null;
  sleep_duration_hrs?: number | null;
  deep_sleep_duration?: number | null;
  rem_sleep_duration?: number | null;
  light_sleep_duration?: number | null;
  awake_duration?: number | null;
  sleep_efficiency?: number | null;
  sleep_latency?: number | null;
  restfulness_score?: number | null;
  bedtime?: string | null;
  wake_time?: string | null;
  deep_sleep_pct?: number | null;
  rem_sleep_pct?: number | null;
  resting_hr?: number | null;
  lowest_hr?: number | null;
  average_hr_sleep?: number | null;
  vo2_max?: number | null;
  cardiovascular_age?: number | null;
  activity_score?: number | null;
  steps?: number | null;
  active_calories?: number | null;
  total_calories?: number | null;
  sedentary_time?: number | null;
  active_time?: number | null;
  spo2_average?: number | null;
  breathing_average?: number | null;
  breathing_regularity?: number | null;
  stress_level?: string | null;
  stress_score?: number | null;
  workout_type?: string | null;
  workout_duration?: number | null;
  workout_intensity?: string | null;
  workout_calories?: number | null;
  workout_source?: string | null;
  temperature_deviation?: number | null;
  temperature_trend?: number | null;
  source?: string | null;
}

export interface Supplement {
  id: string;
  user_id: string;
  supplement_id: string;
  supplement_name?: string | null;
  start_date: string;
  end_date?: string | null;
  notes?: string | null;
  is_manual?: boolean;
  dosage?: string | null;
  frequency?: string | null;
  reason?: string | null;
  created_at?: string;
}

export interface SupplementLog {
  id: string;
  user_id: string;
  supplement_id: string;
  date: string;
  taken?: boolean;
  dose_mg?: number | null;
  time_taken?: string | null;
  created_at?: string;
}

export interface LifeEvent {
  id: string;
  user_id?: string;
  event_date: string;
  event_type: string;
  description?: string;
  impact?: 'positive' | 'negative' | 'neutral';
  created_at?: string;
}

export interface DateRange {
  start: string;
  end: string;
}

export interface AnalyticsData {
  health_data: HealthData[];
  supplement_starts: Supplement[];
  supplement_logs: SupplementLog[];
  life_events: LifeEvent[];
  date_range?: DateRange;
}

export interface OuraStatus {
  connected: boolean;
  source?: string;
  error?: string;
}

// Time slots for supplement stacks
export type TimeSlot = 'morning' | 'intraday' | 'evening';

export interface StackSupplement extends Supplement {
  timeSlot: TimeSlot;
  isTaken: boolean;
  displayDose?: string;
}

// Supplement insight from the backend
export interface SupplementInsight {
  supplement_id: string;
  supplement_name: string;
  days_on: number;
  primary_metric: string;
  before_avg: number | null;
  after_avg: number | null;
  change_pct: number | null;
  has_sufficient_data: boolean;
  is_positive: boolean;
  metric_display_name: string;
}

export interface InsightsData {
  impact_analysis: SupplementInsight[];
  consistency_tracking: Record<string, any>;
  summary: {
    total_supplements: number;
    with_data: number;
    collecting_data: number;
  };
}

// Health alert for dashboard
export interface HealthAlert {
  id: string;
  type: 'sleep' | 'stress' | 'recovery' | 'fatigue' | 'immune';
  severity: 'info' | 'warning' | 'critical';
  title: string;
  description: string;
  icon: string;
  color: string;
  actions: HealthAlertAction[];
}

export interface HealthAlertAction {
  label: string;
  supplementId: string;
  type: 'add' | 'hold' | 'reduce';
}

// Life event types
export const LIFE_EVENT_TYPES: { value: string; label: string; icon: string }[] = [
  { value: 'new_job', label: 'New Job / Work Stress', icon: '💼' },
  { value: 'changed_mattress', label: 'Changed Mattress', icon: '🛏️' },
  { value: 'moved', label: 'Moved', icon: '🏠' },
  { value: 'started_exercise', label: 'Started Exercise', icon: '🏃' },
  { value: 'stopped_exercise', label: 'Stopped Exercise', icon: '🛑' },
  { value: 'sick', label: 'Got Sick', icon: '🤒' },
  { value: 'travel', label: 'Travel', icon: '✈️' },
  { value: 'relationship', label: 'Relationship Change', icon: '❤️' },
  { value: 'diet_change', label: 'Diet Change', icon: '🥗' },
  { value: 'medication', label: 'Medication Change', icon: '💊' },
  { value: 'stress', label: 'Major Stress', icon: '😰' },
  { value: 'injury', label: 'Injury', icon: '🩹' },
  { value: 'other', label: 'Other', icon: '📝' },
];

// Supplement mechanism explanations
export const SUPPLEMENT_MECHANISMS: Record<string, string> = {
  magnesium_glycinate: 'Glycine crosses the blood-brain barrier, promoting GABA activity for deeper sleep. Magnesium relaxes muscles and calms the nervous system.',
  magnesium: 'Essential mineral that activates 300+ enzymes. Supports muscle relaxation, nerve function, and sleep quality.',
  magnesium_l_threonate: 'Unique form that crosses the blood-brain barrier, supporting cognitive function and memory while improving sleep.',
  ashwagandha: 'Adaptogen that reduces cortisol levels by up to 30%. Supports HPA axis recovery from chronic stress.',
  l_theanine: 'Promotes alpha brain waves associated with calm alertness. Increases GABA, serotonin, and dopamine.',
  melatonin: 'Primary sleep hormone that regulates circadian rhythm. Low doses (0.3-1mg) are more effective than high doses.',
  vitamin_d3: 'Fat-soluble vitamin critical for immune function, bone health, and mood regulation. Most people are deficient.',
  vitamin_d: 'Essential for calcium absorption, immune function, and circadian rhythm regulation.',
  fish_oil: 'Rich in EPA and DHA omega-3 fatty acids. Reduces inflammation, supports brain health and cardiovascular function.',
  omega_3: 'Anti-inflammatory fatty acids that support brain, heart, and joint health. Improves HRV in studies.',
  creatine: 'Supports ATP regeneration for muscle energy. Also shown to improve cognitive function and brain energy.',
  glycine: 'Inhibitory amino acid that lowers core body temperature before sleep. Improves subjective sleep quality.',
  zinc: 'Essential mineral for immune function, testosterone production, and sleep quality.',
  apigenin: 'Flavonoid found in chamomile that binds GABA receptors, promoting relaxation without sedation.',
  rhodiola: 'Adaptogen that increases mental stamina and reduces fatigue. Modulates cortisol response.',
  cordyceps: 'Medicinal mushroom that improves oxygen utilization and cellular energy production.',
  lions_mane: 'Mushroom that stimulates nerve growth factor (NGF). Supports cognitive function and neuroplasticity.',
  coq10: 'Mitochondrial antioxidant essential for cellular energy production. Levels decline with age.',
  vitamin_b12: 'Critical for energy metabolism, red blood cell formation, and neurological function.',
  vitamin_b_complex: 'B vitamins work synergistically for energy metabolism, mood regulation, and nervous system health.',
  iron: 'Essential for hemoglobin production and oxygen transport. Supports energy levels and cognitive function.',
  caffeine: 'Adenosine receptor antagonist that increases alertness. Best taken before 2pm to avoid sleep disruption.',
  electrolytes: 'Minerals (sodium, potassium, magnesium) critical for hydration, nerve signaling, and muscle function.',
  alpha_lipoic_acid: 'Powerful antioxidant that regenerates other antioxidants. Supports mitochondrial function and blood sugar regulation.',
  valerian: 'Herb that increases GABA levels, promoting relaxation and sleep onset.',
  gaba: 'Primary inhibitory neurotransmitter that reduces neural excitability. Promotes calm and sleep.',
};

// Navigation types
export type RootStackParamList = {
  Auth: undefined;
  Onboarding: undefined;
  Main: undefined;
};

export type MainTabParamList = {
  Dashboard: undefined;
  Analytics: undefined;
  Settings: undefined;
};
