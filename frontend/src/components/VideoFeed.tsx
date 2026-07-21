import { StreamData } from '../types';

interface Props {
  data: StreamData | null;
  isConnected: boolean;
  error: string | null;
}

const STATUS_STYLES: Record<string, string> = {
  safe: 'bg-safe text-black',
  caution: 'bg-caution text-black',
  danger: 'bg-danger text-white animate-pulse',
};

export default function VideoFeed({ data, isConnected, error }: Props) {
  return (
    <div className="relative rounded-xl overflow-hidden bg-card border border-slate-700 aspect-video">
      {data?.frame ? (
        <img
          src={`data:image/jpeg;base64,${data.frame}`}
          alt="Live driver feed"
          className="w-full h-full object-cover"
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center text-slate-400">
          {error ? (
            <div className="text-danger text-center px-6">⚠️ {error}</div>
          ) : isConnected ? (
            <div className="animate-pulse">Waiting for camera feed…</div>
          ) : (
            <div>Connecting to backend…</div>
          )}
        </div>
      )}

      {/* connection status */}
      <div className="absolute top-3 left-3 flex items-center gap-2 bg-black/60 rounded-full px-3 py-1 text-xs">
        <span
          className={`w-2 h-2 rounded-full ${isConnected ? 'bg-safe' : 'bg-danger'}`}
        />
        {isConnected ? 'LIVE' : 'OFFLINE'}
      </div>

      {/* risk status badge */}
      {data && (
        <div
          className={`absolute top-3 right-3 rounded-md px-3 py-1 text-sm font-bold ${
            STATUS_STYLES[data.status] ?? STATUS_STYLES.safe
          }`}
        >
          {data.status.toUpperCase()}
        </div>
      )}

      {/* metric overlay */}
      {data && (
        <div className="absolute bottom-0 inset-x-0 bg-black/60 px-4 py-2 flex flex-wrap gap-x-6 gap-y-1 text-xs font-mono">
          <span>EAR {data.drowsiness.ear.toFixed(2)}</span>
          <span>emotion: {data.emotion.dominant_emotion}</span>
          <span>flow {data.aggression.flow_magnitude.toFixed(1)}</span>
        </div>
      )}
    </div>
  );
}
