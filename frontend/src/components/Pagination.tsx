/**
 * Pagination controls with page navigation.
 */

import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  const isFirstPage = currentPage === 1;
  const isLastPage = currentPage === totalPages || totalPages === 0;

  return (
    <div className="flex items-center justify-between">
      <div className="text-sm text-neutral-400">
        Page {totalPages === 0 ? 0 : currentPage} of {totalPages}
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={isFirstPage}
        >
          <ChevronLeft className="h-4 w-4" />
          Previous
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={isLastPage}
        >
          Next
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
