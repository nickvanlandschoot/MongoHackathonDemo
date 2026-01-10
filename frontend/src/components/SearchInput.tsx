/**
 * Search input with icon.
 */

import { Search } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export function SearchInput({
  value,
  onChange,
  placeholder = 'Search...',
  className,
}: SearchInputProps) {
  return (
    <div className={cn('relative', className)}>
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-neutral-800 bg-neutral-950/50 py-2.5 pl-10 pr-3 text-sm text-neutral-100 placeholder:text-neutral-400 focus:border-neutral-700 focus:outline-none focus:ring-3 focus:ring-neutral-700/24"
      />
    </div>
  );
}
