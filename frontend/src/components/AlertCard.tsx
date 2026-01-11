/**
 * Alert card displaying risk alert details.
 */

import { Link } from 'react-router-dom';
import { Package as PackageIcon, AlertTriangle, CheckCircle2, Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { RiskAlert } from '@/lib/api';

interface AlertCardProps {
  alert: RiskAlert;
  onStatusChange?: (alertId: string, newStatus: RiskAlert['status']) => void;
  onViewPackage?: (packageName: string) => void;
  className?: string;
}

export function AlertCard({ alert, onStatusChange, onViewPackage, className }: AlertCardProps) {
  // Status badge color
  const statusColorClass =
    alert.status === 'open'
      ? 'bg-red-900/20 text-red-400'
      : alert.status === 'investigated'
        ? 'bg-yellow-900/20 text-yellow-400'
        : 'bg-green-900/20 text-green-400';

  const handleStatusChange = (newStatus: RiskAlert['status']) => {
    if (onStatusChange) {
      onStatusChange(alert.id, newStatus);
    }
  };

  const handleViewPackage = () => {
    if (onViewPackage) {
      onViewPackage(alert.package_name);
    }
  };

  // Calculate severity bar width percentage
  const severityPercent = Math.min(100, Math.max(0, alert.severity));

  return (
    <div className={cn('border border-neutral-800 bg-neutral-900/50', className)}>
      {/* Header with Severity Bar */}
      <div className="px-4 py-3 border-b border-neutral-800">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <AlertTriangle className="h-5 w-5 text-neutral-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <Link
                  to={`/packages/${encodeURIComponent(alert.package_name)}`}
                  className="text-sm font-medium text-neutral-100 hover:text-neutral-50 hover:underline"
                >
                  {alert.package_name}
                </Link>
              </div>
              <p className="text-sm text-neutral-300">{alert.reason}</p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0 ml-4">
            {/* Status Badge */}
            <span
              className={cn(
                'inline-flex items-center px-2 py-1 text-xs font-medium capitalize',
                statusColorClass
              )}
            >
              {alert.status}
            </span>
          </div>
        </div>

        {/* Severity Bar */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-neutral-500">Severity</span>
            <span className="text-neutral-300 font-medium">{alert.severity.toFixed(0)}</span>
          </div>
          <div className="h-1 bg-neutral-800 overflow-hidden">
            <div
              className="h-full bg-red-600/80"
              style={{ width: `${severityPercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* Metadata - Integrated without labels */}
      <div className="px-4 py-2.5 border-b border-neutral-800 flex items-center gap-4 text-xs text-neutral-400">
        <span>{new Date(alert.timestamp).toLocaleString()}</span>
        {alert.release_id && (
          <>
            <span>•</span>
            <span className="font-mono">{alert.release_id.slice(-8)}</span>
          </>
        )}
      </div>

      {/* Analysis Summary - Always Expanded */}
      <div className="px-4 py-3 border-b border-neutral-800">
        <div className="text-xs font-medium text-neutral-400 mb-2">Analysis</div>
        <p className="text-sm text-neutral-300">{alert.analysis.summary}</p>
      </div>

      {/* Evidence - Always Expanded */}
      <div className="px-4 py-3 border-b border-neutral-800">
        <div className="text-xs font-medium text-neutral-400 mb-2">
          Evidence ({alert.analysis.reasons.length})
        </div>
        <ul className="space-y-1.5">
          {alert.analysis.reasons.map((reason, index) => (
            <li key={index} className="text-sm text-neutral-300 flex items-start gap-2">
              <span className="text-neutral-500 flex-shrink-0">•</span>
              <span>{reason}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Action Buttons */}
      <div className="px-4 py-3 flex items-center gap-2 flex-wrap">
        {alert.status === 'open' && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => handleStatusChange('investigated')}
          >
            <Eye className="h-4 w-4" />
            Mark as Investigated
          </Button>
        )}

        {alert.status !== 'resolved' && (
          <Button
            variant="default"
            size="sm"
            onClick={() => handleStatusChange('resolved')}
          >
            <CheckCircle2 className="h-4 w-4" />
            Resolve
          </Button>
        )}

        {alert.status === 'resolved' && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => handleStatusChange('open')}
          >
            Reopen
          </Button>
        )}

        <Button
          variant="ghost"
          size="sm"
          onClick={handleViewPackage}
        >
          <PackageIcon className="h-4 w-4" />
          View Package
        </Button>
      </div>
    </div>
  );
}
