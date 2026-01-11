/**
 * Alert list component with API integration for displaying package alerts.
 */

import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertTriangle, ArrowRight, Loader2 } from 'lucide-react';
import { AlertCard } from '@/components/AlertCard';
import { alertsApi, type RiskAlert } from '@/lib/api';

interface AlertListProps {
  packageName: string;
  maxDisplay?: number;
  className?: string;
}

export function AlertList({ packageName, maxDisplay = 5, className }: AlertListProps) {
  const [alerts, setAlerts] = useState<RiskAlert[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const navigate = useNavigate();

  // Fetch alerts from API
  useEffect(() => {
    const fetchAlerts = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const data = await alertsApi.getByPackage(packageName, { limit: maxDisplay });
        setAlerts(data.alerts);
        setTotal(data.total);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setIsLoading(false);
      }
    };

    fetchAlerts();
  }, [packageName, maxDisplay]);

  // Handle status change
  const handleStatusChange = async (alertId: string, newStatus: RiskAlert['status']) => {
    try {
      const updatedAlert = await alertsApi.updateStatus(alertId, newStatus);

      // Update local state
      setAlerts(alerts.map(alert =>
        alert.id === alertId ? updatedAlert : alert
      ));
    } catch (err) {
      console.error('Failed to update alert status:', err);
    }
  };

  // Handle view package
  const handleViewPackage = (pkgName: string) => {
    navigate(`/packages/${encodeURIComponent(pkgName)}`);
  };

  // Loading state
  if (isLoading) {
    return (
      <div className={className}>
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 text-neutral-400 animate-spin" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={className}>
        <div className="border border-red-900/50 bg-red-900/10 px-4 py-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-red-400" />
            <p className="text-sm text-red-300">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  // Empty state
  if (alerts.length === 0) {
    return (
      <div className={className}>
        <div className="border border-neutral-800 bg-neutral-900/30 px-4 py-8">
          <div className="flex flex-col items-center justify-center text-center">
            <AlertTriangle className="h-12 w-12 text-neutral-600 mb-3" />
            <p className="text-sm text-neutral-400">No alerts found for this package</p>
            <p className="text-xs text-neutral-500 mt-1">
              Alerts will appear here when security issues are detected
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Display alerts
  return (
    <div className={className}>
      <div className="space-y-4">
        {alerts.map(alert => (
          <AlertCard
            key={alert.id}
            alert={alert}
            onStatusChange={handleStatusChange}
            onViewPackage={handleViewPackage}
          />
        ))}

        {/* View All Link */}
        {total > maxDisplay && (
          <Link
            to="/dashboard"
            className="block border border-neutral-800 bg-neutral-900/30 px-4 py-3 text-center hover:bg-neutral-900/50 transition-colors"
          >
            <div className="flex items-center justify-center gap-2 text-sm text-neutral-300 hover:text-neutral-100">
              <span>View all {total} alerts</span>
              <ArrowRight className="h-4 w-4" />
            </div>
          </Link>
        )}
      </div>
    </div>
  );
}
