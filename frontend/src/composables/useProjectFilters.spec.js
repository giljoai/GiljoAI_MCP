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
    const { filteredProjects } = useProjectFilters({ projectTypes, projects, activeProduct })
    expect(filteredProjects.value).toHaveLength(3)
    expect(filteredProjects.value.map((p) => p.id)).not.toContain('p4')
    expect(filteredProjects.value.map((p) => p.id)).not.toContain('p5')
  })

  it('returns empty list when no active product', () => {
    activeProduct = ref(null)
    const { filteredProjects } = useProjectFilters({ projectTypes, projects, activeProduct })
    expect(filteredProjects.value).toHaveLength(0)
  })

  it('typeSelectOptions includes project types and "No Type" option', () => {
    const { typeSelectOptions } = useProjectFilters({ projectTypes, projects, activeProduct })
    expect(typeSelectOptions.value).toHaveLength(3) // 2 types + "No Type"
    expect(typeSelectOptions.value.some((o) => o.value === 'none')).toBe(true)
    expect(typeSelectOptions.value.some((o) => o.title === 'BE')).toBe(true)
  })

  it('filters by search query on name', () => {
    const { filteredBySearch, searchQuery } = useProjectFilters({ projectTypes, projects, activeProduct })
    searchQuery.value = 'auth'
    expect(filteredBySearch.value).toHaveLength(1)
    expect(filteredBySearch.value[0].id).toBe('p1')
  })

  it('filters by search query on mission text', () => {
    const { filteredBySearch, searchQuery } = useProjectFilters({ projectTypes, projects, activeProduct })
    searchQuery.value = 'important'
    expect(filteredBySearch.value).toHaveLength(1)
    expect(filteredBySearch.value[0].id).toBe('p3')
  })

  it('filters by search query on project id', () => {
    const { filteredBySearch, searchQuery } = useProjectFilters({ projectTypes, projects, activeProduct })
    searchQuery.value = 'p2'
    expect(filteredBySearch.value).toHaveLength(1)
    expect(filteredBySearch.value[0].id).toBe('p2')
  })

  it('filters by taxonomy_alias', () => {
    const { filteredBySearch, searchQuery } = useProjectFilters({ projectTypes, projects, activeProduct })
    searchQuery.value = 'FE-0001'
    expect(filteredBySearch.value).toHaveLength(1)
    expect(filteredBySearch.value[0].id).toBe('p2')
  })

  it('filters by type id', () => {
    const { filteredBySearch, filterType } = useProjectFilters({ projectTypes, projects, activeProduct })
    filterType.value = 'type-be'
    expect(filteredBySearch.value).toHaveLength(1)
    expect(filteredBySearch.value[0].id).toBe('p1')
  })

  it('filters by "none" type shows projects with no type', () => {
    const { filteredBySearch, filterType } = useProjectFilters({ projectTypes, projects, activeProduct })
    filterType.value = 'none'
    expect(filteredBySearch.value).toHaveLength(1)
    expect(filteredBySearch.value[0].id).toBe('p3')
  })

  it('filters by status', () => {
    const { filteredProjects, filterStatus } = useProjectFilters({ projectTypes, projects, activeProduct })
    filterStatus.value = 'inactive'
    expect(filteredProjects.value).toHaveLength(1)
    expect(filteredProjects.value[0].id).toBe('p2')
  })

  it('active projects are included in filteredProjects', () => {
    const { filteredProjects } = useProjectFilters({ projectTypes, projects, activeProduct })
    const activeProjects = filteredProjects.value.filter((p) => p.status === 'active')
    expect(activeProjects.length).toBeGreaterThan(0)
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
})
