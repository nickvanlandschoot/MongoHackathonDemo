/**
 * Alert count badge with severity-based coloring.
 */

import { cn } from '@/lib/utils';

type Severity = 'high' | 'medium' | 'low';
type Variant = 'default' | 'compact';

interface AlertBadgeProps {
  count: number;
  severity?: Severity;
  variant?: Variant;
  className?: string;
}

export function AlertBadge({ count, severity = 'low', variant = 'default', className }: AlertBadgeProps) {
  if (count === 0) {
    return null;
  }

  // Color based on severity
  const colorClass =
    severity === 'high'
      ? 'bg-red-900/20 text-red-400 border-red-900/50'
      : severity === 'medium'
        ? 'bg-yellow-900/20 text-yellow-400 border-yellow-900/50'
        : 'bg-green-900/20 text-green-400 border-green-900/50';

  // Animation for high severity
  const animationClass = severity === 'high' ? 'animate-pulse' : '';

  // Size based on variant
  const sizeClass = variant === 'compact' ? 'px-1.5 py-0.5 text-xs' : 'px-2 py-1 text-xs';

  return (
    <span
      className={cn(
        'inline-flex items-center border font-medium',
        colorClass,
        animationClass,
        sizeClass,
        className
      )}
    >
      {count}
    </span>
  );
}
