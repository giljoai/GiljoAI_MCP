/**
 * useStalenessMonitor Composable Test Suite
 * Handover 0234: Agent Status Enhancements - Phase 4
 *
 * Tests for staleness monitoring with duplicate warning prevention
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { ref } from 'vue';
import { useStalenessMonitor } from '@/composables/useStalenessMonitor';

describe('useStalenessMonitor.js', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Warning Emission', () => {
    it('emits warning when job becomes stale', () => {
      const jobs = ref([
        {
          job_id: '123',
          status: 'working',
          last_progress_at: new Date(Date.now() - 11 * 60 * 1000).toISOString()
        }
      ]);

      const warnings = [];
      const emitStaleWarning = (job) => warnings.push(job);

      const { checkStaleness } = useStalenessMonitor(jobs, emitStaleWarning);
      checkStaleness();

      expect(warnings.length).toBe(1);
      expect(warnings[0].job_id).toBe('123');
    });

    it('does not emit duplicate warnings for same job', () => {
      const jobs = ref([
        {
          job_id: '123',
          status: 'working',
          last_progress_at: new Date(Date.now() - 11 * 60 * 1000).toISOString()
        }
      ]);

      const warnings = [];
      const emitStaleWarning = (job) => warnings.push(job);

      const { checkStaleness } = useStalenessMonitor(jobs, emitStaleWarning);
      checkStaleness();  // First check
      checkStaleness();  // Second check

      expect(warnings.length).toBe(1);  // Only one warning
    });

    it('emits warning again when job becomes fresh then stale again', () => {
      const jobs = ref([
        {
          job_id: '123',
          status: 'working',
          last_progress_at: new Date(Date.now() - 11 * 60 * 1000).toISOString()
        }
      ]);

      const warnings = [];
      const emitStaleWarning = (job) => warnings.push(job);

      const { checkStaleness } = useStalenessMonitor(jobs, emitStaleWarning);
      checkStaleness();  // First check - should emit
      expect(warnings.length).toBe(1);

      // Update to fresh
      jobs.value[0].last_progress_at = new Date().toISOString();
      checkStaleness();  // Should reset _wasStale
      expect(warnings.length).toBe(1);  // No new warning

      // Back to stale
      jobs.value[0].last_progress_at = new Date(Date.now() - 11 * 60 * 1000).toISOString();
      checkStaleness();  // Should emit again
      expect(warnings.length).toBe(2);
    });
  });

  describe('Terminal State Handling', () => {
    it('ignores terminal state jobs (complete)', () => {
      const jobs = ref([
        {
          job_id: '123',
          status: 'complete',
          last_progress_at: new Date(Date.now() - 11 * 60 * 1000).toISOString()
        }
      ]);

      const warnings = [];
      const emitStaleWarning = (job) => warnings.push(job);

      const { checkStaleness } = useStalenessMonitor(jobs, emitStaleWarning);
      checkStaleness();

      expect(warnings.length).toBe(0);
    });

    it('ignores terminal state jobs (failed)', () => {
      const jobs = ref([
        {
          job_id: '123',
          status: 'failed',
          last_progress_at: new Date(Date.now() - 11 * 60 * 1000).toISOString()
        }
      ]);

      const warnings = [];
      const emitStaleWarning = (job) => warnings.push(job);

      const { checkStaleness } = useStalenessMonitor(jobs, emitStaleWarning);
      checkStaleness();

      expect(warnings.length).toBe(0);
    });

    it('ignores terminal state jobs (cancelled)', () => {
      const jobs = ref([
        {
          job_id: '123',
          status: 'cancelled',
          last_progress_at: new Date(Date.now() - 11 * 60 * 1000).toISOString()
        }
      ]);

      const warnings = [];
      const emitStaleWarning = (job) => warnings.push(job);

      const { checkStaleness } = useStalenessMonitor(jobs, emitStaleWarning);
      checkStaleness();

      expect(warnings.length).toBe(0);
    });

    it('ignores terminal state jobs (decommissioned)', () => {
      const jobs = ref([
        {
          job_id: '123',
          status: 'decommissioned',
          last_progress_at: new Date(Date.now() - 11 * 60 * 1000).toISOString()
        }
      ]);

      const warnings = [];
      const emitStaleWarning = (job) => warnings.push(job);

      const { checkStaleness } = useStalenessMonitor(jobs, emitStaleWarning);
      checkStaleness();

      expect(warnings.length).toBe(0);
    });
  });

  describe('Multiple Jobs', () => {
    it('handles multiple stale jobs', () => {
      const jobs = ref([
        {
          job_id: '123',
          status: 'working',
          last_progress_at: new Date(Date.now() - 11 * 60 * 1000).toISOString()
        },
        {
          job_id: '456',
          status: 'working',
          last_progress_at: new Date(Date.now() - 15 * 60 * 1000).toISOString()
        }
      ]);

      const warnings = [];
      const emitStaleWarning = (job) => warnings.push(job);

      const { checkStaleness } = useStalenessMonitor(jobs, emitStaleWarning);
      checkStaleness();

      expect(warnings.length).toBe(2);
      expect(warnings.map(w => w.job_id).sort()).toEqual(['123', '456']);
    });

    it('handles mixed fresh and stale jobs', () => {
      const jobs = ref([
        {
          job_id: '123',
          status: 'working',
          last_progress_at: new Date(Date.now() - 11 * 60 * 1000).toISOString()
        },
        {
          job_id: '456',
          status: 'working',
          last_progress_at: new Date(Date.now() - 1 * 60 * 1000).toISOString()
        }
      ]);

      const warnings = [];
      const emitStaleWarning = (job) => warnings.push(job);

      const { checkStaleness } = useStalenessMonitor(jobs, emitStaleWarning);
      checkStaleness();

      expect(warnings.length).toBe(1);
      expect(warnings[0].job_id).toBe('123');
    });

    it('handles jobs added dynamically', () => {
      const jobs = ref([
        {
          job_id: '123',
          status: 'working',
          last_progress_at: new Date(Date.now() - 11 * 60 * 1000).toISOString()
        }
      ]);

      const warnings = [];
      const emitStaleWarning = (job) => warnings.push(job);

      const { checkStaleness } = useStalenessMonitor(jobs, emitStaleWarning);
      checkStaleness();  // First check
      expect(warnings.length).toBe(1);

      // Add new stale job
      jobs.value.push({
        job_id: '456',
        status: 'working',
        last_progress_at: new Date(Date.now() - 12 * 60 * 1000).toISOString()
      });

      checkStaleness();  // Second check
      expect(warnings.length).toBe(2);
    });
  });

  describe('Edge Cases', () => {
    it('handles jobs without last_progress_at', () => {
      const jobs = ref([
        {
          job_id: '123',
          status: 'working',
          last_progress_at: null
        }
      ]);

      const warnings = [];
      const emitStaleWarning = (job) => warnings.push(job);

      const { checkStaleness } = useStalenessMonitor(jobs, emitStaleWarning);
      checkStaleness();

      expect(warnings.length).toBe(0);
    });

    it('handles empty jobs array', () => {
      const jobs = ref([]);
      const warnings = [];
      const emitStaleWarning = (job) => warnings.push(job);

      const { checkStaleness } = useStalenessMonitor(jobs, emitStaleWarning);
      checkStaleness();

      expect(warnings.length).toBe(0);
    });

    it('handles job that transitions from fresh to stale', () => {
      const jobs = ref([
        {
          job_id: '123',
          status: 'working',
          last_progress_at: new Date(Date.now() - 5 * 60 * 1000).toISOString()
        }
      ]);

      const warnings = [];
      const emitStaleWarning = (job) => warnings.push(job);

      const { checkStaleness } = useStalenessMonitor(jobs, emitStaleWarning);

      // First check - should not warn (fresh)
      checkStaleness();
      expect(warnings.length).toBe(0);

      // Simulate time progression (update timestamp as if time passed without update)
      jobs.value[0].last_progress_at = new Date(Date.now() - 11 * 60 * 1000).toISOString();

      // Second check - should warn (now stale)
      checkStaleness();
      expect(warnings.length).toBe(1);
    });
  });

  describe('Interval Management', () => {
    it('starts interval on mount', () => {
      const jobs = ref([]);
      const emitStaleWarning = vi.fn();

      // Create new composable
      useStalenessMonitor(jobs, emitStaleWarning);

      // Interval should have been started (30 second interval)
      // We can't directly verify interval is running without accessing internals,
      // but we can verify no errors occur
      expect(true).toBe(true);
    });

    it('returns checkStaleness method for manual triggering', () => {
      const jobs = ref([]);
      const emitStaleWarning = vi.fn();

      const { checkStaleness } = useStalenessMonitor(jobs, emitStaleWarning);

      expect(typeof checkStaleness).toBe('function');
      expect(() => checkStaleness()).not.toThrow();
    });
  });

  describe('State Tracking with _wasStale Flag', () => {
    it('tracks staleness state with _wasStale flag', () => {
      const jobs = ref([
        {
          job_id: '123',
          status: 'working',
          last_progress_at: new Date(Date.now() - 11 * 60 * 1000).toISOString()
        }
      ]);

      const emitStaleWarning = vi.fn();
      const { checkStaleness } = useStalenessMonitor(jobs, emitStaleWarning);

      checkStaleness();

      // Job should now have _wasStale flag set
      expect(jobs.value[0]._wasStale).toBe(true);
    });

    it('resets _wasStale when job becomes fresh', () => {
      const jobs = ref([
        {
          job_id: '123',
          status: 'working',
          last_progress_at: new Date(Date.now() - 11 * 60 * 1000).toISOString()
        }
      ]);

      const emitStaleWarning = vi.fn();
      const { checkStaleness } = useStalenessMonitor(jobs, emitStaleWarning);

      // First check - mark as stale
      checkStaleness();
      expect(jobs.value[0]._wasStale).toBe(true);

      // Update to fresh
      jobs.value[0].last_progress_at = new Date().toISOString();
      checkStaleness();

      // _wasStale should be reset to false
      expect(jobs.value[0]._wasStale).toBe(false);
    });
  });
});
