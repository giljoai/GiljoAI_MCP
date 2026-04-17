import { describe, it, expect, beforeEach } from 'vitest'
import { ref } from 'vue'
import { useProjectFilters } from './useProjectFilters'

describe('useProjectFilters', () => {
  const makeProjectTypes = () => [
    { id: 'type-be', abbreviation: 'BE', label: 'Backend' },
    { id: 'type-fe', abbreviation: 'FE', label: 'Frontend' },
  ]

  const makeProjects = (productId = 'prod-1') => [
    {
      id: 'p1',
      name: 'Auth Service',
      status: 'active',
      project_type_id: 'type-be',
      product_id: productId,
      deleted_at: null,
      taxonomy_alias: 'BE-0001',
      mission: null,
      hidden: false,
    },
    {
      id: 'p2',
      name: 'Dashboard',
      status: 'inactive',
      project_type_id: 'type-fe',
      product_id: productId,
      deleted_at: null,
      taxonomy_alias: 'FE-0001',
      mission: null,
      hidden: false,
    },
    {
      id: 'p3',
      name: 'Old feature',
      status: 'completed',
      project_type_id: null,
      product_id: productId,
      deleted_at: null,
      taxonomy_alias: null,
      mission: 'important mission',
      hidden: false,
    },
    {
      id: 'p4',
      name: 'Wrong product',
      status: 'active',
      project_type_id: 'type-be',
      product_id: 'prod-other',
      deleted_at: null,
      taxonomy_alias: 'BE-0002',
      mission: null,
      hidden: false,
    },
    {
      id: 'p5',
      name: 'Deleted project',
      status: 'deleted',
      project_type_id: null,
      product_id: productId,
      deleted_at: '2024-01-01',
      taxonomy_alias: null,
      mission: null,
      hidden: false,
    },
    {
      id: 'p6',
      name: 'Hidden Backend',
      status: 'active',
      project_type_id: 'type-be',
      product_id: productId,
      deleted_at: null,
      taxonomy_alias: 'BE-0003',
      mission: null,
      hidden: true,
    },
    {
      id: 'p7',
      name: 'Hidden No Type',
      status: 'inactive',
      project_type_id: null,
      product_id: productId,
      deleted_at: null,
      taxonomy_alias: null,
      mission: null,
      hidden: true,
    },
    {
      id: 'p8',
      name: 'Cancelled Service',
      status: 'cancelled',
      project_type_id: 'type-be',
      product_id: productId,
      deleted_at: null,
      taxonomy_alias: 'BE-0004',
      mission: null,
      hidden: false,
    },
  ]

  let projectTypes
  let projects
  let activeProduct

  beforeEach(() => {
    projectTypes = ref(makeProjectTypes())
    projects = ref(makeProjects())
    activeProduct = ref({ id: 'prod-1', name: 'Test Product' })
  })

  it('returns non-deleted, non-hidden projects when no filters', () => {
    const { filteredProjects } = useProjectFilters({
      projectTypes,
      projects,
      activeProduct,
    })
    const ids = filteredProjects.value.map((p) => p.id)
    expect(ids).toEqual(expect.arrayContaining(['p1', 'p2', 'p3', 'p8']))
    expect(ids).not.toContain('p4')
    expect(ids).not.toContain('p5')
    expect(ids).not.toContain('p6')
    expect(ids).not.toContain('p7')
  })

  it('returns empty list when no active product', () => {
    activeProduct = ref(null)
    const { filteredProjects } = useProjectFilters({
      projectTypes,
      projects,
      activeProduct,
    })
    expect(filteredProjects.value).toHaveLength(0)
  })

  it('typeSelectOptions includes project types and No Type option', () => {
    const { typeSelectOptions } = useProjectFilters({
      projectTypes,
      projects,
      activeProduct,
    })
    expect(typeSelectOptions.value).toHaveLength(3)
    expect(typeSelectOptions.value.some((o) => o.value === 'none')).toBe(true)
    expect(typeSelectOptions.value.some((o) => o.title === 'BE')).toBe(true)
  })

  it('filters by search query on name', () => {
    const { filteredBySearch, searchQuery } = useProjectFilters({
      projectTypes,
      projects,
      activeProduct,
    })
    searchQuery.value = 'auth'
    expect(filteredBySearch.value).toHaveLength(1)
    expect(filteredBySearch.value[0].id).toBe('p1')
  })

  it('filters by search query on mission text', () => {
    const { filteredBySearch, searchQuery } = useProjectFilters({
      projectTypes,
      projects,
      activeProduct,
    })
    searchQuery.value = 'important'
    expect(filteredBySearch.value).toHaveLength(1)
    expect(filteredBySearch.value[0].id).toBe('p3')
  })

  it('filters by search query on project id', () => {
    const { filteredBySearch, searchQuery } = useProjectFilters({
      projectTypes,
      projects,
      activeProduct,
    })
    searchQuery.value = 'p2'
    expect(filteredBySearch.value).toHaveLength(1)
    expect(filteredBySearch.value[0].id).toBe('p2')
  })

  it('filters by taxonomy_alias', () => {
    const { filteredBySearch, searchQuery } = useProjectFilters({
      projectTypes,
      projects,
      activeProduct,
    })
    searchQuery.value = 'FE-0001'
    expect(filteredBySearch.value).toHaveLength(1)
    expect(filteredBySearch.value[0].id).toBe('p2')
  })

  it('filters by type id', () => {
    const { filteredBySearch, filterType } = useProjectFilters({
      projectTypes,
      projects,
      activeProduct,
    })
    filterType.value = 'type-be'
    const ids = filteredBySearch.value.map((p) => p.id)
    expect(ids).toContain('p1')
  })

  it('filters by none type shows projects with no type', () => {
    const { filteredBySearch, filterType } = useProjectFilters({
      projectTypes,
      projects,
      activeProduct,
    })
    filterType.value = 'none'
    const ids = filteredBySearch.value.map((p) => p.id)
    expect(ids).toContain('p3')
  })

  it('filters by status', () => {
    const { filteredProjects, filterStatus } = useProjectFilters({
      projectTypes,
      projects,
      activeProduct,
    })
    filterStatus.value = 'inactive'
    expect(filteredProjects.value).toHaveLength(1)
    expect(filteredProjects.value[0].id).toBe('p2')
  })

  it('active projects are included in filteredProjects', () => {
    const { filteredProjects } = useProjectFilters({
      projectTypes,
      projects,
      activeProduct,
    })
    const activeProjects = filteredProjects.value.filter(
      (p) => p.status === 'active',
    )
    expect(activeProjects.length).toBeGreaterThan(0)
  })

  it('clearFilters resets all filter state', () => {
    const { searchQuery, filterType, filterStatus, clearFilters } =
      useProjectFilters({ projectTypes, projects, activeProduct })
    searchQuery.value = 'something'
    filterType.value = 'type-be'
    filterStatus.value = 'active'
    clearFilters()
    expect(searchQuery.value).toBe('')
    expect(filterType.value).toBeNull()
    expect(filterStatus.value).toBeNull()
  })

  it('currentPage and itemsPerPage are exposed', () => {
    const { currentPage, itemsPerPage } = useProjectFilters({
      projectTypes,
      projects,
      activeProduct,
    })
    expect(currentPage.value).toBe(1)
    expect(itemsPerPage.value).toBe(10)
  })

  // --- Fix 4: Hidden filter bug ---
  describe('hidden project exclusion', () => {
    it('excludes hidden projects when only type filter is active', () => {
      const { filteredProjects, filterType } = useProjectFilters({
        projectTypes,
        projects,
        activeProduct,
      })
      filterType.value = 'type-be'
      const ids = filteredProjects.value.map((p) => p.id)
      expect(ids).toContain('p1')
      expect(ids).not.toContain('p6')
    })

    it('excludes hidden projects when only search is active', () => {
      const { filteredProjects, searchQuery } = useProjectFilters({
        projectTypes,
        projects,
        activeProduct,
      })
      searchQuery.value = 'Hidden'
      const ids = filteredProjects.value.map((p) => p.id)
      expect(ids).toHaveLength(0)
    })

    it('shows hidden projects only when status filter is hidden', () => {
      const { filteredProjects, filterStatus } = useProjectFilters({
        projectTypes,
        projects,
        activeProduct,
      })
      filterStatus.value = 'hidden'
      const ids = filteredProjects.value.map((p) => p.id)
      expect(ids).toContain('p6')
      expect(ids).toContain('p7')
      expect(ids).not.toContain('p1')
    })

    it('shows hidden projects of specific type when both filters active', () => {
      const { filteredProjects, filterStatus, filterType } =
        useProjectFilters({ projectTypes, projects, activeProduct })
      filterStatus.value = 'hidden'
      filterType.value = 'type-be'
      const ids = filteredProjects.value.map((p) => p.id)
      expect(ids).toContain('p6')
      expect(ids).not.toContain('p7')
    })
  })

  // --- Fix 5: Cancelled project filter exclusion ---
  describe('cancelled project visibility', () => {
    it('shows cancelled projects in default view', () => {
      const { filteredProjects } = useProjectFilters({
        projectTypes,
        projects,
        activeProduct,
      })
      const ids = filteredProjects.value.map((p) => p.id)
      expect(ids).toContain('p8')
    })

    it('shows only cancelled projects when status filter is cancelled', () => {
      const { filteredProjects, filterStatus } = useProjectFilters({
        projectTypes,
        projects,
        activeProduct,
      })
      filterStatus.value = 'cancelled'
      const ids = filteredProjects.value.map((p) => p.id)
      expect(ids).toContain('p8')
      expect(ids).not.toContain('p1')
    })

    it('shows cancelled projects when type filter is active', () => {
      const { filteredProjects, filterType } = useProjectFilters({
        projectTypes,
        projects,
        activeProduct,
      })
      filterType.value = 'type-be'
      const ids = filteredProjects.value.map((p) => p.id)
      expect(ids).toContain('p1')
      expect(ids).toContain('p8')
    })
  })
})
