/**
 * Color-coded maintainer trust level badge.
 */

import { cn } from '@/lib/utils';

interface MaintainerTrustBadgeProps {
  level: 'trustworthy' | 'moderate' | 'concerning';
  className?: string;
}

export function MaintainerTrustBadge({ level, className }: MaintainerTrustBadgeProps) {
  const colorClass =
    level === 'trustworthy'
      ? 'bg-green-900/20 text-green-400'
      : level === 'moderate'
        ? 'bg-yellow-900/20 text-yellow-400'
        : 'bg-red-900/20 text-red-400';

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-1 text-xs font-medium capitalize',
        colorClass,
        className
      )}
    >
      {level}
    </span>
  );
}
