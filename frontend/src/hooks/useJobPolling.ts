import { useEffect, useState } from 'react'
import { fetchJobStatus } from '@/services/api'
import type { JobStatusResponse } from '@/services/api'

interface UseJobPollingOptions {
  interval?: number // ms between polls (default: 2000)
  onComplete?: (job: JobStatusResponse) => void
  onError?: (error: Error) => void
}

export function useJobPolling(
  jobId: string | null,
  options: UseJobPollingOptions = {}
) {
  const { interval = 2000, onComplete, onError } = options

  const [job, setJob] = useState<JobStatusResponse | null>(null)
  const [isPolling, setIsPolling] = useState(!!jobId)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    if (!jobId) {
      setIsPolling(false)
      return
    }

    let timeoutId: ReturnType<typeof setTimeout> | null = null
    let isMounted = true

    const poll = async () => {
      try {
        const data = await fetchJobStatus(jobId)
        if (!isMounted) return

        setJob(data)
        setError(null)

        // Stop polling when done or failed
        if (data.status === 'completed' || data.status === 'failed') {
          setIsPolling(false)
          onComplete?.(data)
        } else {
          // Schedule next poll
          timeoutId = setTimeout(poll, interval)
        }
      } catch (err) {
        if (!isMounted) return

        const error = err instanceof Error ? err : new Error(String(err))
        setError(error)
        onError?.(error)

        // Retry after interval even on error
        timeoutId = setTimeout(poll, interval)
      }
    }

    // Start polling immediately
    poll()

    return () => {
      isMounted = false
      if (timeoutId) clearTimeout(timeoutId)
    }
  }, [jobId, interval, onComplete, onError])

  return { job, isPolling, error }
}
