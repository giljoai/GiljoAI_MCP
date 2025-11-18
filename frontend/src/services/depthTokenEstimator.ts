/**
 * Token estimation service for depth configuration
 * Mirrors backend logic from depth_token_estimator.py
 *
 * Purpose: Client-side token estimation for real-time UI feedback
 * Backend Source: src/giljo_mcp/context/depth_token_estimator.py
 */

export interface DepthConfig {
  vision_chunking: 'none' | 'light' | 'moderate' | 'heavy';
  memory_last_n_projects: 1 | 3 | 5 | 10;
  git_commits: 10 | 25 | 50 | 100;
  agent_template_detail: 'minimal' | 'standard' | 'full';
  tech_stack_sections: 'required' | 'all';
  architecture_depth: 'overview' | 'detailed';
  product_core_enabled: boolean;  // Handover 0316: New field
  testing_config_depth: 'none' | 'basic' | 'full';  // Handover 0316: New field
}

export interface TokenEstimate {
  total: number;
  per_source: Record<string, number>;
}

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
  private static readonly TOKEN_ESTIMATES: Record<string, Record<string | number, number>> = {
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
      10: 500,
      25: 1250,
      50: 2500,
      100: 5000,
    },
    agent_template_detail: {
      minimal: 400,
      standard: 800,
      full: 2400,
    },
    tech_stack_sections: {
      required: 200,
      all: 400,
    },
    architecture_depth: {
      overview: 300,
      detailed: 1500,
    },
    // Handover 0316: New context tools
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

  /**
   * Calculate total estimated tokens for given depth configuration
   * @param depthConfig - User's depth configuration settings
   * @returns Total estimated tokens
   */
  static estimateTotal(depthConfig: DepthConfig): number {
    let total = 0;
    for (const [key, value] of Object.entries(depthConfig)) {
      if (key in this.TOKEN_ESTIMATES) {
        total += this.TOKEN_ESTIMATES[key][value] || 0;
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
    for (const [key, value] of Object.entries(depthConfig)) {
      if (key in this.TOKEN_ESTIMATES) {
        estimates[key] = this.TOKEN_ESTIMATES[key][value] || 0;
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
}
