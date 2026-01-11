/**
 * Main container for dependency tree visualization.
 */

import { useEffect, useState, useMemo } from 'react';
import { Loader2, Package, Code, CircleDashed, Users } from 'lucide-react';
import { depsApi } from '@/lib/api';
import type { DependencyTree } from '@/lib/api';
import { DependencyStatsBar } from './DependencyStats';
import { DependencyDepthGroup } from './DependencyDepthGroup';
import { useJobPolling } from '@/hooks/useJobPolling';
import {
  flattenByDepth,
  extractStats,
  filterByType,
  type DependencyType,
} from '@/lib/dependencyUtils';

interface DependencyTreeSectionProps {
  packageName: string;
  version?: string;
  onDepsCrawled?: () => void;
  onStatsLoaded?: (stats: ReturnType<typeof extractStats> | null) => void;
  hideStatsBar?: boolean;
}

export function DependencyTreeSection({
  packageName,
  version,
  onDepsCrawled,
  onStatsLoaded,
  hideStatsBar = false,
}: DependencyTreeSectionProps) {
  const [tree, setTree] = useState<DependencyTree | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterTypes, setFilterTypes] = useState<DependencyType[]>(['prod']);
  const [jobId, setJobId] = useState<string | null>(null);

  // Poll job status when fetching dependencies
  const { isPolling } = useJobPolling({
    jobId,
    onComplete: async () => {
      // Job completed, refetch the dependency tree
      try {
        let versionToFetch = version;
        if (!versionToFetch) {
          const response = await fetch(`https://registry.npmjs.org/${packageName}/latest`);
          if (response.ok) {
            const npmData = await response.json();
            versionToFetch = npmData.version;
          }
        }

        if (versionToFetch) {
          const data = await depsApi.get(packageName, versionToFetch);
          setTree(data);
        }
      } catch (err) {
        console.error('Failed to fetch dependencies after job completion:', err);
      } finally {
        setJobId(null);
        setLoading(false);
        onDepsCrawled?.();
      }
    },
    onError: (err) => {
      setError(err);
      setJobId(null);
      setLoading(false);
    },
  });

  // Fetch dependencies - try to get existing data first, trigger crawl if needed
  useEffect(() => {
    const fetchDependencies = async () => {
      // Skip if already polling a job
      if (jobId) return;

      setLoading(true);
      setError(null);

      try {
        // Get version to fetch
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

        // First, try to get existing dependency tree from database
        try {
          const data = await depsApi.get(packageName, versionToFetch);
          setTree(data);
          setLoading(false);
        } catch (err) {
          // If 404 or data doesn't exist, trigger a new crawl
          if (err instanceof Error && err.message.includes('not found')) {
            console.log('No existing dependency data found, triggering crawl...');
            const result = await depsApi.triggerFetch(packageName, versionToFetch, 3);
            setJobId(result.job_id);
            // Keep loading state active while job runs
          } else {
            throw err;
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch dependencies');
        setLoading(false);
      }
    };

    fetchDependencies();
  }, [packageName, version, jobId]);

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

  // Notify parent of stats changes
  useEffect(() => {
    onStatsLoaded?.(stats);
  }, [stats, onStatsLoaded]);

  // Toggle filter type
  const toggleFilter = (type: DependencyType) => {
    setFilterTypes((prev) => {
      if (prev.includes(type)) {
        // Allow removing all filters (0 selections allowed)
        return prev.filter((t) => t !== type);
      }
      return [...prev, type];
    });
  };

  // Loading or polling state
  if (loading || isPolling) {
    return (
      <div className="border border-neutral-800 bg-neutral-900/50 p-8 text-center">
        <Loader2 className="mx-auto h-8 w-8 animate-spin text-neutral-400" />
        <p className="mt-2 text-sm text-neutral-400">
          {isPolling ? 'Crawling dependencies...' : 'Loading dependencies...'}
        </p>
        {isPolling && (
          <p className="mt-1 text-xs text-neutral-500">
            This can take a minute or two.
          </p>
        )}
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
        {!hideStatsBar && <DependencyStatsBar stats={stats} />}
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
      {!hideStatsBar && <DependencyStatsBar stats={stats} />}

      {/* Filter Controls */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => toggleFilter('prod')}
          className={`inline-flex items-center gap-2 rounded px-3 py-1.5 text-xs font-medium transition-colors border ${
            filterTypes.includes('prod')
              ? 'bg-emerald-900/80 text-emerald-300 border-emerald-800'
              : 'bg-neutral-800 text-neutral-400 hover:bg-neutral-700 border-transparent'
          }`}
        >
          <div className="flex h-4 w-4 items-center justify-center">
            <Package className="h-3 w-3" strokeWidth={1.5} />
          </div>
          Production
        </button>
        <button
          onClick={() => toggleFilter('dev')}
          className={`inline-flex items-center gap-2 rounded px-3 py-1.5 text-xs font-medium transition-colors border ${
            filterTypes.includes('dev')
              ? 'bg-cyan-900/80 text-cyan-300 border-cyan-800'
              : 'bg-neutral-800 text-neutral-400 hover:bg-neutral-700 border-transparent'
          }`}
        >
          <div className="flex h-4 w-4 items-center justify-center">
            <Code className="h-3 w-3" strokeWidth={1.5} />
          </div>
          Development
        </button>
        <button
          onClick={() => toggleFilter('optional')}
          className={`inline-flex items-center gap-2 rounded px-3 py-1.5 text-xs font-medium transition-colors border ${
            filterTypes.includes('optional')
              ? 'bg-amber-900/80 text-amber-300 border-amber-800'
              : 'bg-neutral-800 text-neutral-400 hover:bg-neutral-700 border-transparent'
          }`}
        >
          <div className="flex h-4 w-4 items-center justify-center">
            <CircleDashed className="h-3 w-3" strokeWidth={1.5} />
          </div>
          Optional
        </button>
        <button
          onClick={() => toggleFilter('peer')}
          className={`inline-flex items-center gap-2 rounded px-3 py-1.5 text-xs font-medium transition-colors border ${
            filterTypes.includes('peer')
              ? 'bg-violet-900/80 text-violet-300 border-violet-800'
              : 'bg-neutral-800 text-neutral-400 hover:bg-neutral-700 border-transparent'
          }`}
        >
          <div className="flex h-4 w-4 items-center justify-center">
            <Users className="h-3 w-3" strokeWidth={1.5} />
          </div>
          Peer
        </button>
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
