import { RiskStatus } from '../types';

interface Props {
  score: number;
  status: RiskStatus;
}

const STATUS_COLORS: Record<RiskStatus, string> = {
  safe: '#22C55E',
  caution: '#F59E0B',
  danger: '#EF4444',
};

// 270° arc, from 135° (bottom-left) sweeping clockwise to 45° (bottom-right).
const CX = 100;
const CY = 100;
const R = 80;
const START_ANGLE = 135;
const SWEEP = 270;

function polar(angleDeg: number): [number, number] {
  const rad = (angleDeg * Math.PI) / 180;
  return [CX + R * Math.cos(rad), CY + R * Math.sin(rad)];
}

function arcPath(fromAngle: number, toAngle: number): string {
  const [x1, y1] = polar(fromAngle);
  const [x2, y2] = polar(toAngle);
  const largeArc = toAngle - fromAngle > 180 ? 1 : 0;
  return `M ${x1} ${y1} A ${R} ${R} 0 ${largeArc} 1 ${x2} ${y2}`;
}

const FULL_ARC = arcPath(START_ANGLE, START_ANGLE + SWEEP);
// Total length of a 270° arc of radius 80.
const ARC_LENGTH = (SWEEP / 360) * 2 * Math.PI * R;

export default function RiskGauge({ score, status }: Props) {
  const clamped = Math.max(0, Math.min(100, score));
  const color = STATUS_COLORS[status];
  const dashOffset = ARC_LENGTH * (1 - clamped / 100);

  return (
    <div className="bg-card rounded-xl border border-slate-700 p-4 flex flex-col items-center">
      <h2 className="text-sm uppercase tracking-widest text-slate-400 self-start">
        Risk Score
      </h2>
      <div className="relative w-56 h-56">
        <svg viewBox="0 0 200 200" className="w-full h-full">
          <path
            d={FULL_ARC}
            fill="none"
            stroke="#334155"
            strokeWidth="16"
            strokeLinecap="round"
          />
          <path
            d={FULL_ARC}
            fill="none"
            stroke={color}
            strokeWidth="16"
            strokeLinecap="round"
            strokeDasharray={ARC_LENGTH}
            strokeDashoffset={dashOffset}
            style={{
              transition: 'stroke-dashoffset 0.5s ease, stroke 0.5s ease',
            }}
          />
          {/* tick labels */}
          <text x="38" y="172" fill="#64748B" fontSize="10" textAnchor="middle">
            0
          </text>
          <text x="100" y="30" fill="#64748B" fontSize="10" textAnchor="middle">
            50
          </text>
          <text x="162" y="172" fill="#64748B" fontSize="10" textAnchor="middle">
            100
          </text>
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="text-5xl font-bold tabular-nums"
            style={{ color, transition: 'color 0.5s ease' }}
          >
            {clamped.toFixed(0)}
          </span>
          <span
            className="mt-1 text-sm font-semibold tracking-widest"
            style={{ color }}
          >
            {status.toUpperCase()}
          </span>
        </div>
      </div>
    </div>
  );
}
