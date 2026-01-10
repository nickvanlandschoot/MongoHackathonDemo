/**
 * Context menu component - right-click menu.
 * Follows design system: no rounding, sharp edges, neutral colors.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';

interface ContextMenuProps {
  open: boolean;
  onClose: () => void;
  position: { x: number; y: number };
  children: React.ReactNode;
}

export function ContextMenu({ open, onClose, position, children }: ContextMenuProps) {
  const menuRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!open) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    const handleContextMenu = (event: MouseEvent) => {
      // Close if right-clicking outside the menu
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    // Add listeners with a small delay to avoid immediate close from the triggering event
    const timeoutId = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('contextmenu', handleContextMenu);
      document.addEventListener('keydown', handleEscape);
    }, 100);

    return () => {
      clearTimeout(timeoutId);
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('contextmenu', handleContextMenu);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [open, onClose]);

  React.useEffect(() => {
    if (!open || !menuRef.current) return;

    // Adjust position if menu would go off screen
    const menu = menuRef.current;
    const rect = menu.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    let adjustedX = position.x;
    let adjustedY = position.y;

    if (position.x + rect.width > viewportWidth) {
      adjustedX = viewportWidth - rect.width - 8;
    }
    if (position.y + rect.height > viewportHeight) {
      adjustedY = viewportHeight - rect.height - 8;
    }

    menu.style.left = `${adjustedX}px`;
    menu.style.top = `${adjustedY}px`;
  }, [open, position]);

  if (!open) return null;

  return (
    <div
      ref={menuRef}
      className="fixed z-[9999] min-w-[160px] border border-neutral-800 bg-neutral-900 shadow-lg py-1"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
      }}
      onClick={(e) => e.stopPropagation()}
      onContextMenu={(e) => e.preventDefault()}
      onMouseDown={(e) => e.stopPropagation()}
    >
      {children}
    </div>
  );
}

interface ContextMenuItemProps {
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
  destructive?: boolean;
}

export function ContextMenuItem({
  children,
  onClick,
  className,
  destructive = false,
}: ContextMenuItemProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full px-3 py-2 text-left text-sm transition-colors',
        destructive
          ? 'text-red-400 hover:bg-red-900/20 hover:text-red-300'
          : 'text-neutral-100 hover:bg-neutral-800',
        className
      )}
    >
      {children}
    </button>
  );
}

interface ContextMenuSeparatorProps {
  className?: string;
}

export function ContextMenuSeparator({ className }: ContextMenuSeparatorProps) {
  return <div className={cn('h-px bg-neutral-800', className)} />;
}
