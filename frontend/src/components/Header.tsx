/**
 * Application header with logo and search.
 */

import { Search } from 'lucide-react';

interface HeaderProps {
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder?: string;
}

export function Header({ searchValue, onSearchChange, searchPlaceholder = 'Search...' }: HeaderProps) {
  return (
    <header className="border-b border-neutral-800 bg-neutral-950">
      <div className="flex items-center justify-between px-6 py-3">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center bg-red-600 text-xs font-semibold text-white">
              I
            </div>
            <span className="text-sm font-medium text-neutral-100">Intrace</span>
          </div>
        </div>

        {/* Search */}
        {onSearchChange && (
          <div className="relative w-96">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
            <input
              type="text"
              value={searchValue || ''}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder={searchPlaceholder}
              className="w-full border border-neutral-800 bg-neutral-950 py-2 pl-10 pr-3 text-sm text-neutral-100 placeholder:text-neutral-400 focus:border-neutral-700 focus:outline-none"
            />
          </div>
        )}
      </div>
    </header>
  );
}
