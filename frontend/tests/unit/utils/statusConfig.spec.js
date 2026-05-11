import { describe, it, expect } from 'vitest';
import {
  getStatusConfig,
  getHealthConfig,
  isJobStale,
  formatLastActivity,
  isAwaitingUser,
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

    it('returns awaiting_user config when status is awaiting_user', () => {
      const config = getStatusConfig('awaiting_user');
      expect(config.label).toBe('Decision Required');
      expect(config.icon).toBe('mdi-clipboard-check-outline');
    });

    it('returns generic blocked config for blocked status (no longer special-cases Closeout reason)', () => {
      const config = getStatusConfig('blocked');
      expect(config.label).toBe('Needs Input');
      expect(config.icon).toBe('mdi-account-question');
    });
  });

  describe('isAwaitingUser', () => {
    it('returns true only when status is awaiting_user', () => {
      expect(isAwaitingUser('awaiting_user')).toBe(true);
    });

    it('returns false for any other status', () => {
      expect(isAwaitingUser('working')).toBe(false);
      expect(isAwaitingUser('blocked')).toBe(false);
      expect(isAwaitingUser('complete')).toBe(false);
      expect(isAwaitingUser(null)).toBe(false);
      expect(isAwaitingUser(undefined)).toBe(false);
    });
  });

  describe('getStatusLabel with awaiting_user', () => {
    it('returns Decision Required for awaiting_user', () => {
      expect(getStatusLabel('awaiting_user')).toBe('Decision Required');
    });

    it('returns Needs Input for plain blocked agent', () => {
      expect(getStatusLabel('blocked')).toBe('Needs Input');
    });

    it('returns normal label for other statuses', () => {
      expect(getStatusLabel('working')).toBe('Working');
    });
  });

  describe('getStatusColor with awaiting_user', () => {
    it('returns amber for awaiting_user', () => {
      expect(getStatusColor('awaiting_user')).toBe('#ffc107');
    });

    it('returns orange for blocked', () => {
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
