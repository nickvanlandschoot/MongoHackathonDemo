/**
 * Color-coded risk score badge.
 */

import { cn } from '@/lib/utils';

interface RiskBadgeProps {
  score: number;
  className?: string;
}

export function RiskBadge({ score, className }: RiskBadgeProps) {
  // Determine color based on risk score
  const colorClass =
    score < 30
      ? 'bg-green-900/20 text-green-400'
      : score < 70
        ? 'bg-yellow-900/20 text-yellow-400'
        : 'bg-red-900/20 text-red-400';

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-1 text-xs font-medium',
        colorClass,
        className
      )}
    >
      {score.toFixed(1)}
    </span>
  );
}
