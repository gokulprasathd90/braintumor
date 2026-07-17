/**
 * AlertsBanner — displays threshold-based system alerts from the overview.
 * Renders nothing when there are no alerts.
 */

import type { DashboardAlert } from '@/types';

interface Props {
  alerts: DashboardAlert[];
}

const STYLES = {
  critical: {
    wrapper: 'bg-red-50 border-red-200',
    icon: '🔴',
    text: 'text-red-800',
    badge: 'bg-red-100 text-red-700',
  },
  warning: {
    wrapper: 'bg-amber-50 border-amber-200',
    icon: '🟡',
    text: 'text-amber-800',
    badge: 'bg-amber-100 text-amber-700',
  },
} as const;

export default function AlertsBanner({ alerts }: Props) {
  if (alerts.length === 0) return null;

  const criticals = alerts.filter((a) => a.level === 'critical');
  const warnings  = alerts.filter((a) => a.level === 'warning');

  return (
    <div className="space-y-2" data-testid="alerts-banner" role="alert">
      {[...criticals, ...warnings].map((alert, i) => {
        const s = STYLES[alert.level];
        return (
          <div
            key={i}
            className={`flex items-start gap-3 rounded-xl border px-4 py-3 ${s.wrapper}`}
          >
            <span className="text-base leading-none mt-0.5">{s.icon}</span>
            <div className="flex-1 min-w-0">
              <span className={`text-xs font-semibold uppercase tracking-wide ${s.text}`}>
                {alert.level}
              </span>
              <span className={`ml-2 text-xs px-1.5 py-0.5 rounded font-medium ${s.badge}`}>
                {alert.domain}
              </span>
              <p className={`text-sm mt-0.5 ${s.text}`}>{alert.message}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
