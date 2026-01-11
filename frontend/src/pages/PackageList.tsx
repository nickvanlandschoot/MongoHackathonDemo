/**
 * Package list page with search and pagination.
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { PackageCard } from '@/components/PackageCard';
import { LoadingPackageCard } from '@/components/LoadingPackageCard';
import { Pagination } from '@/components/Pagination';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogBody } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { packagesApi } from '@/lib/api';
import { usePackagesCache, getCacheKey } from '@/lib/cache';
import type { Package } from '@/lib/api';

interface OptimisticPackage {
  name: string;
  loadedData?: Partial<Package>;
  error?: string;
}

const ITEMS_PER_PAGE = 20;

export function PackageList() {
  const navigate = useNavigate();
  const cache = usePackagesCache();
  const [packages, setPackages] = useState<Package[]>([]);
  const [optimisticPackages, setOptimisticPackages] = useState<OptimisticPackage[]>([]);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [packageToDelete, setPackageToDelete] = useState<Package | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setCurrentPage(1); // Reset to first page on search
    }, 500);

    return () => clearTimeout(timer);
  }, [search]);

  // Fetch packages when page or search changes
  const fetchPackages = async () => {
    const skip = (currentPage - 1) * ITEMS_PER_PAGE;
    const cacheKey = getCacheKey({
      skip,
      limit: ITEMS_PER_PAGE,
      search: debouncedSearch || undefined,
    });

    // Check cache first
    const cachedData = cache.getCache(cacheKey);
    if (cachedData) {
      setPackages(cachedData.packages);
      setTotal(cachedData.total);
      return;
    }

    // Fetch from API if not cached
    setLoading(true);
    setError(null);

    try {
      const response = await packagesApi.list({
        skip,
        limit: ITEMS_PER_PAGE,
        search: debouncedSearch || undefined,
      });

      setPackages(response.packages);
      setTotal(response.total);

      // Store in cache
      cache.setCache(cacheKey, response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load packages');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPackages();
  }, [currentPage, debouncedSearch]);

  const totalPages = Math.ceil(total / ITEMS_PER_PAGE);

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handlePackageClick = (pkg: Package) => {
    navigate(`/packages/${encodeURIComponent(pkg.name)}`);
  };

  const handlePackageAdded = () => {
    // Invalidate cache when a new package is added
    cache.invalidateAll();
    // Refetch to show the new package
    fetchPackages();
  };

  const handlePackageDelete = (pkg: Package) => {
    setPackageToDelete(pkg);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!packageToDelete) return;

    // Optimistically remove from state and close modal immediately
    const packageNameToDelete = packageToDelete.name;
    const packageToRestore = packageToDelete;
    setPackages((prev) => prev.filter((pkg) => pkg.name !== packageNameToDelete));
    setTotal((prev) => Math.max(0, prev - 1));
    setDeleteDialogOpen(false);
    setPackageToDelete(null);

    // Delete in background
    setDeleting(true);
    try {
      await packagesApi.delete(packageNameToDelete);
      // Invalidate cache but don't refetch - we already optimistically removed it
      cache.invalidateAll();
    } catch (err) {
      // If delete fails, restore the package and show error
      setError(err instanceof Error ? err.message : 'Failed to delete package');
      // Restore the package optimistically
      setPackages((prev) => {
        // Check if it's not already in the list
        if (!prev.find((pkg) => pkg.name === packageNameToDelete)) {
          return [...prev, packageToRestore].sort((a, b) => a.name.localeCompare(b.name));
        }
        return prev;
      });
      setTotal((prev) => prev + 1);
      // Refetch to ensure consistency
      await fetchPackages();
    } finally {
      setDeleting(false);
    }
  };

  const handleOptimisticAdd = async (packageName: string, promise: Promise<void>) => {
    // Add optimistic package to the list
    const optimisticPkg: OptimisticPackage = {
      name: packageName,
      loadedData: {},
    };
    setOptimisticPackages((prev) => [optimisticPkg, ...prev]);

    // Start polling for package data while waiting for promise
    const pollInterval = setInterval(async () => {
      try {
        const pkg = await packagesApi.get(packageName);
        // Update optimistic package with loaded data
        setOptimisticPackages((prev) =>
          prev.map((p) =>
            p.name === packageName
              ? { ...p, loadedData: pkg }
              : p
          )
        );
      } catch {
        // Package not ready yet, continue polling
      }
    }, 1000);

    try {
      await promise;
      // Wait a bit for final data to be available
      setTimeout(() => {
        // Remove optimistic package and refetch to show real data
        setOptimisticPackages((prev) => prev.filter((p) => p.name !== packageName));
        handlePackageAdded();
        clearInterval(pollInterval);
      }, 500);
    } catch (err) {
      clearInterval(pollInterval);
      // Mark optimistic package as errored
      setOptimisticPackages((prev) =>
        prev.map((p) =>
          p.name === packageName
            ? { ...p, error: err instanceof Error ? err.message : 'Failed to create package' }
            : p
        )
      );
      // Remove after a few seconds to show error
      setTimeout(() => {
        setOptimisticPackages((prev) => prev.filter((p) => p.name !== packageName));
      }, 5000);
    }
  };

  return (
    <Layout
      searchValue={search}
      onSearchChange={setSearch}
      searchPlaceholder="Search packages..."
      onPackageAdded={handlePackageAdded}
      onOptimisticAdd={handleOptimisticAdd}
    >
      <div className="px-6 py-6">
        <div className="mx-auto max-w-7xl">
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
          {!loading && packages.length === 0 && optimisticPackages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <p className="text-sm text-neutral-400">
                {search ? 'No packages match your search' : 'No packages found'}
              </p>
              {!search && (
                <p className="mt-2 text-sm text-neutral-500">
                  Click "New Package" in the sidebar to add your first package
                </p>
              )}
            </div>
          )}

          {/* Package Grid */}
          {!loading && (packages.length > 0 || optimisticPackages.length > 0) && (
            <>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {/* Optimistic packages shown first */}
                {optimisticPackages.map((optPkg) => (
                  optPkg.error ? (
                    <div
                      key={optPkg.name}
                      className="border border-red-900/50 bg-red-900/10 px-4 py-3"
                    >
                      <div className="text-sm font-medium text-red-400">
                        Failed to add {optPkg.name}
                      </div>
                      <div className="mt-1 text-xs text-red-300/70">
                        {optPkg.error}
                      </div>
                    </div>
                  ) : (
                    <LoadingPackageCard
                      key={optPkg.name}
                      packageName={optPkg.name}
                      loadedData={optPkg.loadedData}
                      onClick={() => navigate(`/packages/${encodeURIComponent(optPkg.name)}`)}
                    />
                  )
                ))}
                {/* Regular packages */}
                {packages.map((pkg) => (
                  <PackageCard
                    key={pkg.name}
                    package={pkg}
                    onClick={() => handlePackageClick(pkg)}
                    onDelete={handlePackageDelete}
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

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader onClose={() => setDeleteDialogOpen(false)}>
            <DialogTitle>Delete Package</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <p className="text-sm text-neutral-400 mb-4">
              Are you sure you want to delete <span className="text-neutral-100 font-medium">{packageToDelete?.name}</span>?
              This action cannot be undone and will delete all associated releases.
            </p>
            <div className="flex justify-end gap-2">
              <Button
                variant="secondary"
                onClick={() => {
                  setDeleteDialogOpen(false);
                  setPackageToDelete(null);
                }}
                disabled={deleting}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={confirmDelete}
                disabled={deleting}
              >
                {deleting ? 'Deleting...' : 'Delete'}
              </Button>
            </div>
          </DialogBody>
        </DialogContent>
      </Dialog>
    </Layout>
  );
}
