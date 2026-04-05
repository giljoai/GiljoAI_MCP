import { describe, it, expect, beforeEach } from 'vitest'
import { ref } from 'vue'
import { useProjectFilters } from './useProjectFilters'

describe('useProjectFilters', () => {
  const makeProjectTypes = () => [
    { id: 'type-be', abbreviation: 'BE', label: 'Backend' },
    { id: 'type-fe', abbreviation: 'FE', label: 'Frontend' },
  ]

  const makeProjects = (productId = 'prod-1') => [
    { id: 'p1', name: 'Auth Service', status: 'active', project_type_id: 'type-be', product_id: productId, deleted_at: null, taxonomy_alias: 'BE-0001', mission: null },
    { id: 'p2', name: 'Dashboard', status: 'inactive', project_type_id: 'type-fe', product_id: productId, deleted_at: null, taxonomy_alias: 'FE-0001', mission: null },
    { id: 'p3', name: 'Old feature', status: 'completed', project_type_id: null, product_id: productId, deleted_at: null, taxonomy_alias: null, mission: 'important mission' },
    { id: 'p4', name: 'Wrong product', status: 'active', project_type_id: 'type-be', product_id: 'prod-other', deleted_at: null, taxonomy_alias: 'BE-0002', mission: null },
    { id: 'p5', name: 'Deleted project', status: 'deleted', project_type_id: null, product_id: productId, deleted_at: '2024-01-01', taxonomy_alias: null, mission: null },
  ]

  let projectTypes
  let projects
  let activeProduct

  beforeEach(() => {
    projectTypes = ref(makeProjectTypes())
    projects = ref(makeProjects())
    activeProduct = ref({ id: 'prod-1', name: 'Test Product' })
  })

  it('returns all non-deleted projects for active product when no filters', () => {
    const { sortedProjects } = useProjectFilters({ projectTypes, projects, activeProduct })
    expect(sortedProjects.value).toHaveLength(3)
    expect(sortedProjects.value.map((p) => p.id)).not.toContain('p4')
    expect(sortedProjects.value.map((p) => p.id)).not.toContain('p5')
  })

  it('returns empty list when no active product', () => {
    activeProduct = ref(null)
    const { sortedProjects } = useProjectFilters({ projectTypes, projects, activeProduct })
    expect(sortedProjects.value).toHaveLength(0)
  })

  it('typeSelectOptions includes project types and "No Type" option', () => {
    const { typeSelectOptions } = useProjectFilters({ projectTypes, projects, activeProduct })
    expect(typeSelectOptions.value).toHaveLength(3) // 2 types + "No Type"
    expect(typeSelectOptions.value.some((o) => o.value === 'none')).toBe(true)
    expect(typeSelectOptions.value.some((o) => o.title === 'BE')).toBe(true)
  })

  it('filters by search query on name', () => {
    const { sortedProjects, searchQuery } = useProjectFilters({ projectTypes, projects, activeProduct })
    searchQuery.value = 'auth'
    expect(sortedProjects.value).toHaveLength(1)
    expect(sortedProjects.value[0].id).toBe('p1')
  })

  it('filters by search query on mission text', () => {
    const { sortedProjects, searchQuery } = useProjectFilters({ projectTypes, projects, activeProduct })
    searchQuery.value = 'important'
    expect(sortedProjects.value).toHaveLength(1)
    expect(sortedProjects.value[0].id).toBe('p3')
  })

  it('filters by search query on project id', () => {
    const { sortedProjects, searchQuery } = useProjectFilters({ projectTypes, projects, activeProduct })
    searchQuery.value = 'p2'
    expect(sortedProjects.value).toHaveLength(1)
    expect(sortedProjects.value[0].id).toBe('p2')
  })

  it('filters by taxonomy_alias', () => {
    const { sortedProjects, searchQuery } = useProjectFilters({ projectTypes, projects, activeProduct })
    searchQuery.value = 'FE-0001'
    expect(sortedProjects.value).toHaveLength(1)
    expect(sortedProjects.value[0].id).toBe('p2')
  })

  it('filters by type id', () => {
    const { sortedProjects, filterType } = useProjectFilters({ projectTypes, projects, activeProduct })
    filterType.value = 'type-be'
    expect(sortedProjects.value).toHaveLength(1)
    expect(sortedProjects.value[0].id).toBe('p1')
  })

  it('filters by "none" type shows projects with no type', () => {
    const { sortedProjects, filterType } = useProjectFilters({ projectTypes, projects, activeProduct })
    filterType.value = 'none'
    expect(sortedProjects.value).toHaveLength(1)
    expect(sortedProjects.value[0].id).toBe('p3')
  })

  it('filters by status', () => {
    const { sortedProjects, filterStatus } = useProjectFilters({ projectTypes, projects, activeProduct })
    filterStatus.value = 'inactive'
    expect(sortedProjects.value).toHaveLength(1)
    expect(sortedProjects.value[0].id).toBe('p2')
  })

  it('active projects sort before inactive projects', () => {
    const { sortedProjects } = useProjectFilters({ projectTypes, projects, activeProduct })
    const statuses = sortedProjects.value.map((p) => p.status)
    const firstNonActive = statuses.findIndex((s) => s !== 'active')
    const lastActive = statuses.lastIndexOf('active')
    if (firstNonActive !== -1 && lastActive !== -1) {
      expect(lastActive).toBeLessThan(firstNonActive)
    }
  })

  it('clearFilters resets all filter state', () => {
    const { searchQuery, filterType, filterStatus, clearFilters } = useProjectFilters({ projectTypes, projects, activeProduct })
    searchQuery.value = 'something'
    filterType.value = 'type-be'
    filterStatus.value = 'active'
    clearFilters()
    expect(searchQuery.value).toBe('')
    expect(filterType.value).toBeNull()
    expect(filterStatus.value).toBeNull()
  })

  it('currentPage and itemsPerPage are exposed', () => {
    const { currentPage, itemsPerPage } = useProjectFilters({ projectTypes, projects, activeProduct })
    expect(currentPage.value).toBe(1)
    expect(itemsPerPage.value).toBe(10)
  })

  it('sortConfig is exposed', () => {
    const { sortConfig } = useProjectFilters({ projectTypes, projects, activeProduct })
    expect(sortConfig.value[0].key).toBe('created_at')
    expect(sortConfig.value[0].order).toBe('desc')
  })
})
