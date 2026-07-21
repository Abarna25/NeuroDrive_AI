export type RiskStatus = 'safe' | 'caution' | 'danger';

export interface DrowsinessData {
  score: number;
  ear: number;
  is_drowsy: boolean;
  is_yawning: boolean;
  is_nodding: boolean;
  perclos: number;
}

export interface EmotionData {
  score: number;
  dominant_emotion: string;
  confidence: number;
}

export interface AggressionData {
  score: number;
  flow_magnitude: number;
  is_tailgating: boolean;
  vehicle_distance: 'safe' | 'close' | 'critical';
}

export interface StreamData {
  risk_score: number;
  status: RiskStatus;
  color: string;
  drowsiness: DrowsinessData;
  emotion: EmotionData;
  aggression: AggressionData;
  alert: { triggered: boolean; message: string };
  frame: string;
  timestamp: string;
  error?: string;
  status_message?: string;
}

export interface AlertEntry {
  id: number;
  timestamp: string;
  alert_type: RiskStatus;
  risk_score: number;
  dominant_emotion: string;
}

export interface SessionSummaryData {
  session_id: string;
  start_time: string;
  end_time: string;
  total_drive_seconds: number;
  total_alerts: number;
  caution_alerts: number;
  danger_alerts: number;
  avg_risk_score: number;
  peak_risk_score: number;
  peak_risk_timestamp: string | null;
  dominant_emotion: string;
}

export const API_BASE = 'http://localhost:8000';
export const WS_URL = 'ws://localhost:8000/ws/stream';
