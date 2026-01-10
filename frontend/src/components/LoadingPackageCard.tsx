/**
 * Loading/skeleton package card for optimistic UI updates.
 * Shows progressive loading states for individual data pieces.
 */

import { Package as PackageIcon } from 'lucide-react';
import { RiskBadge } from '@/components/RiskBadge';
import { cn } from '@/lib/utils';

interface LoadingPackageCardProps {
  packageName: string;
  onClick?: () => void;
  className?: string;
  loadedData?: Partial<{
    owner: string;
    latest_release_date: string;
    latest_release_version: string;
    risk_score: number;
  }>;
}

function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'animate-pulse rounded bg-neutral-800/50',
        className
      )}
    />
  );
}

export function LoadingPackageCard({
  packageName,
  onClick,
  className,
  loadedData = {}
}: LoadingPackageCardProps) {
  const lastRelease = loadedData.latest_release_date
    ? new Date(loadedData.latest_release_date).toLocaleString()
    : null;

  return (
    <div
      className={cn(
        'cursor-pointer border border-neutral-800 bg-neutral-900/30 transition-colors hover:border-neutral-700',
        className
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between border-b border-neutral-800 px-4 py-3">
        <div className="flex items-center gap-2">
          <PackageIcon className="h-4 w-4 text-neutral-400" />
          <h3 className="text-sm font-medium text-neutral-100">{packageName}</h3>
        </div>
        {loadedData.risk_score !== undefined ? (
          <RiskBadge score={loadedData.risk_score} />
        ) : (
          <Skeleton className="h-5 w-16" />
        )}
      </div>
      <div className="px-4 py-3">
        <div className="space-y-1.5 text-xs text-neutral-400">
          <div>
            <span className="text-neutral-500">Owner:</span>{' '}
            {loadedData.owner ? (
              loadedData.owner
            ) : (
              <Skeleton className="inline-block h-3 w-20 align-middle" />
            )}
          </div>
          <div>
            <span className="text-neutral-500">Last release:</span>{' '}
            {lastRelease ? (
              <>
                {lastRelease}
                {loadedData.latest_release_version && (
                  <span className="ml-1">(v{loadedData.latest_release_version})</span>
                )}
              </>
            ) : (
              <Skeleton className="inline-block h-3 w-24 align-middle" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
