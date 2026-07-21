import { useCallback, useEffect, useRef, useState } from 'react';
import AlertLog from './components/AlertLog';
import ModuleStatus from './components/ModuleStatus';
import RiskChart, { ChartPoint } from './components/RiskChart';
import RiskGauge from './components/RiskGauge';
import SessionSummary from './components/SessionSummary';
import VideoFeed from './components/VideoFeed';
import { useWebSocket } from './hooks/useWebSocket';
import { AlertEntry, API_BASE, SessionSummaryData } from './types';

const CHART_WINDOW = 60; // one point per second, last 60 seconds

export default function App() {
  const { data, isConnected, error } = useWebSocket();

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [summary, setSummary] = useState<SessionSummaryData | null>(null);
  const [sessionAlerts, setSessionAlerts] = useState<AlertEntry[]>([]);
  const [alerts, setAlerts] = useState<AlertEntry[]>([]);
  const [chartPoints, setChartPoints] = useState<ChartPoint[]>([]);

  const alertIdRef = useRef(0);
  const lastChartPushRef = useRef(0);

  // Accumulate alert-log entries and once-per-second chart points from the stream.
  useEffect(() => {
    if (!data) return;

    if (data.alert.triggered) {
      alertIdRef.current += 1;
      const entry: AlertEntry = {
        id: alertIdRef.current,
        timestamp: data.timestamp,
        alert_type: data.status,
        risk_score: data.risk_score,
        dominant_emotion: data.emotion.dominant_emotion,
      };
      setAlerts((prev) => [entry, ...prev].slice(0, 50));
    }

    const now = Date.now();
    if (now - lastChartPushRef.current >= 1000) {
      lastChartPushRef.current = now;
      setChartPoints((prev) => {
        const shifted = prev.map((p) => ({ ...p, t: p.t + 1 })).filter((p) => p.t <= CHART_WINDOW);
        return [
          ...shifted,
          {
            t: 0,
            risk: data.risk_score,
            drowsiness: Math.round(data.drowsiness.score * 100),
            emotion: Math.round(data.emotion.score * 100),
            aggression: Math.round(data.aggression.score * 100),
          },
        ];
      });
    }
  }, [data]);

  const startSession = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/session/start`, { method: 'POST' });
      const body = await res.json();
      setSessionId(body.session_id);
      setSummary(null);
      setSessionAlerts([]);
      setAlerts([]);
    } catch {
      window.alert('Could not start session — is the backend running?');
    }
  }, []);

  const endSession = useCallback(async () => {
    if (!sessionId) return;
    try {
      const res = await fetch(`${API_BASE}/session/end/${sessionId}`, { method: 'POST' });
      const body: SessionSummaryData = await res.json();
      const alertsRes = await fetch(`${API_BASE}/session/${sessionId}/alerts`);
      const alertsBody = await alertsRes.json();
      setSummary(body);
      setSessionAlerts(alertsBody.alerts ?? []);
      setSessionId(null);
    } catch {
      window.alert('Could not end session — is the backend running?');
    }
  }, [sessionId]);

  return (
    <div className="min-h-screen bg-background text-textmain">
      {/* top bar */}
      <header className="border-b border-slate-800 px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-bold">
          🛡️ NeuroDrive <span className="text-accent">AI</span>
        </h1>
        <div className="flex items-center gap-3">
          {sessionId && (
            <span className="text-xs text-slate-400 font-mono hidden sm:inline">
              session {sessionId.slice(0, 8)}…
            </span>
          )}
          {sessionId ? (
            <button
              onClick={endSession}
              className="bg-danger hover:bg-red-600 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
            >
              End Session
            </button>
          ) : (
            <button
              onClick={startSession}
              className="bg-safe hover:bg-green-600 text-black text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
            >
              Start Session
            </button>
          )}
        </div>
      </header>

      <main className="p-6 max-w-7xl mx-auto space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* left column */}
          <div className="space-y-6">
            <VideoFeed data={data} isConnected={isConnected} error={error} />
            <ModuleStatus
              drowsiness={data?.drowsiness ?? null}
              aggression={data?.aggression ?? null}
              emotion={data?.emotion ?? null}
            />
          </div>

          {/* right column */}
          <div className="space-y-6">
            <RiskGauge score={data?.risk_score ?? 0} status={data?.status ?? 'safe'} />
            <RiskChart points={chartPoints} />
            <AlertLog alerts={alerts} />
          </div>
        </div>

        {summary && (
          <SessionSummary
            summary={summary}
            alerts={sessionAlerts}
            onNewSession={startSession}
          />
        )}
      </main>
    </div>
  );
}
