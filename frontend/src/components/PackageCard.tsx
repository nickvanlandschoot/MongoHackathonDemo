/**
 * Package display card.
 */

import { useState, useRef, useEffect } from 'react';
import { Package as PackageIcon, Trash2 } from 'lucide-react';
import { RiskBadge } from '@/components/RiskBadge';
import { ContextMenu, ContextMenuItem, ContextMenuSeparator } from '@/components/ui/context-menu';
import type { Package } from '@/lib/api';
import { cn } from '@/lib/utils';

interface PackageCardProps {
  package: Package;
  onClick?: () => void;
  onDelete?: (pkg: Package) => void;
  className?: string;
}

export function PackageCard({ package: pkg, onClick, onDelete, className }: PackageCardProps) {
  const [contextMenuOpen, setContextMenuOpen] = useState(false);
  const [contextMenuPosition, setContextMenuPosition] = useState({ x: 0, y: 0 });
  const cardRef = useRef<HTMLDivElement>(null);

  const lastRelease = pkg.latest_release_date
    ? new Date(pkg.latest_release_date).toLocaleString()
    : 'No releases';

  const handleContextMenu = (e: React.MouseEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    const x = e.clientX;
    const y = e.clientY;
    setContextMenuPosition({ x, y });
    setContextMenuOpen(true);
  };

  const handleDelete = () => {
    setContextMenuOpen(false);
    if (onDelete) {
      onDelete(pkg);
    }
  };


  return (
    <>
      <div ref={cardRef} className="relative">
        <div
          className={cn(
            'cursor-pointer border border-neutral-800 bg-neutral-900/30 transition-colors hover:border-neutral-700',
            className
          )}
          onClick={onClick}
          onContextMenu={handleContextMenu}
        >
          <div className="flex items-start justify-between border-b border-neutral-800 px-4 py-3">
            <div className="flex items-center gap-2">
              <PackageIcon className="h-4 w-4 text-neutral-400" />
              <h3 className="text-sm font-medium text-neutral-100">{pkg.name}</h3>
            </div>
            <RiskBadge score={pkg.risk_score} />
          </div>
          <div className="px-4 py-3">
            <div className="space-y-1.5 text-xs text-neutral-400">
              {pkg.owner && (
                <div>
                  <span className="text-neutral-500">Owner:</span> {pkg.owner}
                </div>
              )}
              <div>
                <span className="text-neutral-500">Last release:</span> {lastRelease}
                {pkg.latest_release_version && (
                  <span className="ml-1">(v{pkg.latest_release_version})</span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      <ContextMenu
        open={contextMenuOpen}
        onClose={() => setContextMenuOpen(false)}
        position={contextMenuPosition}
      >
        <ContextMenuItem onClick={handleDelete} destructive>
          <div className="flex items-center gap-2">
            <Trash2 className="h-4 w-4" />
            <span>Delete Package</span>
          </div>
        </ContextMenuItem>
      </ContextMenu>
    </>
  );
}
