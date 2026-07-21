import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

export interface ChartPoint {
  t: number; // seconds ago (0 = now)
  risk: number;
  drowsiness: number;
  emotion: number;
  aggression: number;
}

interface Props {
  points: ChartPoint[];
}

export default function RiskChart({ points }: Props) {
  return (
    <div className="bg-card rounded-xl border border-slate-700 p-4">
      <h2 className="text-sm uppercase tracking-widest text-slate-400 mb-3">
        Risk Timeline (last 60s)
      </h2>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={points} margin={{ top: 5, right: 10, bottom: 5, left: -20 }}>
            <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
            <XAxis
              dataKey="t"
              tick={{ fill: '#64748B', fontSize: 11 }}
              stroke="#475569"
              tickFormatter={(v: number) => `${v}s`}
              reversed
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fill: '#64748B', fontSize: 11 }}
              stroke="#475569"
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1E293B',
                border: '1px solid #334155',
                borderRadius: 8,
                color: '#F1F5F9',
              }}
              labelFormatter={(v) => `${v}s ago`}
            />
            <ReferenceLine y={30} stroke="#F59E0B" strokeDasharray="6 4" />
            <ReferenceLine y={60} stroke="#EF4444" strokeDasharray="6 4" />
            <Bar dataKey="aggression" fill="#3B82F6" opacity={0.15} isAnimationActive={false} />
            <Line
              type="monotone"
              dataKey="risk"
              name="Overall Risk"
              stroke="#3B82F6"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="drowsiness"
              name="Drowsiness"
              stroke="#A855F7"
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="emotion"
              name="Emotion"
              stroke="#FB923C"
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="flex gap-4 mt-2 text-xs text-slate-400">
        <span className="flex items-center gap-1">
          <span className="w-3 h-0.5 bg-accent inline-block" /> Overall
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-0.5 bg-purple-500 inline-block" /> Drowsiness
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-0.5 bg-orange-400 inline-block" /> Emotion
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-2 bg-accent/20 inline-block" /> Aggression
        </span>
      </div>
    </div>
  );
}
