import { describe, it, expect } from 'vitest';
import {
  isAwaitingUser,
  getStatusLabel,
  getStatusColor
} from '@/utils/statusConfig';

describe('statusConfig.js', () => {
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
});
