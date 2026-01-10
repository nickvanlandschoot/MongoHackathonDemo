/**
 * Individual dependency card with expand/collapse functionality.
 */

import { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight, Package as PackageIcon, Users } from 'lucide-react';
import { Link } from 'react-router-dom';
import { packagesApi } from '@/lib/api';
import type { DependencyNode, Package } from '@/lib/api';
import type { DependencyType } from '@/lib/dependencyUtils';
import { getTypeColor } from '@/lib/dependencyUtils';
import { RiskBadge } from '@/components/RiskBadge';

interface DependencyCardProps {
  name: string;
  version: string;
  spec: string;
  type: DependencyType;
  childCount: number;
  node: DependencyNode;
  depth: number;
}

export function DependencyCard({
  name,
  version,
  spec,
  type,
  childCount,
  node,
  depth,
}: DependencyCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [pkg, setPkg] = useState<Package | null>(null);

  const hasChildren = childCount > 0;
  const indentLevel = depth - 1; // depth 1 = no indent, depth 2 = 1 indent, etc.

  // Get maintainer info directly from node.children (dependency tree data)
  const maintainers = (node.children as any)?.maintainers || [];
  const maintainerCount = maintainers.length;

  // Optionally fetch package data if it exists (for clickable links and risk scores)
  useEffect(() => {
    const fetchPackageData = async () => {
      try {
        const packageData = await packagesApi.get(name);
        setPkg(packageData);
      } catch (err) {
        // Package might not exist in our database - that's ok for dependencies
        console.debug(`Package ${name} not found in database (showing dependency data only)`);
      }
    };

    fetchPackageData();
  }, [name]);

  const toggleExpand = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (hasChildren) {
      setIsExpanded(!isExpanded);
    }
  };

  const CardContent = (
    <>
      {/* Left border indicator for nested deps */}
      {indentLevel > 0 && (
        <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-neutral-700" />
      )}

      <div className="flex items-center justify-between p-3">
        {/* Left: Icon + Name + Version */}
        <div className="flex items-center gap-3">
          {/* Expand/Collapse Icon or Package Icon */}
          {hasChildren ? (
            <button onClick={toggleExpand} className="flex-shrink-0">
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 text-neutral-400" />
              ) : (
                <ChevronRight className="h-4 w-4 text-neutral-400" />
              )}
            </button>
          ) : (
            <PackageIcon className="h-4 w-4 flex-shrink-0 text-neutral-600" />
          )}

          {/* Type Indicator Dot */}
          <div className={`h-2 w-2 flex-shrink-0 rounded-full ${getTypeColor(type)}`} />

          {/* Name and Version */}
          <div>
            <div className="font-medium text-neutral-100">{name}</div>
            <div className="text-sm text-neutral-400">
              {version} <span className="text-neutral-600">({spec})</span>
            </div>
          </div>
        </div>

        {/* Right: Badges */}
        <div className="flex items-center gap-2">
          {/* Maintainer Count - from dependency tree data */}
          {maintainerCount > 0 && (
            <span
              className="flex items-center gap-1 rounded bg-neutral-800 px-2 py-1 text-xs font-medium text-neutral-300 cursor-help"
              title={`Maintainers: ${maintainers.join(', ')}`}
            >
              <Users className="h-3 w-3" />
              {maintainerCount}
            </span>
          )}

          {/* Risk Badge - only if Package record exists */}
          {pkg && <RiskBadge score={pkg.risk_score} className="text-xs px-2 py-0.5" />}

          {/* Child Count Badge */}
          {childCount > 0 && (
            <span className="rounded bg-neutral-700 px-2 py-1 text-xs font-medium text-neutral-300">
              {childCount} {childCount === 1 ? 'dep' : 'deps'}
            </span>
          )}
        </div>
      </div>
    </>
  );

  return (
    <div className="relative">
      {/* Main Card */}
      {pkg ? (
        <Link
          to={`/packages/${encodeURIComponent(name)}`}
          className="block border border-neutral-800 bg-neutral-900/50 transition-colors hover:bg-neutral-900"
          style={{ marginLeft: `${indentLevel * 16}px` }}
        >
          {CardContent}
        </Link>
      ) : (
        <div
          className="border border-neutral-800 bg-neutral-900/50"
          style={{ marginLeft: `${indentLevel * 16}px` }}
        >
          {CardContent}
        </div>
      )}

      {/* Expanded Children */}
      {isExpanded && hasChildren && (
        <div className="mt-2 space-y-2">
          {/* Production Dependencies */}
          {node.children.dependencies &&
            Object.entries(node.children.dependencies).map(([childName, childNode], index) => (
              <DependencyCard
                key={`${depth}-prod-${childName}-${childNode.resolved_version}-${index}`}
                name={childName}
                version={childNode.resolved_version}
                spec={childNode.spec}
                type="prod"
                childCount={countNodeDeps(childNode)}
                node={childNode}
                depth={depth + 1}
              />
            ))}

          {/* Dev Dependencies */}
          {node.children.devDependencies &&
            Object.entries(node.children.devDependencies).map(([childName, childNode], index) => (
              <DependencyCard
                key={`${depth}-dev-${childName}-${childNode.resolved_version}-${index}`}
                name={childName}
                version={childNode.resolved_version}
                spec={childNode.spec}
                type="dev"
                childCount={countNodeDeps(childNode)}
                node={childNode}
                depth={depth + 1}
              />
            ))}

          {/* Optional Dependencies */}
          {node.children.optionalDependencies &&
            Object.entries(node.children.optionalDependencies).map(([childName, childNode], index) => (
              <DependencyCard
                key={`${depth}-optional-${childName}-${childNode.resolved_version}-${index}`}
                name={childName}
                version={childNode.resolved_version}
                spec={childNode.spec}
                type="optional"
                childCount={countNodeDeps(childNode)}
                node={childNode}
                depth={depth + 1}
              />
            ))}

          {/* Peer Dependencies */}
          {node.children.peerDependencies &&
            Object.entries(node.children.peerDependencies).map(([childName, childNode], index) => (
              <DependencyCard
                key={`${depth}-peer-${childName}-${childNode.resolved_version}-${index}`}
                name={childName}
                version={childNode.resolved_version}
                spec={childNode.spec}
                type="peer"
                childCount={countNodeDeps(childNode)}
                node={childNode}
                depth={depth + 1}
              />
            ))}
        </div>
      )}
    </div>
  );
}

/**
 * Count total dependencies for a node (helper function).
 */
function countNodeDeps(node: DependencyNode): number {
  let count = 0;

  const depTypes = ['dependencies', 'devDependencies', 'optionalDependencies', 'peerDependencies'] as const;

  for (const depType of depTypes) {
    const deps = node.children[depType];
    if (deps) {
      count += Object.keys(deps).length;
    }
  }

  return count;
}
