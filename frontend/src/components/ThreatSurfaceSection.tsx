/**
 * Comprehensive threat surface assessment display.
 */

import { useState, useEffect } from 'react';
import { Loader2, ChevronDown, ChevronUp, Shield, AlertTriangle } from 'lucide-react';
import { threatSurfaceApi } from '@/lib/api';
import type { ThreatAssessment, CurrentAssessmentResponse } from '@/lib/api';
import { RiskLevelBadge } from './RiskLevelBadge';
import { MaintainerTrustBadge } from './MaintainerTrustBadge';
import { AssessmentHistoryTimeline } from './AssessmentHistoryTimeline';
import { useJobPolling } from '@/hooks/useJobPolling';

interface ThreatSurfaceSectionProps {
  packageName: string;
}

export function ThreatSurfaceSection({ packageName }: ThreatSurfaceSectionProps) {
  const [assessment, setAssessment] = useState<ThreatAssessment | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [historyExpanded, setHistoryExpanded] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);

  // Poll job status when generating assessment
  const { isPolling } = useJobPolling({
    jobId,
    onComplete: async () => {
      // Job completed, refetch the threat assessment
      try {
        const data: CurrentAssessmentResponse = await threatSurfaceApi.getCurrent(packageName);
        if (data.assessment) {
          setAssessment(data.assessment);
        }
      } catch (err) {
        console.error('Failed to fetch assessment after job completion:', err);
      } finally {
        setJobId(null);
        setLoading(false);
      }
    },
    onError: (err) => {
      setError(err);
      setJobId(null);
      setLoading(false);
    },
  });

  // Fetch assessment - only fetch existing data, never auto-trigger generation
  useEffect(() => {
    const fetchAssessment = async () => {
      // Skip if already polling a job
      if (jobId) return;

      setLoading(true);
      setError(null);

      try {
        // Try to get existing assessment
        const data: CurrentAssessmentResponse = await threatSurfaceApi.getCurrent(packageName);

        if (data.status === 'available' && data.assessment) {
          // Assessment exists, use it
          setAssessment(data.assessment);
        }
        // For 'not_generated' or 'generating' status, just show appropriate UI
        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch threat assessment');
        setLoading(false);
      }
    };

    fetchAssessment();
  }, [packageName, jobId]);

  // Loading or polling state
  if (loading || isPolling) {
    return (
      <div className="border border-neutral-800 bg-neutral-900/50 p-8 text-center">
        <Loader2 className="mx-auto h-8 w-8 animate-spin text-neutral-400" />
        <p className="mt-2 text-sm text-neutral-400">
          {isPolling ? 'Generating threat assessment...' : 'Loading threat assessment...'}
        </p>
        {isPolling && (
          <p className="mt-1 text-xs text-neutral-500">
            This can take a while.
          </p>
        )}
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="border border-red-900/50 bg-red-900/10 p-4 text-sm text-red-400">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4" />
          <strong>Error:</strong> {error}
        </div>
      </div>
    );
  }

  // No data - show pending message
  if (!assessment) {
    return (
      <div className="border border-neutral-800 bg-neutral-900/50 p-8 text-center">
        <Shield className="mx-auto h-12 w-12 text-neutral-600 mb-4" />
        <p className="text-sm text-neutral-400 mb-2">Threat assessment is being generated.</p>
        <p className="text-xs text-neutral-500">
          This happens automatically when a package is added. Check back shortly.
        </p>
      </div>
    );
  }

  const maintainerLevel = (assessment.maintainer_assessment.overall || 'moderate') as 'trustworthy' | 'moderate' | 'concerning';

  return (
    <div className="space-y-6">
      {/* Header with Risk Level */}
      <div className="border border-neutral-800 bg-neutral-900/50 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="h-5 w-5 text-neutral-400" />
            <h3 className="text-sm font-medium text-neutral-100">
              Threat Surface Assessment
            </h3>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-xs text-neutral-500">
              v{assessment.version}
            </div>
            <RiskLevelBadge
              level={assessment.overall_risk_level}
              confidence={assessment.confidence}
            />
          </div>
        </div>
      </div>

      {/* Comprehensive Assessment Narrative */}
      <div className="border border-neutral-800 bg-neutral-900/50 p-6">
        <h4 className="text-xs font-medium text-neutral-400 mb-3">Assessment</h4>
        <p className="text-sm text-neutral-300 whitespace-pre-wrap leading-relaxed">
          {assessment.assessment_narrative}
        </p>
      </div>

      {/* Evolution Narrative */}
      {assessment.evolution_narrative && (
        <div className="border border-blue-900/50 bg-blue-900/10 p-6">
          <h4 className="text-xs font-medium text-blue-400 mb-3">Evolution Since Last Assessment</h4>
          <p className="text-sm text-neutral-300 whitespace-pre-wrap leading-relaxed">
            {assessment.evolution_narrative}
          </p>
        </div>
      )}

      {/* Key Strengths vs Key Risks Grid */}
      <div className="grid grid-cols-2 gap-4">
        {/* Key Strengths */}
        <div className="border border-neutral-800 bg-neutral-900/50 p-4">
          <h4 className="text-xs font-medium text-green-400 mb-3">Key Strengths</h4>
          {assessment.key_strengths.length > 0 ? (
            <ul className="space-y-2">
              {assessment.key_strengths.map((strength, idx) => (
                <li key={idx} className="text-sm text-neutral-300 flex gap-2">
                  <span className="text-green-400 mt-0.5">•</span>
                  <span>{strength}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-neutral-500">None identified</p>
          )}
        </div>

        {/* Key Risks */}
        <div className="border border-neutral-800 bg-neutral-900/50 p-4">
          <h4 className="text-xs font-medium text-red-400 mb-3">Key Risks</h4>
          {assessment.key_risks.length > 0 ? (
            <ul className="space-y-2">
              {assessment.key_risks.map((risk, idx) => (
                <li key={idx} className="text-sm text-neutral-300 flex gap-2">
                  <span className="text-red-400 mt-0.5">•</span>
                  <span>{risk}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-neutral-500">None identified</p>
          )}
        </div>
      </div>

      {/* Notable Dependencies */}
      {assessment.notable_dependencies.length > 0 && (
        <div className="border border-neutral-800 bg-neutral-900/50 p-4">
          <h4 className="text-xs font-medium text-neutral-400 mb-3">Notable Dependencies</h4>
          <div className="space-y-3">
            {assessment.notable_dependencies.map((dep, idx) => (
              <div key={idx} className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="text-sm font-medium text-neutral-200">{dep.name}</div>
                  <div className="text-xs text-neutral-400 mt-1">{dep.reason}</div>
                </div>
                <RiskLevelBadge
                  level={dep.risk as 'low' | 'medium' | 'high' | 'critical'}
                  confidence={1.0}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Maintainer Assessment */}
      {assessment.maintainer_assessment.overall && (
        <div className="border border-neutral-800 bg-neutral-900/50 p-4">
          <h4 className="text-xs font-medium text-neutral-400 mb-3">Maintainer Assessment</h4>
          <div className="flex items-start gap-3">
            <MaintainerTrustBadge level={maintainerLevel} />
            {assessment.maintainer_assessment.details && (
              <p className="text-sm text-neutral-300 flex-1">
                {assessment.maintainer_assessment.details}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Metadata */}
      <div className="border border-neutral-800 bg-neutral-900/50 p-4">
        <div className="flex items-center justify-between text-xs text-neutral-500">
          <span>Dependency depth analyzed: {assessment.dependency_depth_analyzed} levels</span>
          <span>Generated: {new Date(assessment.timestamp).toLocaleString()}</span>
        </div>
      </div>

      {/* Expandable History Timeline */}
      <div className="border border-neutral-800 bg-neutral-900/50">
        <button
          onClick={() => setHistoryExpanded(!historyExpanded)}
          className="w-full flex items-center justify-between p-4 text-left transition-colors hover:bg-neutral-800/30"
        >
          <h4 className="text-sm font-medium text-neutral-300">Assessment History</h4>
          {historyExpanded ? (
            <ChevronUp className="h-4 w-4 text-neutral-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-neutral-400" />
          )}
        </button>

        {historyExpanded && (
          <div className="border-t border-neutral-800 p-4">
            <AssessmentHistoryTimeline packageName={packageName} />
          </div>
        )}
      </div>
    </div>
  );
}
