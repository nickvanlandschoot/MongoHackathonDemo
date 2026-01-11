/**
 * Package detail page showing all package information.
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, ExternalLink, Package as PackageIcon } from 'lucide-react';
import { Layout } from '@/components/Layout';
import { DependencyTreeSection } from '@/components/DependencyTreeSection';
import { AlertList } from '@/components/AlertList';
import { ThreatSurfaceSection } from '@/components/ThreatSurfaceSection';
import { packagesApi } from '@/lib/api';
import { usePackageDetailCache } from '@/lib/cache';
import type { Package } from '@/lib/api';
import type { DependencyStats } from '@/lib/dependencyUtils';

/**
 * Parse and clean GitHub URL from various npm repository URL formats.
 * Handles: git+https://, git://, .git suffixes, etc.
 */
function parseGitHubUrl(repoUrl: string): string {
  let url = repoUrl;

  // Remove git+ prefix
  if (url.startsWith('git+')) {
    url = url.substring(4);
  }

  // Replace git:// with https://
  if (url.startsWith('git://')) {
    url = url.replace('git://', 'https://');
  }

  // Remove .git suffix
  if (url.endsWith('.git')) {
    url = url.substring(0, url.length - 4);
  }

  return url;
}

export function PackageDetail() {
  // Use wildcard param to support scoped npm packages like @scope/package
  const { "*": name } = useParams();
  const cache = usePackageDetailCache();
  const [pkg, setPkg] = useState<Package | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [depStats, setDepStats] = useState<DependencyStats | null>(null);

  const fetchPackage = useCallback(async () => {
    if (!name) return;

    // Check cache first
    const cachedPackage = cache.getCache(name);
    if (cachedPackage) {
      setPkg(cachedPackage);
      setLoading(false);
      return;
    }

    // Fetch from API if not cached
    setLoading(true);
    setError(null);

    try {
      const data = await packagesApi.get(name);
      setPkg(data);
      // Store in cache
      cache.setCache(name, data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load package');
    } finally {
      setLoading(false);
    }
  }, [name, cache]);

  useEffect(() => {
    fetchPackage();
  }, [fetchPackage]);

  if (loading) {
    return (
      <Layout>
        <div className="px-6 py-8">
          <div className="mx-auto max-w-4xl">
            <div className="flex items-center justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-neutral-800 border-t-neutral-400" />
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  if (error || !pkg) {
    return (
      <Layout>
        <div className="px-6 py-8">
          <div className="mx-auto max-w-4xl">
            <Link
              to="/"
              className="mb-6 inline-flex items-center gap-2 text-sm text-neutral-400 transition-colors hover:text-neutral-100"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Packages
            </Link>
            <div className="border border-red-900/50 bg-red-900/10 px-4 py-3 text-sm text-red-400">
              {error || 'Package not found'}
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  const lastRelease = pkg.latest_release_date
    ? new Date(pkg.latest_release_date).toLocaleString()
    : 'No releases';

  return (
    <Layout>
      <div className="px-6 py-8">
        <div className="mx-auto max-w-6xl">
        {/* Back Link */}
        <Link
          to="/"
          className="mb-6 inline-flex items-center gap-2 text-sm text-neutral-400 transition-colors hover:text-neutral-100"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Packages
        </Link>

        {/* Package Header Card */}
        <div className="mb-6 border border-neutral-800 bg-neutral-900/50 p-6">
          <div className="flex items-center justify-between">
            {/* Left side - Package Name & Icon */}
            <div className="flex items-start gap-4">
              <PackageIcon className="h-10 w-10 text-neutral-400" />
              <div>
                <h1 className="text-3xl font-semibold text-neutral-100">{pkg.name}</h1>
                <div className="mt-2 flex items-center gap-3">
                  <span className="inline-flex items-center border border-neutral-800 bg-neutral-900 px-2 py-0.5 text-xs font-medium text-neutral-400">
                    {pkg.registry}
                  </span>
                  {pkg.owner && (
                    <span className="text-sm text-neutral-400">
                      by <span className="text-neutral-300">{pkg.owner}</span>
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Right side - Package Details */}
            <div className="flex items-start gap-8">
              {/* Last Release */}
              <div>
                <div className="text-xs font-medium text-neutral-500">LAST RELEASE</div>
                <div className="mt-1.5 text-sm text-neutral-100">
                  {lastRelease}
                  {pkg.latest_release_version && (
                    <span className="ml-2 text-neutral-500">
                      v{pkg.latest_release_version}
                    </span>
                  )}
                </div>
              </div>

              {/* Repository */}
              {pkg.repo_url && (
                <div>
                  <div className="text-xs font-medium text-neutral-500">REPOSITORY</div>
                  <div className="mt-1.5">
                    <a
                      href={parseGitHubUrl(pkg.repo_url)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-sm text-neutral-100 transition-colors hover:text-neutral-400"
                    >
                      View on GitHub
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </div>
                </div>
              )}

              {/* Dependency Stats */}
              {depStats && (
                <div className="flex items-start gap-6 text-xs">
                  <div>
                    <div className="text-neutral-500">Total</div>
                    <div className="mt-1 text-lg font-semibold text-neutral-100">{depStats.total}</div>
                  </div>
                  <div>
                    <div className="text-neutral-500">Prod</div>
                    <div className="mt-1 text-lg font-semibold text-neutral-100">{depStats.byType.prod}</div>
                  </div>
                  <div>
                    <div className="text-neutral-500">Dev</div>
                    <div className="mt-1 text-lg font-semibold text-neutral-100">{depStats.byType.dev}</div>
                  </div>
                  <div>
                    <div className="text-neutral-500">Depth</div>
                    <div className="mt-1 text-lg font-semibold text-neutral-100">{depStats.maxDepth}</div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-6">

          {/* Dependencies Section */}
          <div className="border-t border-neutral-800 pt-6">
            <h2 className="mb-4 text-xl font-semibold text-neutral-100">Dependencies</h2>
            <DependencyTreeSection
              packageName={pkg.name}
              version={pkg.latest_release_version}
              onDepsCrawled={fetchPackage}
              onStatsLoaded={setDepStats}
              hideStatsBar={true}
            />
          </div>

          {/* Threat Surface Assessment Section */}
          <div className="border-t border-neutral-800 pt-6">
            <h2 className="mb-4 text-xl font-semibold text-neutral-100">Threat Surface Assessment</h2>
            <ThreatSurfaceSection packageName={pkg.name} />
          </div>

          {/* Security Alerts Section */}
          <div className="border-t border-neutral-800 pt-6">
            <h2 className="mb-4 text-xl font-semibold text-neutral-100">Security Alerts</h2>
            <AlertList packageName={pkg.name} maxDisplay={5} />
          </div>
        </div>
        </div>
      </div>
    </Layout>
  );
}
