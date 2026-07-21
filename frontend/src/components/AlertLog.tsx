import { useEffect, useRef } from 'react';
import { AlertEntry } from '../types';

interface Props {
  alerts: AlertEntry[];
}

export default function AlertLog({ alerts }: Props) {
  const listRef = useRef<HTMLDivElement>(null);

  // Newest entries render on top, so "scroll to newest" means scroll to top.
  useEffect(() => {
    listRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  }, [alerts.length]);

  const shown = alerts.slice(0, 50);

  return (
    <div className="bg-card rounded-xl border border-slate-700 p-4">
      <h2 className="text-sm uppercase tracking-widest text-slate-400 mb-3">
        Alert Log
      </h2>
      <div ref={listRef} className="max-h-52 overflow-y-auto space-y-2 pr-1">
        {shown.length === 0 ? (
          <div className="text-slate-400 text-sm py-6 text-center">
            No alerts yet — drive safe! 🟢
          </div>
        ) : (
          shown.map((alert) => (
            <div
              key={alert.id}
              className={`flex items-center justify-between rounded-lg px-3 py-2 text-xs border ${
                alert.alert_type === 'danger'
                  ? 'border-danger/50 bg-danger/10'
                  : 'border-caution/50 bg-caution/10'
              }`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`font-bold px-1.5 py-0.5 rounded ${
                    alert.alert_type === 'danger'
                      ? 'bg-danger text-white'
                      : 'bg-caution text-black'
                  }`}
                >
                  {alert.alert_type.toUpperCase()}
                </span>
                <span className="text-slate-300">
                  {new Date(alert.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <div className="flex items-center gap-3 font-mono">
                <span>risk {alert.risk_score.toFixed(1)}</span>
                <span className="text-slate-400">{alert.dominant_emotion}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
