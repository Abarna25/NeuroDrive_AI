import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { AlertEntry, SessionSummaryData } from '../types';

interface Props {
  summary: SessionSummaryData;
  alerts: AlertEntry[];
  onNewSession: () => void;
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  if (m === 0) return `${s}s`;
  return `${m}m ${s}s`;
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="bg-background/60 rounded-lg p-3">
      <div className="text-xs text-slate-400 uppercase tracking-wide">{label}</div>
      <div className={`text-xl font-bold mt-1 ${accent ?? ''}`}>{value}</div>
    </div>
  );
}

export default function SessionSummary({ summary, alerts, onNewSession }: Props) {
  // Bucket the session's alerts by minute for the bar chart.
  const buckets = new Map<string, number>();
  for (const alert of alerts) {
    const d = new Date(alert.timestamp);
    const key = `${d.getHours().toString().padStart(2, '0')}:${d
      .getMinutes()
      .toString()
      .padStart(2, '0')}`;
    buckets.set(key, (buckets.get(key) ?? 0) + 1);
  }
  const chartData = Array.from(buckets.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([minute, count]) => ({ minute, count }));

  return (
    <div className="bg-card rounded-xl border border-accent/40 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold">🏁 Session Summary</h2>
        <button
          onClick={onNewSession}
          className="bg-accent hover:bg-blue-600 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
        >
          Start New Session
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <Stat label="Drive time" value={formatDuration(summary.total_drive_seconds)} />
        <Stat
          label="Total alerts"
          value={`${summary.total_alerts}`}
          accent={summary.total_alerts > 0 ? 'text-caution' : 'text-safe'}
        />
        <Stat
          label="Caution / Danger"
          value={`${summary.caution_alerts} / ${summary.danger_alerts}`}
        />
        <Stat label="Avg risk" value={summary.avg_risk_score.toFixed(1)} />
        <Stat
          label="Peak risk"
          value={summary.peak_risk_score.toFixed(1)}
          accent={summary.peak_risk_score > 60 ? 'text-danger' : ''}
        />
        <Stat label="Dominant emotion" value={summary.dominant_emotion} />
      </div>

      {summary.peak_risk_timestamp && (
        <p className="text-xs text-slate-400 mt-3">
          Peak risk occurred at{' '}
          {new Date(summary.peak_risk_timestamp).toLocaleTimeString()}
        </p>
      )}

      {chartData.length > 0 && (
        <div className="mt-5">
          <h3 className="text-sm text-slate-400 uppercase tracking-widest mb-2">
            Alerts over time
          </h3>
          <div className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: -25 }}>
                <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                <XAxis dataKey="minute" tick={{ fill: '#64748B', fontSize: 11 }} stroke="#475569" />
                <YAxis allowDecimals={false} tick={{ fill: '#64748B', fontSize: 11 }} stroke="#475569" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1E293B',
                    border: '1px solid #334155',
                    borderRadius: 8,
                    color: '#F1F5F9',
                  }}
                />
                <Bar dataKey="count" fill="#3B82F6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
