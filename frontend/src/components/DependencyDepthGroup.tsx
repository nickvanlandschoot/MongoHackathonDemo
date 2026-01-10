/**
 * Groups dependencies by depth level.
 */

import { DependencyCard } from './DependencyCard';
import { getDepthLabel } from '@/lib/dependencyUtils';
import type { ProcessedDependency } from '@/lib/dependencyUtils';

interface DependencyDepthGroupProps {
  depth: number;
  dependencies: ProcessedDependency[];
}

export function DependencyDepthGroup({ depth, dependencies }: DependencyDepthGroupProps) {
  if (dependencies.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      {/* Depth Header */}
      <div className="flex items-center gap-2 border-b border-neutral-800 pb-2">
        <span className="rounded bg-neutral-800 px-2 py-1 text-xs font-semibold text-neutral-400">
          Depth {depth}
        </span>
        <h3 className="text-sm font-medium text-neutral-300">{getDepthLabel(depth)}</h3>
        <span className="text-sm text-neutral-500">({dependencies.length})</span>
      </div>

      {/* Dependency Cards */}
      <div className="space-y-2">
        {dependencies.map((dep) => (
          <DependencyCard
            key={`${dep.name}-${dep.version}-${dep.type}`}
            name={dep.name}
            version={dep.version}
            spec={dep.spec}
            type={dep.type}
            childCount={dep.childCount}
            node={dep.node}
            depth={depth}
          />
        ))}
      </div>
    </div>
  );
}
