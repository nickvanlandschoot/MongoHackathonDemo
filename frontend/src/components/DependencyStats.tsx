/**
 * Summary statistics bar for dependency tree.
 */

import type { DependencyStats } from '@/lib/dependencyUtils';

interface DependencyStatsProps {
  stats: DependencyStats;
}

export function DependencyStatsBar({ stats }: DependencyStatsProps) {
  return (
    <div className="grid grid-cols-2 gap-4 border border-neutral-800 bg-neutral-900/50 p-4 sm:grid-cols-4">
      {/* Total Dependencies */}
      <div>
        <div className="text-sm text-neutral-500">Total Dependencies</div>
        <div className="mt-1 text-2xl font-semibold text-neutral-100">{stats.total}</div>
      </div>

      {/* Production Dependencies */}
      <div>
        <div className="text-sm text-neutral-500">Production</div>
        <div className="mt-1 text-2xl font-semibold text-neutral-100">{stats.byType.prod}</div>
      </div>

      {/* Development Dependencies */}
      <div>
        <div className="text-sm text-neutral-500">Development</div>
        <div className="mt-1 text-2xl font-semibold text-neutral-100">{stats.byType.dev}</div>
      </div>

      {/* Maximum Depth */}
      <div>
        <div className="text-sm text-neutral-500">Maximum Depth</div>
        <div className="mt-1 text-2xl font-semibold text-neutral-100">{stats.maxDepth}</div>
      </div>
    </div>
  );
}
