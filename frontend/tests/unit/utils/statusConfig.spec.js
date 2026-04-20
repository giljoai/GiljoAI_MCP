import { describe, it, expect } from 'vitest';
import {
  getStatusConfig,
  getHealthConfig,
  isJobStale,
  formatLastActivity,
  isCloseoutBlocked,
  getStatusLabel,
  getStatusColor
} from '@/utils/statusConfig';

describe('statusConfig.js', () => {
  describe('getStatusConfig', () => {
    it('returns correct config for each status', () => {
      expect(getStatusConfig('waiting').icon).toBe('mdi-clock-outline');
      expect(getStatusConfig('working').icon).toBe('mdi-cog');
      expect(getStatusConfig('blocked').icon).toBe('mdi-account-question');
      expect(getStatusConfig('complete').icon).toBe('mdi-check-circle');
      expect(getStatusConfig('silent').icon).toBe('mdi-clock-alert');
      expect(getStatusConfig('handed_over').icon).toBe('mdi-hand-wave');
      expect(getStatusConfig('decommissioned').icon).toBe('mdi-archive');
    });

    it('returns default config for unknown status', () => {
      expect(getStatusConfig('invalid').icon).toBe('mdi-clock-outline');
    });

    it('returns closeout-blocked config when status is blocked with Closeout reason', () => {
      const config = getStatusConfig('blocked', 'Closeout: awaiting user review');
      expect(config.label).toBe('Decision Required');
      expect(config.icon).toBe('mdi-clipboard-check-outline');
    });

    it('returns generic blocked config when block_reason does not start with Closeout', () => {
      const config = getStatusConfig('blocked', 'Waiting for upstream agent');
      expect(config.label).toBe('Needs Input');
      expect(config.icon).toBe('mdi-account-question');
    });
  });

  describe('isCloseoutBlocked', () => {
    it('returns true when status is blocked and reason starts with Closeout', () => {
      expect(isCloseoutBlocked('blocked', 'Closeout: awaiting user review')).toBe(true);
      expect(isCloseoutBlocked('blocked', 'Closeout: deferred findings')).toBe(true);
    });

    it('returns false when status is not blocked', () => {
      expect(isCloseoutBlocked('working', 'Closeout: something')).toBe(false);
      expect(isCloseoutBlocked('complete', 'Closeout: done')).toBe(false);
    });

    it('returns false when block_reason does not start with Closeout', () => {
      expect(isCloseoutBlocked('blocked', 'Waiting for input')).toBe(false);
      expect(isCloseoutBlocked('blocked', 'BLOCKED: unclear requirements')).toBe(false);
    });

    it('returns false when block_reason is null or undefined', () => {
      expect(isCloseoutBlocked('blocked', null)).toBe(false);
      expect(isCloseoutBlocked('blocked', undefined)).toBe(false);
      expect(isCloseoutBlocked('blocked')).toBe(false);
    });
  });

  describe('getStatusLabel with closeout', () => {
    it('returns Decision Required for closeout-blocked agent', () => {
      expect(getStatusLabel('blocked', 'Closeout: awaiting user review')).toBe('Decision Required');
    });

    it('returns Needs Input for generic blocked agent', () => {
      expect(getStatusLabel('blocked', null)).toBe('Needs Input');
      expect(getStatusLabel('blocked')).toBe('Needs Input');
    });

    it('returns normal label when status is not blocked', () => {
      expect(getStatusLabel('working', 'Closeout: something')).toBe('Working');
    });
  });

  describe('getStatusColor with closeout', () => {
    it('returns amber for closeout-blocked agent', () => {
      expect(getStatusColor('blocked', 'Closeout: awaiting user review')).toBe('#ffc107');
    });

    it('returns orange for generic blocked agent', () => {
      expect(getStatusColor('blocked', null)).toBe('#ff9800');
      expect(getStatusColor('blocked')).toBe('#ff9800');
    });
  });

  describe('getHealthConfig', () => {
    it('returns correct config for each health state', () => {
      expect(getHealthConfig('healthy').showIndicator).toBe(false);
      expect(getHealthConfig('warning').showIndicator).toBe(true);
      expect(getHealthConfig('critical').pulse).toBe(true);
      expect(getHealthConfig('timeout').icon).toBe('mdi-timer-alert');
    });
  });

  describe('isJobStale', () => {
    it('returns true for jobs inactive >10 minutes', () => {
      const elevenMinutesAgo = new Date(Date.now() - 11 * 60 * 1000).toISOString();
      expect(isJobStale(elevenMinutesAgo, 'working')).toBe(true);
    });

    it('returns false for terminal states', () => {
      const elevenMinutesAgo = new Date(Date.now() - 11 * 60 * 1000).toISOString();
      // Terminal states: complete, silent, decommissioned, handed_over
      expect(isJobStale(elevenMinutesAgo, 'complete')).toBe(false);
      expect(isJobStale(elevenMinutesAgo, 'silent')).toBe(false);
      expect(isJobStale(elevenMinutesAgo, 'decommissioned')).toBe(false);
      expect(isJobStale(elevenMinutesAgo, 'handed_over')).toBe(false);
    });

    it('returns false for null lastProgressAt', () => {
      expect(isJobStale(null, 'working')).toBe(false);
    });
  });

  describe('formatLastActivity', () => {
    it('formats relative time correctly', () => {
      expect(formatLastActivity(null)).toBe('Never');

      const now = new Date();
      expect(formatLastActivity(now.toISOString())).toBe('Just now');

      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
      expect(formatLastActivity(fiveMinutesAgo)).toBe('5 minutes ago');

      const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
      expect(formatLastActivity(twoHoursAgo)).toBe('2 hours ago');
    });
  });
});
