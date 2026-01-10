/**
 * Package detail page showing all package information.
 */

import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, ExternalLink, Package as PackageIcon, Check, X, User } from 'lucide-react';
import { Layout } from '@/components/Layout';
import { RiskBadge } from '@/components/RiskBadge';
import { DependencyTreeSection } from '@/components/DependencyTreeSection';
import { packagesApi } from '@/lib/api';
import type { Package, Identity } from '@/lib/api';

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
  const { name } = useParams<{ name: string }>();
  const [pkg, setPkg] = useState<Package | null>(null);
  const [maintainers, setMaintainers] = useState<Identity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [maintainersLoading, setMaintainersLoading] = useState(false);

  useEffect(() => {
    const fetchPackage = async () => {
      if (!name) return;

      setLoading(true);
      setError(null);

      try {
        const data = await packagesApi.get(name);
        setPkg(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load package');
      } finally {
        setLoading(false);
      }
    };

    fetchPackage();
  }, [name]);

  useEffect(() => {
    const fetchMaintainers = async () => {
      if (!name || !pkg?.scan_state.maintainers_crawled) return;

      setMaintainersLoading(true);

      try {
        const data = await packagesApi.getMaintainers(name);
        setMaintainers(data);
      } catch (err) {
        console.error('Failed to fetch maintainers:', err);
      } finally {
        setMaintainersLoading(false);
      }
    };

    fetchMaintainers();
  }, [name, pkg?.scan_state.maintainers_crawled]);

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

  const analysisUpdated = pkg.analysis.updated_at
    ? new Date(pkg.analysis.updated_at).toLocaleString()
    : 'Unknown';

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

        {/* Header */}
        <div className="mb-6 flex items-start justify-between">
          <div className="flex items-center gap-3">
            <PackageIcon className="h-8 w-8 text-neutral-400" />
            <div>
              <h1 className="text-3xl font-semibold text-neutral-100">{pkg.name}</h1>
              <div className="mt-1 flex items-center gap-2">
                <span className="inline-flex items-center border border-neutral-800 bg-neutral-900 px-2 py-0.5 text-xs font-medium text-neutral-400">
                  {pkg.registry}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {/* Package Information and Scan Status - Side by Side */}
          <div className="grid grid-cols-2 gap-4">
            {/* Package Information */}
            <div className="border border-neutral-800 bg-neutral-900/50 p-4">
              <h2 className="mb-4 text-sm font-semibold text-neutral-100">Package Information</h2>
              <div className="space-y-3 text-sm">
                <div>
                  <div className="text-neutral-500">Owner</div>
                  <div className="mt-1 text-neutral-100">
                    {pkg.owner || 'Unknown'}
                  </div>
                </div>
                <div>
                  <div className="text-neutral-500">Registry</div>
                  <div className="mt-1 text-neutral-100">{pkg.registry}</div>
                </div>
                <div>
                  <div className="text-neutral-500">Last Release</div>
                  <div className="mt-1 text-neutral-100">
                    {lastRelease}
                    {pkg.latest_release_version && (
                      <span className="ml-2 text-neutral-500">
                        (v{pkg.latest_release_version})
                      </span>
                    )}
                  </div>
                </div>
                {pkg.repo_url && (
                  <div>
                    <div className="text-neutral-500">Repository</div>
                    <div className="mt-1">
                      <a
                        href={parseGitHubUrl(pkg.repo_url)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-neutral-100 transition-colors hover:text-neutral-400"
                      >
                        View on GitHub
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Scan Status */}
            <div className="border border-neutral-800 bg-neutral-900/50 p-4">
              <h2 className="mb-4 text-sm font-semibold text-neutral-100">Scan Status</h2>
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-neutral-400">Dependencies Crawled</span>
                  <span className="flex items-center gap-1.5 text-neutral-100">
                    {pkg.scan_state.deps_crawled ? (
                      <>
                        <Check className="h-4 w-4 text-green-400" />
                        Yes
                      </>
                    ) : (
                      <>
                        <X className="h-4 w-4 text-neutral-500" />
                        No
                      </>
                    )}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-neutral-400">Releases Crawled</span>
                  <span className="flex items-center gap-1.5 text-neutral-100">
                    {pkg.scan_state.releases_crawled ? (
                      <>
                        <Check className="h-4 w-4 text-green-400" />
                        Yes
                      </>
                    ) : (
                      <>
                        <X className="h-4 w-4 text-neutral-500" />
                        No
                      </>
                    )}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-neutral-400">Maintainers Crawled</span>
                  <span className="flex items-center gap-1.5 text-neutral-100">
                    {pkg.scan_state.maintainers_crawled ? (
                      <>
                        <Check className="h-4 w-4 text-green-400" />
                        Yes
                      </>
                    ) : (
                      <>
                        <X className="h-4 w-4 text-neutral-500" />
                        No
                      </>
                    )}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-neutral-400">Crawl Depth</span>
                  <span className="text-neutral-100">
                    {pkg.scan_state.crawl_depth}
                  </span>
                </div>
                {pkg.scan_state.last_full_scan && (
                  <div className="flex items-center justify-between">
                    <span className="text-neutral-400">Last Full Scan</span>
                    <span className="text-neutral-100">
                      {new Date(pkg.scan_state.last_full_scan).toLocaleString()}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Analysis Section - Not a Card */}
          <div className="border-t border-neutral-800 pt-6">
            <div className="mb-6 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-neutral-100">Risk Analysis</h2>
              <RiskBadge score={pkg.risk_score} className="text-base px-3 py-1.5" />
            </div>

            <div className="space-y-6">
              <div className="flex items-center gap-6">
                <div>
                  <div className="text-6xl font-semibold text-neutral-100">
                    {pkg.risk_score.toFixed(1)}
                  </div>
                  <div className="mt-1 text-sm text-neutral-500">Risk Score</div>
                </div>
                <div className="text-sm text-neutral-400">
                  Risk score ranges from 0 (low risk) to 100 (high risk)
                </div>
              </div>

              <div>
                <h3 className="mb-2 text-sm font-semibold text-neutral-100">Summary</h3>
                <div className="text-sm text-neutral-300">{pkg.analysis.summary}</div>
              </div>

              {pkg.analysis.reasons.length > 0 && (
                <div>
                  <h3 className="mb-2 text-sm font-semibold text-neutral-100">Risk Factors</h3>
                  <ul className="space-y-2 text-sm text-neutral-400">
                    {pkg.analysis.reasons.map((reason, index) => (
                      <li key={index} className="flex items-start gap-2">
                        <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 bg-red-500" />
                        {reason}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="grid grid-cols-3 gap-6 border-t border-neutral-800 pt-4">
                <div>
                  <div className="text-sm text-neutral-500">Confidence</div>
                  <div className="mt-1 text-lg font-medium text-neutral-100">
                    {(pkg.analysis.confidence * 100).toFixed(0)}%
                  </div>
                </div>
                <div>
                  <div className="text-sm text-neutral-500">Source</div>
                  <div className="mt-1 text-lg font-medium text-neutral-100 capitalize">
                    {pkg.analysis.source}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-neutral-500">Updated</div>
                  <div className="mt-1 text-lg font-medium text-neutral-100">{analysisUpdated}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Maintainers Section */}
          <div className="border-t border-neutral-800 pt-6">
            <h2 className="mb-4 text-xl font-semibold text-neutral-100">Maintainers</h2>
            {!pkg.scan_state.maintainers_crawled ? (
              <div className="border border-neutral-800 bg-neutral-900/50 p-8 text-center">
                <User className="mx-auto h-8 w-8 text-neutral-600" />
                <p className="mt-2 text-sm text-neutral-400">
                  Maintainers not yet crawled. Check back after the next scan.
                </p>
              </div>
            ) : maintainersLoading ? (
              <div className="border border-neutral-800 bg-neutral-900/50 p-8 text-center">
                <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-neutral-800 border-t-neutral-400" />
                <p className="mt-2 text-sm text-neutral-400">Loading maintainers...</p>
              </div>
            ) : maintainers.length === 0 ? (
              <div className="border border-neutral-800 bg-neutral-900/50 p-8 text-center">
                <p className="text-sm text-neutral-400">No maintainer information available.</p>
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {maintainers.map((maintainer) => (
                  <div
                    key={maintainer.id || maintainer.handle}
                    className="border border-neutral-800 bg-neutral-900/50 p-4"
                  >
                    <div className="mb-3 flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <User className="h-5 w-5 text-neutral-400" />
                        <div>
                          <div className="font-medium text-neutral-100">{maintainer.handle}</div>
                          <div className="text-xs text-neutral-500 capitalize">{maintainer.kind}</div>
                        </div>
                      </div>
                      <RiskBadge score={maintainer.risk_score} className="text-xs px-2 py-0.5" />
                    </div>

                    {maintainer.email_domain && (
                      <div className="mb-2 text-xs text-neutral-400">
                        <span className="text-neutral-500">Email:</span> {maintainer.email_domain}
                      </div>
                    )}

                    <div className="mb-2 flex items-center gap-2 text-xs">
                      <span className="text-neutral-500">Affiliation:</span>
                      <span className="capitalize text-neutral-300">{maintainer.affiliation_tag}</span>
                    </div>

                    {maintainer.country && (
                      <div className="mb-2 text-xs">
                        <span className="text-neutral-500">Country:</span>{' '}
                        <span className="text-neutral-300">{maintainer.country}</span>
                      </div>
                    )}

                    <div className="mt-3 border-t border-neutral-800 pt-3">
                      <div className="text-xs text-neutral-400">{maintainer.analysis.summary}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Dependencies Section */}
          <div className="border-t border-neutral-800 pt-6">
            <h2 className="mb-4 text-xl font-semibold text-neutral-100">Dependencies</h2>
            <DependencyTreeSection
              packageName={pkg.name}
              version={pkg.latest_release_version}
              depsCrawled={pkg.scan_state.deps_crawled}
            />
          </div>
        </div>
        </div>
      </div>
    </Layout>
  );
}
