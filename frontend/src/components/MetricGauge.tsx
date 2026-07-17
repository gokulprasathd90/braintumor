/**
 * MetricGauge — circular-style gauge for a single percentage metric
 * (CPU, RAM, disk, GPU).  Renders as an SVG arc with a colour-coded fill.
 */

interface Props {
  label: string;
  value: number | null;       // 0–100
  unit?: string;
  /** Threshold at which the gauge turns amber (default 70). */
  warnAt?: number;
  /** Threshold at which the gauge turns red (default 90). */
  critAt?: number;
  size?: number;
  className?: string;
}

function arcPath(cx: number, cy: number, r: number, pct: number): string {
  const angle = (pct / 100) * 270 - 135; // sweep from -135° to 135°
  const startAngle = -135 * (Math.PI / 180);
  const endAngle = angle * (Math.PI / 180);
  const x1 = cx + r * Math.cos(startAngle);
  const y1 = cy + r * Math.sin(startAngle);
  const x2 = cx + r * Math.cos(endAngle);
  const y2 = cy + r * Math.sin(endAngle);
  const large = pct > 50 ? 1 : 0;
  return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
}

export default function MetricGauge({
  label,
  value,
  unit = '%',
  warnAt = 70,
  critAt = 90,
  size = 100,
  className = '',
}: Props) {
  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.36;
  const strokeWidth = size * 0.09;

  const pct = value ?? 0;
  const colour =
    pct >= critAt ? '#ef4444' :
    pct >= warnAt ? '#f59e0b' :
    '#22c55e';

  const trackPath = arcPath(cx, cy, r, 100);
  const valuePath = arcPath(cx, cy, r, Math.min(pct, 100));

  return (
    <div
      className={`flex flex-col items-center gap-1 ${className}`}
      data-testid="metric-gauge"
      aria-label={`${label}: ${value === null ? 'N/A' : `${pct}${unit}`}`}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Track */}
        <path
          d={trackPath}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Value arc */}
        {value !== null && (
          <path
            d={valuePath}
            fill="none"
            stroke={colour}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
        )}
        {/* Centre text */}
        <text
          x={cx}
          y={cy + 4}
          textAnchor="middle"
          fontSize={size * 0.18}
          fontWeight="700"
          fill={value === null ? '#94a3b8' : colour}
        >
          {value === null ? 'N/A' : `${Math.round(pct)}${unit}`}
        </text>
      </svg>
      <p className="text-xs font-medium text-pipeline-500 text-center leading-tight">{label}</p>
    </div>
  );
}
