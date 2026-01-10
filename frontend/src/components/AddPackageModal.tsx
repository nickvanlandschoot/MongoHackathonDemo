/**
 * Modal for adding a new package.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogBody,
} from '@/components/ui/dialog';
import { packagesApi } from '@/lib/api';

interface AddPackageModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  onOptimisticAdd?: (packageName: string, promise: Promise<void>) => void;
}

export function AddPackageModal({ open, onOpenChange, onSuccess, onOptimisticAdd }: AddPackageModalProps) {
  const navigate = useNavigate();
  const [packageName, setPackageName] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!packageName.trim()) {
      setError('Package name is required');
      return;
    }

    const trimmedName = packageName.trim();
    setError(null);

    // Close modal immediately for optimistic UI
    setPackageName('');
    onOpenChange(false);

    // Create promise for the package creation
    const createPromise = (async () => {
      try {
        const pkg = await packagesApi.create(trimmedName);
        if (onSuccess) {
          onSuccess();
        }
        navigate(`/packages/${encodeURIComponent(pkg.name)}`);
      } catch (err) {
        throw err;
      }
    })();

    // Notify parent with optimistic package and promise
    if (onOptimisticAdd) {
      onOptimisticAdd(trimmedName, createPromise);
    }
  };

  const handleClose = () => {
    setPackageName('');
    setError(null);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader onClose={handleClose}>
          <DialogTitle>Add Package</DialogTitle>
        </DialogHeader>
        <DialogBody>
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
                className="w-full border border-neutral-800 bg-neutral-950 px-3 py-3 text-sm text-neutral-100 placeholder:text-neutral-400 focus:border-neutral-700 focus:outline-none focus:ring-3 focus:ring-neutral-700/24"
                autoFocus
              />
              <p className="mt-2 text-xs text-neutral-400">
                Enter npm package name. We'll fetch the latest version automatically.
              </p>
            </div>

            {/* Error Message */}
            {error && (
              <div className="border border-red-900/50 bg-red-900/10 px-3 py-2 text-sm text-red-400">
                {error}
              </div>
            )}

            {/* Submit Button */}
            <div className="flex justify-end gap-3">
              <Button
                type="button"
                variant="secondary"
                onClick={handleClose}
              >
                Cancel
              </Button>
              <Button type="submit">
                Add Package
              </Button>
            </div>
          </form>
        </DialogBody>
      </DialogContent>
    </Dialog>
  );
}
