import { useEffect, useState, useCallback, useRef } from 'react';
import { depsApi } from '../lib/api';

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed';

interface UseJobPollingOptions {
  jobId: string | null;
  onComplete?: () => void;
  onError?: (error: string) => void;
  pollInterval?: number;
}

/**
 * Hook for polling job status until completion or failure.
 *
 * @param options.jobId - Job ID to poll (null to skip polling)
 * @param options.onComplete - Callback when job completes successfully
 * @param options.onError - Callback when job fails
 * @param options.pollInterval - Polling interval in ms (default: 2000)
 */
export function useJobPolling({
  jobId,
  onComplete,
  onError,
  pollInterval = 2000,
}: UseJobPollingOptions) {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Use refs to store callbacks to avoid dependency changes
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);

  // Update refs when callbacks change
  useEffect(() => {
    onCompleteRef.current = onComplete;
    onErrorRef.current = onError;
  }, [onComplete, onError]);

  const pollJobStatus = useCallback(async () => {
    if (!jobId) return;

    try {
      const result = await depsApi.getJobStatus(jobId);
      setStatus(result.status);

      if (result.status === 'completed') {
        setIsPolling(false);
        onCompleteRef.current?.();
      } else if (result.status === 'failed') {
        setIsPolling(false);
        const errorMsg = result.error || 'Job failed';
        setError(errorMsg);
        onErrorRef.current?.(errorMsg);
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to poll job status';
      setError(errorMsg);
      setIsPolling(false);
      onErrorRef.current?.(errorMsg);
    }
  }, [jobId]);

  useEffect(() => {
    if (!jobId) {
      setIsPolling(false);
      return;
    }

    setIsPolling(true);
    setError(null);
    setStatus('pending');

    // Start polling
    const intervalId = setInterval(pollJobStatus, pollInterval);

    // Poll immediately
    pollJobStatus();

    return () => {
      clearInterval(intervalId);
    };
  }, [jobId, pollInterval, pollJobStatus]);

  return {
    status,
    isPolling,
    error,
  };
}
