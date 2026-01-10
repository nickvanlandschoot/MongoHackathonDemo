/**
 * Package creation form page.
 */

import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { packagesApi } from '@/lib/api';

export function PackageCreate() {
  const navigate = useNavigate();
  const [packageName, setPackageName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!packageName.trim()) {
      setError('Package name is required');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const pkg = await packagesApi.create(packageName.trim());
      navigate(`/packages/${encodeURIComponent(pkg.name)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create package');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 px-6 py-8">
      <div className="mx-auto max-w-md">
        {/* Back Link */}
        <Link
          to="/"
          className="mb-6 inline-flex items-center gap-2 text-sm text-neutral-400 transition-colors hover:text-neutral-100"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Packages
        </Link>

        {/* Form Card */}
        <Card>
          <CardHeader>
            <CardTitle>Add Package</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Package Name Input */}
              <div>
                <label
                  htmlFor="packageName"
                  className="mb-2 block text-sm font-medium text-neutral-100"
                >
                  Package Name
                </label>
                <input
                  id="packageName"
                  type="text"
                  value={packageName}
                  onChange={(e) => setPackageName(e.target.value)}
                  placeholder="e.g., express"
                  className="w-full rounded-lg border border-neutral-800 bg-neutral-950/50 px-3 py-3 text-sm text-neutral-100 placeholder:text-neutral-400 focus:border-neutral-700 focus:outline-none focus:ring-3 focus:ring-neutral-700/24"
                  disabled={loading}
                />
                <p className="mt-2 text-xs text-neutral-400">
                  Enter npm package name. We'll fetch the latest version automatically.
                </p>
              </div>

              {/* Error Message */}
              {error && (
                <div className="rounded-lg border border-red-900/50 bg-red-900/10 px-3 py-2 text-sm text-red-400">
                  {error}
                </div>
              )}

              {/* Submit Button */}
              <Button type="submit" disabled={loading} className="w-full">
                {loading ? (
                  <>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    Adding...
                  </>
                ) : (
                  'Add Package'
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
