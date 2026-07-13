/**
 * useSequenceRunner.spec.js — FE-6131e / FE-6165f
 *
 * Covers the selection state, roadmap-default resolution, cap=5 enforcement on
 * run creation, the sequence_runs POST payload (review_policy=per_card, all
 * project_statuses pending), and navigation to the scoped cockpit (staging phase).
 *
 * Edition scope: CE.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'

const { createMock, getMock, updateMock, roadmapGetMock, pushMock } = vi.hoisted(() => ({
  createMock: vi.fn(),
  getMock: vi.fn(),
  updateMock: vi.fn(),
  roadmapGetMock: vi.fn(),
  pushMock: vi.fn(),
}))

vi.mock('@/services/api', () => {
  const apiObj = {
    sequenceRuns: { create: createMock, get: getMock, update: updateMock },
    roadmap: { get: roadmapGetMock },
  }
  return { api: apiObj, default: apiObj }
})

vi.mock('vue-router', () => ({ useRouter: () => ({ push: pushMock }) }))

import { useSequenceRunner } from '@/composables/useSequenceRunner'

beforeEach(() => {
  createMock.mockResolvedValue({ data: { id: 'run-123' } })
  roadmapGetMock.mockResolvedValue({ data: { items: [] } })
})

describe('useSequenceRunner — selection', () => {
  it('toggles selection on/off and tracks count', () => {
    const seq = useSequenceRunner()
    seq.toggle({ id: 'p1', name: 'One' })
    seq.toggle({ id: 'p2', name: 'Two' })
    expect(seq.selectedIds.value).toEqual(['p1', 'p2'])
    expect(seq.selectedCount.value).toBe(2)
    seq.toggle({ id: 'p1' }) // toggle off
    expect(seq.selectedIds.value).toEqual(['p2'])
    seq.clear()
    expect(seq.selectedCount.value).toBe(0)
  })
})

describe('useSequenceRunner — checkbox-stick fix (FE-6165a)', () => {
  it('keys a roadmap row by project_id, NOT the roadmap_item PK', () => {
    // Regression: the bug was that toggle() keyed by `item.id` (the roadmap_item
    // PK) while the checkbox membership test reads `element.project_id` — so the
    // box never rendered ticked. selectedIds MUST hold project_ids.
    const seq = useSequenceRunner()
    seq.toggle({ id: 'rm-item-pk', project_id: 'proj-1', name: 'One' })
    expect(seq.selectedIds.value).toEqual(['proj-1'])
    expect(seq.selectedIds.value).not.toContain('rm-item-pk')
  })

  it('keys a project-list row (no project_id field) by its id', () => {
    // Project rows have no `project_id`; their `id` IS the project_id.
    const seq = useSequenceRunner()
    seq.toggle({ id: 'proj-2', name: 'Two' })
    expect(seq.selectedIds.value).toEqual(['proj-2'])
  })

  it('electionActive flips true only when >= 2 projects are elected (FE-6170 threshold)', () => {
    // FE-6170: threshold raised from >0 to >=2 so 1-elected user keeps the
    // per-row/card single-project play button usable (not dead-ended).
    const seq = useSequenceRunner()
    expect(seq.electionActive.value).toBe(false)
    // 1 elected — electionActive stays false (keeps single play usable)
    seq.toggle({ project_id: 'proj-1', name: 'One' })
    expect(seq.electionActive.value).toBe(false)
    // 2 elected — electionActive becomes true (fades per-row play)
    seq.toggle({ project_id: 'proj-2', name: 'Two' })
    expect(seq.electionActive.value).toBe(true)
    seq.clear()
    expect(seq.electionActive.value).toBe(false)
  })
})

describe('useSequenceRunner — resolveRunOrder', () => {
  it('orders selected projects by roadmap sort_order and flags chains locked', async () => {
    roadmapGetMock.mockResolvedValue({
      data: {
        items: [
          { item_type: 'project', project_id: 'b', sort_order: 0 },
          { item_type: 'project', project_id: 'a', sort_order: 1 },
          { item_type: 'task', task_id: 't1', sort_order: 2 }, // ignored
          { item_type: 'project', project_id: 'free', sort_order: 3 },
        ],
      },
    })
    const seq = useSequenceRunner()
    const resolved = await seq.resolveRunOrder([
      { id: 'a', name: 'A', taxonomy_alias: 'BE-0001a' },
      { id: 'b', name: 'B', taxonomy_alias: 'BE-0001b' },
      { id: 'free', name: 'Free', taxonomy_alias: 'FE-0009' },
    ])
    // roadmap puts b(0) before a(1), but the chain lock re-asserts suffix order a→b.
    expect(resolved.map((r) => r.project_id)).toEqual(['a', 'b', 'free'])
    expect(resolved.find((r) => r.project_id === 'a').locked).toBe(true)
    expect(resolved.find((r) => r.project_id === 'free').locked).toBe(false)
  })
})

describe('useSequenceRunner — startSequence (cap + payload + nav)', () => {
  it('refuses to start with more than 5 projects (cap=5 enforcement)', async () => {
    const seq = useSequenceRunner()
    const six = ['1', '2', '3', '4', '5', '6']
    const run = await seq.startSequence({ projectIds: six, resolvedOrder: six, executionMode: 'multi_terminal' })
    expect(run).toBeNull()
    expect(createMock).not.toHaveBeenCalled()
  })

  it('POSTs a per_card run with all projects pending, then navigates to the scoped cockpit', async () => {
    const seq = useSequenceRunner()
    const order = ['a', 'b', 'c']
    const run = await seq.startSequence({
      projectIds: order,
      resolvedOrder: order,
      executionMode: 'multi_terminal',
    })
    expect(createMock).toHaveBeenCalledTimes(1)
    const body = createMock.mock.calls[0][0]
    expect(body.resolved_order).toEqual(order)
    expect(body.review_policy).toBe('per_card')
    expect(body.status).toBe('pending')
    expect(body.project_statuses).toEqual({ a: 'pending', b: 'pending', c: 'pending' })
    expect(run).toEqual({ id: 'run-123' })
    // FE-6174c: Mission Control retired — navigate to the /jobs multi variant for
    // the chain HEAD project (resolved_order[0]). The create mock omits
    // resolved_order, so the head falls back to the locally-resolved order[0]='a'.
    expect(pushMock).toHaveBeenCalledWith({
      name: 'ProjectLaunch',
      params: { projectId: 'a' },
      query: { run: 'run-123' },
    })
  })

  it('FE-6174c: routes to the head project from the create response resolved_order[0]', async () => {
    // When the BE echoes resolved_order, the head comes from the response (not the
    // locally-passed order) so a server-side re-order is honoured.
    createMock.mockResolvedValueOnce({ data: { id: 'run-9', resolved_order: ['head', 'tail'] } })
    const seq = useSequenceRunner()
    await seq.startSequence({
      projectIds: ['head', 'tail'],
      resolvedOrder: ['head', 'tail'],
      executionMode: 'multi_terminal',
    })
    expect(pushMock).toHaveBeenCalledWith({
      name: 'ProjectLaunch',
      params: { projectId: 'head' },
      query: { run: 'run-9' },
    })
  })

  it('defaults execution_mode to multi_terminal when none passed', async () => {
    const seq = useSequenceRunner()
    const order = ['x', 'y']
    await seq.startSequence({ projectIds: order, resolvedOrder: order })
    const body = createMock.mock.calls[0][0]
    expect(body.execution_mode).toBe('multi_terminal')
  })
})
