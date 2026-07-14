/**
 * FE-9000c: Edit-Mission modal PATCHes an unmounted route (405, never persists).
 *
 * `AgentMissionEditModal.spec.js` mocks `@/services/api` wholesale (see
 * tests/setup.js), so it never exercises the actual URL string inside
 * `api.agentJobs.updateMission` -- that's the layer the bug lived in. This
 * test unmocks the real module and asserts the axios call target directly
 * against the mounted route confirmed live in
 * tests/unit/test_be6042b_app_surface.py (`PATCH /api/jobs/{job_id}/mission`).
 * `/api/agent-jobs/{job_id}/mission` is never mounted for PATCH.
 */
import { describe, it, expect, vi } from 'vitest'

vi.unmock('@/services/api')

describe('api.agentJobs.updateMission (FE-9000c contract)', () => {
  it('PATCHes the mounted /api/jobs/:id/mission route, not /api/agent-jobs/:id/mission', async () => {
    const { api, apiClient } = await import('@/services/api')
    const patchSpy = vi.spyOn(apiClient, 'patch').mockResolvedValue({ data: { success: true } })

    await api.agentJobs.updateMission('job-123', { mission: 'Updated mission' })

    expect(patchSpy).toHaveBeenCalledWith('/api/jobs/job-123/mission', {
      mission: 'Updated mission',
    })
    expect(patchSpy).not.toHaveBeenCalledWith(
      expect.stringContaining('/api/agent-jobs/'),
      expect.anything(),
    )

    patchSpy.mockRestore()
  })
})
