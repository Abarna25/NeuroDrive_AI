import { AggressionData, DrowsinessData, EmotionData } from '../types';

interface Props {
  drowsiness: DrowsinessData | null;
  aggression: AggressionData | null;
  emotion: EmotionData | null;
}

const EMOTION_EMOJI: Record<string, string> = {
  angry: '😠',
  fear: '😨',
  disgust: '🤢',
  sad: '😢',
  surprise: '😲',
  neutral: '😐',
  happy: '😊',
};

function Badge({ label, tone }: { label: string; tone: 'safe' | 'caution' | 'danger' }) {
  const styles = {
    safe: 'bg-safe/20 text-safe',
    caution: 'bg-caution/20 text-caution',
    danger: 'bg-danger/20 text-danger',
  };
  return (
    <span className={`text-xs font-bold px-2 py-0.5 rounded ${styles[tone]}`}>
      {label}
    </span>
  );
}

function Card({
  icon,
  title,
  badge,
  children,
}: {
  icon: string;
  title: string;
  badge: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-card rounded-xl border border-slate-700 p-4 flex-1 min-w-[180px]">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-semibold">
          <span className="mr-1.5">{icon}</span>
          {title}
        </span>
        {badge}
      </div>
      <div className="space-y-1.5 text-xs text-slate-300">{children}</div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between">
      <span className="text-slate-400">{label}</span>
      <span className="font-mono">{value}</span>
    </div>
  );
}

export default function ModuleStatus({ drowsiness, aggression, emotion }: Props) {
  const drowsyBadge = !drowsiness ? (
    <Badge label="—" tone="safe" />
  ) : drowsiness.is_drowsy ? (
    <Badge label="DROWSY" tone="danger" />
  ) : drowsiness.is_yawning ? (
    <Badge label="YAWNING" tone="caution" />
  ) : (
    <Badge label="ALERT" tone="safe" />
  );

  const aggroBadge = !aggression ? (
    <Badge label="—" tone="safe" />
  ) : aggression.is_tailgating ? (
    <Badge label="TAILGATING" tone="danger" />
  ) : aggression.flow_magnitude > 8 ? (
    <Badge label="AGGRESSIVE" tone="caution" />
  ) : (
    <Badge label="SAFE" tone="safe" />
  );

  const emotionTone = !emotion
    ? 'safe'
    : emotion.score > 0.6
      ? 'danger'
      : emotion.score > 0.3
        ? 'caution'
        : 'safe';
  const emotionBadge = (
    <Badge
      label={emotion ? emotion.dominant_emotion.toUpperCase() : '—'}
      tone={emotionTone as 'safe' | 'caution' | 'danger'}
    />
  );

  return (
    <div className="flex flex-wrap gap-4">
      <Card icon="😴" title="Drowsiness" badge={drowsyBadge}>
        <Row label="EAR" value={drowsiness ? drowsiness.ear.toFixed(3) : '—'} />
        <Row label="PERCLOS" value={drowsiness ? `${drowsiness.perclos.toFixed(0)}%` : '—'} />
        <Row label="Yawning" value={drowsiness ? (drowsiness.is_yawning ? 'Yes' : 'No') : '—'} />
        <Row label="Nodding" value={drowsiness ? (drowsiness.is_nodding ? 'Yes' : 'No') : '—'} />
      </Card>

      <Card icon="🚗" title="Aggression" badge={aggroBadge}>
        <Row
          label="Flow magnitude"
          value={aggression ? aggression.flow_magnitude.toFixed(2) : '—'}
        />
        <Row label="Vehicle distance" value={aggression ? aggression.vehicle_distance : '—'} />
        <Row
          label="Tailgating"
          value={aggression ? (aggression.is_tailgating ? 'Yes' : 'No') : '—'}
        />
      </Card>

      <Card icon="😊" title="Emotion" badge={emotionBadge}>
        <Row
          label="Dominant"
          value={
            emotion
              ? `${EMOTION_EMOJI[emotion.dominant_emotion] ?? '❓'} ${emotion.dominant_emotion}`
              : '—'
          }
        />
        <Row
          label="Confidence"
          value={emotion ? `${emotion.confidence.toFixed(0)}%` : '—'}
        />
        <Row label="Risk score" value={emotion ? emotion.score.toFixed(2) : '—'} />
      </Card>
    </div>
  );
}
