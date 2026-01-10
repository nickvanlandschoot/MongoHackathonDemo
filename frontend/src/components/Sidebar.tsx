/**
 * Sidebar navigation component.
 */

import { Plus, Package } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';

interface SidebarProps {
  onNewPackage: () => void;
}

export function Sidebar({ onNewPackage }: SidebarProps) {
  const location = useLocation();
  const isPackagesActive = location.pathname === '/';

  return (
    <aside className='flex h-screen w-full flex-col select-none overflow-x-hidden border-r border-neutral-800 bg-neutral-950'>
      <div className='flex flex-col h-full overflow-x-hidden'>
        {/* Logo */}
        <div
          className='flex shrink-0 items-center gap-2 px-4 border-b border-neutral-800 overflow-x-hidden'
          style={{ height: '39.5px' }}
        >
          <div className='flex items-center gap-2 min-w-0 w-full h-full'>
            <img
              src='/images/intrace-logo-white-icononly.svg'
              alt='Intrace'
              className='h-5 w-5 flex-shrink-0'
            />
            <span className='text-sm font-medium text-neutral-100 truncate'>
              Intrace Sentinel
            </span>
          </div>
        </div>

        {/* Navigation */}
        <div className='p-4 min-w-0 overflow-x-hidden'>
          <h2 className='mb-2 px-2 text-xs font-semibold text-neutral-400 truncate'>
            Navigation
          </h2>

          <ul className='flex flex-col gap-1 min-w-0 overflow-x-hidden'>
            {/* New Package Button - Quick Action Style */}
            <li className='min-w-0'>
              <button
                onClick={onNewPackage}
                className='flex h-6 w-full items-center gap-1 px-1.5 py-1 rounded-none text-neutral-300 hover:text-neutral-200 hover:bg-neutral-800 transition-colors duration-200 ease-in-out'
              >
                <Plus className='size-2.5 flex-shrink-0' strokeWidth={2} />
                <span className='truncate min-w-0 text-sm'>New Package</span>
              </button>
            </li>

            {/* Packages Link - Regular NavItem Style */}
            <li className='min-w-0'>
              <button
                className={cn(
                  'group flex h-9 w-full items-center gap-2.5 rounded-none p-2 text-sm font-medium focus:outline-none focus-visible:outline-current min-w-0 transition-colors duration-200 ease-in-out',
                  isPackagesActive
                    ? 'border border-neutral-800 bg-neutral-950 text-neutral-100'
                    : 'text-neutral-400 hover:bg-neutral-800 hover:text-neutral-300'
                )}
              >
                <span className='flex-shrink-0'>
                  <Package className='h-4 w-4' strokeWidth={1.5} />
                </span>
                <span className='truncate min-w-0'>Packages</span>
              </button>
            </li>
          </ul>
        </div>
      </div>
    </aside>
  );
}
