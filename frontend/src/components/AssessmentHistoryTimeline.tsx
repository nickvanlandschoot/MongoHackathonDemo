/**
 * Timeline display of threat assessment history.
 */

import { useState, useEffect } from 'react';
import { Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { threatSurfaceApi } from '@/lib/api';
import type { ThreatAssessment } from '@/lib/api';
import { RiskLevelBadge } from './RiskLevelBadge';

interface AssessmentHistoryTimelineProps {
  packageName: string;
}

export function AssessmentHistoryTimeline({ packageName }: AssessmentHistoryTimelineProps) {
  const [assessments, setAssessments] = useState<ThreatAssessment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true);
      setError(null);

      try {
        const data = await threatSurfaceApi.getHistory(packageName, 20);
        setAssessments(data.assessments);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch assessment history');
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [packageName]);

  if (loading) {
    return (
      <div className="border border-neutral-800 bg-neutral-900/50 p-8 text-center">
        <Loader2 className="mx-auto h-6 w-6 animate-spin text-neutral-400" />
        <p className="mt-2 text-sm text-neutral-400">Loading assessment history...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="border border-red-900/50 bg-red-900/10 p-4 text-sm text-red-400">
        <strong>Error:</strong> {error}
      </div>
    );
  }

  if (assessments.length === 0) {
    return (
      <div className="border border-neutral-800 bg-neutral-900/50 p-8 text-center">
        <p className="text-sm text-neutral-400">No assessment history available.</p>
      </div>
    );
  }

  const toggleExpanded = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="space-y-0">
      {assessments.map((assessment, index) => {
        const isExpanded = expandedId === assessment.id;
        const isLast = index === assessments.length - 1;

        return (
          <div key={assessment.id} className="relative">
            {!isLast && (
              <div className="absolute left-[15px] top-8 bottom-0 w-[2px] bg-neutral-800" />
            )}

            <div className="relative flex gap-4">
              <div className="relative z-10 mt-2">
                <div className="h-8 w-8 border-2 border-neutral-800 bg-neutral-900 flex items-center justify-center">
                  <div className="h-2 w-2 bg-neutral-600" />
                </div>
              </div>

              <div className="flex-1 pb-6">
                <button
                  onClick={() => toggleExpanded(assessment.id)}
                  className="w-full border border-neutral-800 bg-neutral-900/30 p-4 text-left transition-colors hover:border-neutral-700"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium text-neutral-100">
                          v{assessment.version}
                        </span>
                        <RiskLevelBadge
                          level={assessment.overall_risk_level}
                          confidence={assessment.confidence}
                        />
                      </div>
                      <div className="mt-1 text-xs text-neutral-500">
                        {new Date(assessment.timestamp).toLocaleString()}
                      </div>
                    </div>
                    {isExpanded ? (
                      <ChevronUp className="h-4 w-4 text-neutral-400" />
                    ) : (
                      <ChevronDown className="h-4 w-4 text-neutral-400" />
                    )}
                  </div>
                </button>

                {isExpanded && (
                  <div className="mt-2 border border-neutral-800 bg-neutral-900/50 p-4">
                    <div className="space-y-4">
                      {assessment.evolution_narrative && (
                        <div>
                          <h4 className="text-xs font-medium text-neutral-400 mb-2">Evolution</h4>
                          <p className="text-sm text-neutral-300 whitespace-pre-wrap">
                            {assessment.evolution_narrative}
                          </p>
                        </div>
                      )}

                      <div>
                        <h4 className="text-xs font-medium text-neutral-400 mb-2">Assessment</h4>
                        <p className="text-sm text-neutral-300 whitespace-pre-wrap">
                          {assessment.assessment_narrative}
                        </p>
                      </div>

                      {assessment.key_strengths.length > 0 && (
                        <div>
                          <h4 className="text-xs font-medium text-neutral-400 mb-2">Key Strengths</h4>
                          <ul className="space-y-1.5">
                            {assessment.key_strengths.map((strength, idx) => (
                              <li key={idx} className="text-sm text-green-400">
                                • {strength}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {assessment.key_risks.length > 0 && (
                        <div>
                          <h4 className="text-xs font-medium text-neutral-400 mb-2">Key Risks</h4>
                          <ul className="space-y-1.5">
                            {assessment.key_risks.map((risk, idx) => (
                              <li key={idx} className="text-sm text-red-400">
                                • {risk}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
