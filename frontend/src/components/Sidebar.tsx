/**
 * Sidebar navigation component.
 */

import { Plus, Package, PanelLeftClose, PanelLeftOpen, AlertTriangle } from 'lucide-react';
import { useLocation, Link } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { alertsApi } from '@/lib/api';

interface SidebarProps {
  onNewPackage: () => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export function Sidebar({ onNewPackage, isCollapsed, onToggleCollapse }: SidebarProps) {
  const location = useLocation();
  const isPackagesActive = location.pathname === '/';
  const isAlertsActive = location.pathname === '/alerts';
  const [openAlertsCount, setOpenAlertsCount] = useState<number>(0);

  useEffect(() => {
    const fetchAlertStats = async () => {
      try {
        const stats = await alertsApi.getStats();
        setOpenAlertsCount(stats.open_alerts);
      } catch (err) {
        console.error('Failed to fetch alert stats:', err);
      }
    };

    fetchAlertStats();
    // Refresh alert count every 30 seconds
    const interval = setInterval(fetchAlertStats, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <aside className='flex h-screen w-full flex-col select-none overflow-x-hidden border-r border-neutral-800 bg-neutral-950'>
      <div className='flex flex-col h-full overflow-x-hidden'>
        {/* Logo */}
        <div
          className='flex shrink-0 items-center gap-2 border-b border-neutral-800 overflow-x-hidden'
          style={{ height: '39.5px' }}
        >
          <div className={cn(
            'flex items-center gap-2 min-w-0 w-full h-full transition-all duration-300',
            isCollapsed ? 'px-2 justify-center' : 'px-4'
          )}>
            <img
              src='/images/intrace-logo-white-icononly.svg'
              alt='Intrace'
              className='h-5 w-5 flex-shrink-0'
            />
            {!isCollapsed && (
              <span className='text-sm font-medium text-neutral-100 truncate flex-1'>
                Intrace Sentinel
              </span>
            )}
            <button
              onClick={onToggleCollapse}
              className='flex-shrink-0 text-neutral-400 hover:text-neutral-100 transition-colors'
              aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {isCollapsed ? (
                <PanelLeftOpen className='h-4 w-4' strokeWidth={1.5} />
              ) : (
                <PanelLeftClose className='h-4 w-4' strokeWidth={1.5} />
              )}
            </button>
          </div>
        </div>

        {/* Navigation */}
        <div className={cn(
          'min-w-0 overflow-x-hidden transition-all duration-300',
          isCollapsed ? 'p-2' : 'p-4'
        )}>
          {!isCollapsed && (
            <h2 className='mb-2 px-2 text-xs font-semibold text-neutral-400 truncate'>
              Navigation
            </h2>
          )}

          <ul className={cn(
            'flex flex-col gap-1 min-w-0 overflow-x-hidden',
            isCollapsed && 'mt-2'
          )}>
            {/* New Package Button - Quick Action Style */}
            <li className='min-w-0'>
              <button
                onClick={onNewPackage}
                className={cn(
                  'flex h-6 w-full items-center rounded-none text-neutral-300 hover:text-neutral-200 hover:bg-neutral-800 transition-colors duration-200 ease-in-out',
                  isCollapsed ? 'justify-center px-1' : 'gap-1 px-1.5 py-1'
                )}
                title={isCollapsed ? 'New Package' : undefined}
              >
                <Plus className='size-2.5 flex-shrink-0' strokeWidth={2} />
                {!isCollapsed && <span className='truncate min-w-0 text-sm'>New Package</span>}
              </button>
            </li>

            {/* Packages Link - Regular NavItem Style */}
            <li className='min-w-0'>
              <Link
                to="/"
                className={cn(
                  'group flex h-9 w-full items-center rounded-none text-sm font-medium focus:outline-none focus-visible:outline-current min-w-0 transition-colors duration-200 ease-in-out',
                  isCollapsed ? 'justify-center p-2' : 'gap-2.5 p-2',
                  isPackagesActive
                    ? 'border border-neutral-800 bg-neutral-950 text-neutral-100'
                    : 'text-neutral-400 hover:bg-neutral-800 hover:text-neutral-300'
                )}
                title={isCollapsed ? 'Packages' : undefined}
              >
                <span className='flex-shrink-0'>
                  <Package className='h-4 w-4' strokeWidth={1.5} />
                </span>
                {!isCollapsed && <span className='truncate min-w-0'>Packages</span>}
              </Link>
            </li>

            {/* Alerts Link with Badge */}
            <li className='min-w-0'>
              <Link
                to="/alerts"
                className={cn(
                  'group flex h-9 w-full items-center rounded-none text-sm font-medium focus:outline-none focus-visible:outline-current min-w-0 transition-colors duration-200 ease-in-out',
                  isCollapsed ? 'justify-center p-2' : 'gap-2.5 p-2',
                  isAlertsActive
                    ? 'border border-neutral-800 bg-neutral-950 text-neutral-100'
                    : 'text-neutral-400 hover:bg-neutral-800 hover:text-neutral-300'
                )}
                title={isCollapsed ? 'Alerts' : undefined}
              >
                <span className='flex-shrink-0'>
                  <AlertTriangle className='h-4 w-4' strokeWidth={1.5} />
                </span>
                {!isCollapsed && (
                  <>
                    <span className='truncate min-w-0'>Alerts</span>
                    {openAlertsCount > 0 && (
                      <span className='ml-auto flex-shrink-0 flex items-center justify-center min-w-[20px] h-5 px-1.5 bg-red-900/50 border border-red-900 text-red-400 text-xs font-medium rounded'>
                        {openAlertsCount}
                      </span>
                    )}
                  </>
                )}
              </Link>
            </li>
          </ul>
        </div>
      </div>
    </aside>
  );
}
