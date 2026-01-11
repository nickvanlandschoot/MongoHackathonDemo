/**
 * Alerts dashboard page with filtering and pagination.
 */

import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronDown } from 'lucide-react';
import { Layout } from '@/components/Layout';
import { AlertCard } from '@/components/AlertCard';
import { Pagination } from '@/components/Pagination';
import { alertsApi } from '@/lib/api';
import { useAlertsCache, getAlertsCacheKey } from '@/lib/cache';
import type { RiskAlert, AlertStats } from '@/lib/api';

const ITEMS_PER_PAGE = 20;

type StatusFilter = 'all' | 'open' | 'investigated' | 'resolved';
type SortOption = 'newest' | 'oldest' | 'severity';

export function AlertsDashboard() {
  const navigate = useNavigate();
  const cache = useAlertsCache();
  const [alerts, setAlerts] = useState<RiskAlert[]>([]);
  const [stats, setStats] = useState<AlertStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [sortOption, setSortOption] = useState<SortOption>('newest');
  const [statusDropdownOpen, setStatusDropdownOpen] = useState(false);
  const [sortDropdownOpen, setSortDropdownOpen] = useState(false);
  const statusDropdownRef = useRef<HTMLDivElement>(null);
  const sortDropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (statusDropdownRef.current && !statusDropdownRef.current.contains(event.target as Node)) {
        setStatusDropdownOpen(false);
      }
      if (sortDropdownRef.current && !sortDropdownRef.current.contains(event.target as Node)) {
        setSortDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Fetch stats on mount
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const statsData = await alertsApi.getStats();
        setStats(statsData);
      } catch (err) {
        console.error('Failed to fetch stats:', err);
      }
    };
    fetchStats();
  }, []);

  // Fetch alerts when filters or page changes
  const fetchAlerts = async () => {
    const skip = (currentPage - 1) * ITEMS_PER_PAGE;
    const cacheKey = getAlertsCacheKey({
      skip,
      limit: ITEMS_PER_PAGE,
      status: statusFilter !== 'all' ? statusFilter : undefined,
      sortOption,
    });

    // Check cache first
    const cachedData = cache.getCache(cacheKey);
    if (cachedData) {
      // Apply client-side sorting to cached data
      let sortedAlerts = [...cachedData.alerts];
      if (sortOption === 'oldest') {
        sortedAlerts.reverse();
      } else if (sortOption === 'severity') {
        sortedAlerts.sort((a, b) => b.severity - a.severity);
      }
      setAlerts(sortedAlerts);
      setTotal(cachedData.total);
      return;
    }

    // Fetch from API if not cached
    setLoading(true);
    setError(null);

    try {
      // Build API params
      const params: {
        skip: number;
        limit: number;
        status?: 'open' | 'investigated' | 'resolved';
        severity_min?: number;
      } = {
        skip,
        limit: ITEMS_PER_PAGE,
      };

      // Add status filter
      if (statusFilter !== 'all') {
        params.status = statusFilter as 'open' | 'investigated' | 'resolved';
      }

      const response = await alertsApi.list(params);

      // Store in cache before sorting
      cache.setCache(cacheKey, response);

      // Apply client-side sorting
      let sortedAlerts = [...response.alerts];
      if (sortOption === 'oldest') {
        sortedAlerts.reverse();
      } else if (sortOption === 'severity') {
        sortedAlerts.sort((a, b) => b.severity - a.severity);
      }

      setAlerts(sortedAlerts);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load alerts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [currentPage, statusFilter, sortOption]);

  const totalPages = Math.ceil(total / ITEMS_PER_PAGE);

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleStatusChange = async (alertId: string, newStatus: 'open' | 'investigated' | 'resolved') => {
    try {
      // Optimistically update the UI
      setAlerts((prev) =>
        prev.map((alert) =>
          alert.id === alertId ? { ...alert, status: newStatus } : alert
        )
      );

      // Update on server
      await alertsApi.updateStatus(alertId, newStatus);

      // Invalidate cache since alert status changed
      cache.invalidateAll();

      // Refetch stats to update counts
      const statsData = await alertsApi.getStats();
      setStats(statsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update alert status');
      // Invalidate cache and refetch to revert optimistic update
      cache.invalidateAll();
      await fetchAlerts();
    }
  };

  const handleViewPackage = (packageName: string) => {
    navigate(`/packages/${encodeURIComponent(packageName)}`);
  };

  return (
    <Layout>
      <div className="px-6 py-6">
        <div className="mx-auto max-w-7xl">

          {/* Stats Bar */}
          {stats && (
            <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div className="border border-neutral-800 bg-neutral-900/30 px-4 py-3">
                <div className="text-2xl font-bold text-neutral-100">{stats.open_alerts}</div>
                <div className="text-xs text-neutral-400">Open Alerts</div>
              </div>
              <div className="border border-neutral-800 bg-neutral-900/30 px-4 py-3">
                <div className="text-2xl font-bold text-neutral-100">{stats.investigated_alerts}</div>
                <div className="text-xs text-neutral-400">Investigated</div>
              </div>
              <div className="border border-neutral-800 bg-neutral-900/30 px-4 py-3">
                <div className="text-2xl font-bold text-neutral-100">{stats.resolved_alerts}</div>
                <div className="text-xs text-neutral-400">Resolved</div>
              </div>
            </div>
          )}

          {/* Filters - Compact Layout */}
          <div className="mb-6 flex items-center gap-6">
            {/* Status Dropdown */}
            <div className="relative" ref={statusDropdownRef}>
              <button
                onClick={() => setStatusDropdownOpen(!statusDropdownOpen)}
                className="flex items-center gap-1.5 text-sm text-neutral-300 hover:text-neutral-100 transition-colors"
              >
                <span>
                  {statusFilter === 'all' ? 'All Status' :
                   statusFilter === 'open' ? 'Open' :
                   statusFilter === 'investigated' ? 'Investigated' : 'Resolved'}
                </span>
                <ChevronDown className="h-3.5 w-3.5 text-neutral-400" />
              </button>
              {statusDropdownOpen && (
                <div className="absolute top-full mt-1 bg-neutral-900 border border-neutral-800 py-1 min-w-[140px] z-10">
                  <button
                    onClick={() => {
                      setStatusFilter('all');
                      setCurrentPage(1);
                      setStatusDropdownOpen(false);
                    }}
                    className="w-full text-left px-3 py-1.5 text-sm text-neutral-300 hover:bg-neutral-800 hover:text-neutral-100 transition-colors"
                  >
                    All Status
                  </button>
                  <button
                    onClick={() => {
                      setStatusFilter('open');
                      setCurrentPage(1);
                      setStatusDropdownOpen(false);
                    }}
                    className="w-full text-left px-3 py-1.5 text-sm text-neutral-300 hover:bg-neutral-800 hover:text-neutral-100 transition-colors"
                  >
                    Open
                  </button>
                  <button
                    onClick={() => {
                      setStatusFilter('investigated');
                      setCurrentPage(1);
                      setStatusDropdownOpen(false);
                    }}
                    className="w-full text-left px-3 py-1.5 text-sm text-neutral-300 hover:bg-neutral-800 hover:text-neutral-100 transition-colors"
                  >
                    Investigated
                  </button>
                  <button
                    onClick={() => {
                      setStatusFilter('resolved');
                      setCurrentPage(1);
                      setStatusDropdownOpen(false);
                    }}
                    className="w-full text-left px-3 py-1.5 text-sm text-neutral-300 hover:bg-neutral-800 hover:text-neutral-100 transition-colors"
                  >
                    Resolved
                  </button>
                </div>
              )}
            </div>


            {/* Sort Dropdown */}
            <div className="relative" ref={sortDropdownRef}>
              <button
                onClick={() => setSortDropdownOpen(!sortDropdownOpen)}
                className="flex items-center gap-1.5 text-sm text-neutral-300 hover:text-neutral-100 transition-colors"
              >
                <span>
                  {sortOption === 'newest' ? 'Newest First' :
                   sortOption === 'oldest' ? 'Oldest First' : 'Highest Severity'}
                </span>
                <ChevronDown className="h-3.5 w-3.5 text-neutral-400" />
              </button>
              {sortDropdownOpen && (
                <div className="absolute top-full mt-1 bg-neutral-900 border border-neutral-800 py-1 min-w-[140px] z-10">
                  <button
                    onClick={() => {
                      setSortOption('newest');
                      setCurrentPage(1);
                      setSortDropdownOpen(false);
                    }}
                    className="w-full text-left px-3 py-1.5 text-sm text-neutral-300 hover:bg-neutral-800 hover:text-neutral-100 transition-colors"
                  >
                    Newest First
                  </button>
                  <button
                    onClick={() => {
                      setSortOption('oldest');
                      setCurrentPage(1);
                      setSortDropdownOpen(false);
                    }}
                    className="w-full text-left px-3 py-1.5 text-sm text-neutral-300 hover:bg-neutral-800 hover:text-neutral-100 transition-colors"
                  >
                    Oldest First
                  </button>
                  <button
                    onClick={() => {
                      setSortOption('severity');
                      setCurrentPage(1);
                      setSortDropdownOpen(false);
                    }}
                    className="w-full text-left px-3 py-1.5 text-sm text-neutral-300 hover:bg-neutral-800 hover:text-neutral-100 transition-colors"
                  >
                    Highest Severity
                  </button>
                </div>
              )}
            </div>
          </div>


          {/* Error State */}
          {error && (
            <div className="mb-6 border border-red-900/50 bg-red-900/10 px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}

          {/* Loading State */}
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-neutral-800 border-t-neutral-400" />
            </div>
          )}

          {/* Empty State */}
          {!loading && alerts.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <p className="text-sm text-neutral-400">
                No alerts found matching your filters
              </p>
              <p className="mt-2 text-sm text-neutral-500">
                Try adjusting your filters or check back later
              </p>
            </div>
          )}

          {/* Alerts Grid */}
          {!loading && alerts.length > 0 && (
            <>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                {alerts.map((alert) => (
                  <AlertCard
                    key={alert.id}
                    alert={alert}
                    onStatusChange={handleStatusChange}
                    onViewPackage={handleViewPackage}
                  />
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="mt-6">
                  <Pagination
                    currentPage={currentPage}
                    totalPages={totalPages}
                    onPageChange={handlePageChange}
                  />
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </Layout>
  );
}
