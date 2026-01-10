/**
 * Main container for dependency tree visualization.
 */

import { useEffect, useState, useMemo } from 'react';
import { AlertTriangle, Filter } from 'lucide-react';
import { depsApi } from '@/lib/api';
import type { DependencyTree } from '@/lib/api';
import { DependencyStatsBar } from './DependencyStats';
import { DependencyDepthGroup } from './DependencyDepthGroup';
import {
  flattenByDepth,
  extractStats,
  filterByType,
  type DependencyType,
} from '@/lib/dependencyUtils';

interface DependencyTreeSectionProps {
  packageName: string;
  version?: string;
  depsCrawled: boolean;
}

export function DependencyTreeSection({
  packageName,
  version,
  depsCrawled,
}: DependencyTreeSectionProps) {
  const [tree, setTree] = useState<DependencyTree | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterTypes, setFilterTypes] = useState<DependencyType[]>(['prod']);

  useEffect(() => {
    const fetchDependencies = async () => {
      setLoading(true);
      setError(null);

      try {
        // If no version provided, fetch latest from npm
        let versionToFetch = version;
        if (!versionToFetch) {
          const response = await fetch(`https://registry.npmjs.org/${packageName}/latest`);
          if (!response.ok) {
            throw new Error('Failed to fetch latest version from npm');
          }
          const npmData = await response.json();
          versionToFetch = npmData.version;
        }

        if (!versionToFetch) {
          throw new Error('Could not determine package version');
        }

        // Get existing dependency tree from database (does not trigger a new crawl)
        const data = await depsApi.get(packageName, versionToFetch);
        setTree(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch dependencies');
      } finally {
        setLoading(false);
      }
    };

    if (depsCrawled) {
      fetchDependencies();
    }
  }, [packageName, version, depsCrawled]);

  // Process tree data
  const { stats, groupedDeps } = useMemo(() => {
    if (!tree) {
      return { stats: null, groupedDeps: {} };
    }

    const grouped = flattenByDepth(tree);
    const filtered = filterByType(grouped, filterTypes);
    const treeStats = extractStats(tree);

    return { stats: treeStats, groupedDeps: filtered };
  }, [tree, filterTypes]);

  // Toggle filter type
  const toggleFilter = (type: DependencyType) => {
    setFilterTypes((prev) => {
      if (prev.includes(type)) {
        // Don't allow removing all filters
        if (prev.length === 1) return prev;
        return prev.filter((t) => t !== type);
      }
      return [...prev, type];
    });
  };

  // Not crawled yet
  if (!depsCrawled) {
    return (
      <div className="border border-neutral-800 bg-neutral-900/50 p-8 text-center">
        <AlertTriangle className="mx-auto h-8 w-8 text-neutral-600" />
        <p className="mt-2 text-sm text-neutral-400">
          Dependencies not yet crawled. Check back after the next scan.
        </p>
      </div>
    );
  }

  // Loading state
  if (loading) {
    return (
      <div className="border border-neutral-800 bg-neutral-900/50 p-8 text-center">
        <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-neutral-800 border-t-neutral-400" />
        <p className="mt-2 text-sm text-neutral-400">Loading dependencies...</p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="border border-red-900/50 bg-red-900/10 p-4 text-sm text-red-400">
        <strong>Error:</strong> {error}
      </div>
    );
  }

  // No data
  if (!tree || !stats) {
    return (
      <div className="border border-neutral-800 bg-neutral-900/50 p-8 text-center">
        <p className="text-sm text-neutral-400">No dependency data available.</p>
      </div>
    );
  }

  // Empty dependencies
  if (stats.total === 0) {
    return (
      <div className="space-y-4">
        <DependencyStatsBar stats={stats} />
        <div className="border border-neutral-800 bg-neutral-900/50 p-8 text-center">
          <p className="text-sm text-neutral-400">This package has no dependencies.</p>
        </div>
      </div>
    );
  }

  // Get sorted depth keys
  const depthKeys = Object.keys(groupedDeps)
    .map(Number)
    .sort((a, b) => a - b);

  return (
    <div className="space-y-6">
      {/* Stats Bar */}
      <DependencyStatsBar stats={stats} />

      {/* Filter Controls */}
      <div className="flex items-center gap-3">
        <Filter className="h-4 w-4 text-neutral-500" />
        <span className="text-sm text-neutral-400">Show:</span>
        <div className="flex gap-2">
          <button
            onClick={() => toggleFilter('prod')}
            className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
              filterTypes.includes('prod')
                ? 'bg-green-600 text-white'
                : 'bg-neutral-800 text-neutral-400 hover:bg-neutral-700'
            }`}
          >
            Production
          </button>
          <button
            onClick={() => toggleFilter('dev')}
            className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
              filterTypes.includes('dev')
                ? 'bg-blue-600 text-white'
                : 'bg-neutral-800 text-neutral-400 hover:bg-neutral-700'
            }`}
          >
            Development
          </button>
          <button
            onClick={() => toggleFilter('optional')}
            className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
              filterTypes.includes('optional')
                ? 'bg-yellow-600 text-white'
                : 'bg-neutral-800 text-neutral-400 hover:bg-neutral-700'
            }`}
          >
            Optional
          </button>
          <button
            onClick={() => toggleFilter('peer')}
            className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
              filterTypes.includes('peer')
                ? 'bg-purple-600 text-white'
                : 'bg-neutral-800 text-neutral-400 hover:bg-neutral-700'
            }`}
          >
            Peer
          </button>
        </div>
      </div>

      {/* Dependency Tree grouped by depth */}
      <div className="space-y-6">
        {depthKeys.length > 0 ? (
          depthKeys.map((depth) => (
            <DependencyDepthGroup
              key={depth}
              depth={depth}
              dependencies={groupedDeps[depth]}
            />
          ))
        ) : (
          <div className="border border-neutral-800 bg-neutral-900/50 p-8 text-center">
            <p className="text-sm text-neutral-400">
              No dependencies match the selected filters.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
