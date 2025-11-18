/**
 * Token estimation service for depth configuration
 * Mirrors backend logic from depth_token_estimator.py
 *
 * Purpose: Client-side token estimation for real-time UI feedback
 * Backend Source: src/giljo_mcp/context/depth_token_estimator.py
 *
 * Handover 0319: Updated for Context Management v3.0
 * - Added granular field selection for tech_stack, architecture, testing
 * - Project context is always included (~200 tokens)
 */

// Field selection configuration for granular control
export interface TechStackFields {
  languages: boolean;
  frameworks: boolean;
  databases: boolean;
  dependencies: boolean;
}

export interface ArchitectureFields {
  primary_pattern: boolean;
  api_style: boolean;
  design_patterns: boolean;
  architecture_notes: boolean;
  security_considerations: boolean;
  scalability_notes: boolean;
}

export interface TestingFields {
  quality_standards: boolean;
  testing_strategy: boolean;
  testing_frameworks: boolean;
}

export interface DepthConfig {
  vision_chunking: 'none' | 'light' | 'moderate' | 'heavy';
  memory_last_n_projects: 1 | 3 | 5 | 10;
  git_commits: 0 | 5 | 15 | 25;  // Updated for v3.0
  agent_template_detail: 'type_only' | 'full';  // Updated for v3.0
  product_core_enabled: boolean;
  // v3.0: Field-based selection for tech_stack, architecture, testing
  tech_stack_fields?: TechStackFields;
  architecture_fields?: ArchitectureFields;
  testing_fields?: TestingFields;
  // Legacy fields (deprecated in v3.0)
  tech_stack_sections?: 'required' | 'all';
  architecture_depth?: 'overview' | 'detailed';
  testing_config_depth?: 'none' | 'basic' | 'full';
  project_context_enabled?: boolean;  // Deprecated: always included in v3.0
}

export interface TokenEstimate {
  total: number;
  per_source: Record<string, number>;
}

/**
 * Field token definitions for granular selection
 */
export const FIELD_TOKENS = {
  tech_stack: {
    languages: 50,
    frameworks: 100,
    databases: 50,
    dependencies: 100,
  },
  architecture: {
    primary_pattern: 50,
    api_style: 50,
    design_patterns: 150,
    architecture_notes: 500,
    security_considerations: 300,
    scalability_notes: 200,
  },
  testing: {
    quality_standards: 100,
    testing_strategy: 150,
    testing_frameworks: 100,
  },
};

/**
 * Client-side token estimator for depth configuration
 *
 * IMPORTANT: Token estimates must match backend exactly
 * See: src/giljo_mcp/context/depth_token_estimator.py
 */
export class DepthTokenEstimator {
  /**
   * Token estimates per depth setting
   * These values MUST match backend constants exactly
   */
  private static readonly TOKEN_ESTIMATES: Record<string, Record<string | number | boolean, number>> = {
    vision_chunking: {
      none: 0,
      light: 10000,
      moderate: 17500,
      heavy: 30000,
    },
    memory_last_n_projects: {
      1: 500,
      3: 1500,
      5: 2500,
      10: 5000,
    },
    git_commits: {
      0: 0,
      5: 250,
      15: 750,
      25: 1250,
      10: 500,  // Legacy support
      50: 2500,  // Legacy support
      100: 5000,  // Legacy support
    },
    agent_template_detail: {
      type_only: 400,
      full: 2400,
      minimal: 400,  // Legacy support
      standard: 800,  // Legacy support
    },
    // Legacy fields
    tech_stack_sections: {
      required: 200,
      all: 400,
    },
    architecture_depth: {
      overview: 300,
      detailed: 1500,
    },
    product_core_enabled: {
      true: 100,
      false: 0,
    },
    testing_config_depth: {
      none: 0,
      basic: 150,
      full: 400,
    },
  };

  // Project context is always included in v3.0
  private static readonly PROJECT_CONTEXT_TOKENS = 200;

  /**
   * Calculate tokens for field-based selection
   */
  static calculateFieldTokens(
    fields: Record<string, boolean> | undefined,
    tokenMap: Record<string, number>
  ): number {
    if (!fields) return 0;
    return Object.entries(fields).reduce((sum, [key, selected]) => {
      return sum + (selected ? (tokenMap[key] || 0) : 0);
    }, 0);
  }

