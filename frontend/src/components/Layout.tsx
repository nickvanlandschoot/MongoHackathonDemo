/**
 * Main layout with sidebar and content area.
 */

import { useState } from 'react';
import { Search } from 'lucide-react';
import { Sidebar } from './Sidebar';
import { AddPackageModal } from './AddPackageModal';

interface LayoutProps {
  children: React.ReactNode;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder?: string;
  onPackageAdded?: () => void;
  onOptimisticAdd?: (packageName: string, promise: Promise<void>) => void;
  pageTitle?: string;
}

export function Layout({
  children,
  searchValue,
  onSearchChange,
  searchPlaceholder = 'Search...',
  onPackageAdded,
  onOptimisticAdd,
  pageTitle = 'PACKAGES',
}: LayoutProps) {
  const [showAddModal, setShowAddModal] = useState(false);

  const handleAddSuccess = () => {
    if (onPackageAdded) {
      onPackageAdded();
    }
  };

  return (
    <div className='flex h-screen bg-neutral-950'>
      {/* Sidebar */}
      <div className='w-64 min-w-0 max-w-64'>
        <Sidebar onNewPackage={() => setShowAddModal(true)} />
      </div>

      {/* Main Content */}
      <div className='flex flex-1 flex-col overflow-hidden'>
        {/* Compact Header */}
        <div className='px-6 pt-4'>
          <div className='relative flex items-center justify-between border-b border-red-700/50'>
            {/* Left: Page Title */}
            <div className='flex h-6 items-center gap-1.5 bg-red-600 px-4'>
              <span className='whitespace-nowrap text-xs font-bold uppercase text-black'>
                {pageTitle}
              </span>
            </div>

            {/* Right: Search */}
            {onSearchChange && (
              <div className='flex h-6 flex-1 items-center justify-end gap-3 bg-red-600/10 px-4'>
                <div className='relative w-64'>
                  <Search className='absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-neutral-400' />
                  <input
                    type='text'
                    value={searchValue || ''}
                    onChange={(e) => onSearchChange(e.target.value)}
                    placeholder={searchPlaceholder}
                    className='h-6 w-full border-0 bg-transparent pl-9 pr-3 text-xs text-neutral-100 placeholder:text-neutral-400 focus:bg-transparent focus:outline-none'
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Content Area */}
        <div className='flex-1 overflow-auto'>{children}</div>
      </div>

      {/* Add Package Modal */}
      <AddPackageModal
        open={showAddModal}
        onOpenChange={setShowAddModal}
        onSuccess={handleAddSuccess}
        onOptimisticAdd={onOptimisticAdd}
      />
    </div>
  );
}
