/**
 * Color-coded risk level badge with confidence indicator.
 */

import { cn } from '@/lib/utils';

interface RiskLevelBadgeProps {
  level: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  className?: string;
}

export function RiskLevelBadge({ level, confidence, className }: RiskLevelBadgeProps) {
  const colorClass =
    level === 'low'
      ? 'bg-green-900/20 text-green-400'
      : level === 'medium'
        ? 'bg-yellow-900/20 text-yellow-400'
        : level === 'high'
          ? 'bg-red-900/20 text-red-400'
          : 'bg-red-950/30 text-red-300';

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-1 text-xs font-medium',
        colorClass,
        className
      )}
    >
      <span className="capitalize">{level}</span>
      <span className="text-neutral-500">({Math.round(confidence * 100)}%)</span>
    </span>
  );
}