  /**
   * Calculate total estimated tokens for given depth configuration
   * @param depthConfig - User's depth configuration settings
   * @returns Total estimated tokens
   */
  static estimateTotal(depthConfig: DepthConfig): number {
    let total = 0;

    // Always include project context in v3.0
    total += this.PROJECT_CONTEXT_TOKENS;

    // Process each config key
    for (const [key, value] of Object.entries(depthConfig)) {
      // Skip field-based configs - they're handled separately
      if (key.endsWith('_fields')) continue;

      // Handle v3.0 field-based selection
      if (key === 'tech_stack_fields' && value) {
        total += this.calculateFieldTokens(value as TechStackFields, FIELD_TOKENS.tech_stack);
        continue;
      }
      if (key === 'architecture_fields' && value) {
        total += this.calculateFieldTokens(value as ArchitectureFields, FIELD_TOKENS.architecture);
        continue;
      }
      if (key === 'testing_fields' && value) {
        total += this.calculateFieldTokens(value as TestingFields, FIELD_TOKENS.testing);
        continue;
      }

      // Legacy dropdown-based config
      if (key in this.TOKEN_ESTIMATES) {
        total += this.TOKEN_ESTIMATES[key][value as string | number | boolean] || 0;
      }
    }

    return total;
  }

  /**
   * Calculate per-source token estimates
   * @param depthConfig - User's depth configuration settings
   * @returns Token estimates broken down by source
   */
  static estimatePerSource(depthConfig: DepthConfig): Record<string, number> {
    const estimates: Record<string, number> = {};

    // Always include project context in v3.0
    estimates['project_context'] = this.PROJECT_CONTEXT_TOKENS;

    for (const [key, value] of Object.entries(depthConfig)) {
      // Skip field-based configs for legacy key lookup
      if (key.endsWith('_fields')) continue;

      // Handle v3.0 field-based selection
      if (key === 'tech_stack_fields' && value) {
        estimates['tech_stack'] = this.calculateFieldTokens(
          value as TechStackFields,
          FIELD_TOKENS.tech_stack
        );
        continue;
      }
      if (key === 'architecture_fields' && value) {
        estimates['architecture'] = this.calculateFieldTokens(
          value as ArchitectureFields,
          FIELD_TOKENS.architecture
        );
        continue;
      }
      if (key === 'testing_fields' && value) {
        estimates['testing'] = this.calculateFieldTokens(
          value as TestingFields,
          FIELD_TOKENS.testing
        );
        continue;
      }

      // Legacy dropdown-based config
      if (key in this.TOKEN_ESTIMATES) {
        estimates[key] = this.TOKEN_ESTIMATES[key][value as string | number | boolean] || 0;
      }
    }

    return estimates;
  }

  /**
   * Calculate complete token estimate with total and breakdown
   * @param depthConfig - User's depth configuration settings
   * @returns Complete token estimate object
   */
  static estimate(depthConfig: DepthConfig): TokenEstimate {
    return {
      total: this.estimateTotal(depthConfig),
      per_source: this.estimatePerSource(depthConfig),
    };
  }

  /**
   * Get field definitions with labels and token estimates
   * Used by FieldCheckboxGroup component
   */
  static getTechStackFieldDefinitions() {
    return [
      { key: 'languages', label: 'Programming Languages', tokens: FIELD_TOKENS.tech_stack.languages },
      { key: 'frameworks', label: 'Frameworks', tokens: FIELD_TOKENS.tech_stack.frameworks },
      { key: 'databases', label: 'Databases', tokens: FIELD_TOKENS.tech_stack.databases },
      { key: 'dependencies', label: 'Dependencies', tokens: FIELD_TOKENS.tech_stack.dependencies },
    ];
  }

  static getArchitectureFieldDefinitions() {
    return [
      { key: 'primary_pattern', label: 'Primary Pattern', tokens: FIELD_TOKENS.architecture.primary_pattern },
      { key: 'api_style', label: 'API Style', tokens: FIELD_TOKENS.architecture.api_style },
      { key: 'design_patterns', label: 'Design Patterns', tokens: FIELD_TOKENS.architecture.design_patterns },
      { key: 'architecture_notes', label: 'Architecture Notes', tokens: FIELD_TOKENS.architecture.architecture_notes },
      { key: 'security_considerations', label: 'Security Considerations', tokens: FIELD_TOKENS.architecture.security_considerations },
      { key: 'scalability_notes', label: 'Scalability Notes', tokens: FIELD_TOKENS.architecture.scalability_notes },
    ];
  }

  static getTestingFieldDefinitions() {
    return [
      { key: 'quality_standards', label: 'Quality Standards', tokens: FIELD_TOKENS.testing.quality_standards },
      { key: 'testing_strategy', label: 'Testing Strategy', tokens: FIELD_TOKENS.testing.testing_strategy },
      { key: 'testing_frameworks', label: 'Testing Frameworks', tokens: FIELD_TOKENS.testing.testing_frameworks },
    ];
  }
}
