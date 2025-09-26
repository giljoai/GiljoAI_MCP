# Linting Standards & Enforcement

## Overview

This document outlines the comprehensive linting standards for the GiljoAI MCP Coding Orchestrator project, covering Python backend code, Vue.js frontend code, and CI/CD enforcement procedures.

## Python Linting Standards

### Ruff Configuration

We use Ruff as our primary Python linter and formatter, configured via `.ruff.toml`:

- **Line Length**: 120 characters
- **Python Version**: 3.9+
- **Comprehensive Rule Set**: 40+ rule categories enabled
- **Auto-fixing**: Enabled for all compatible rules

#### Key Rule Categories

| Category              | Rules     | Purpose                                   |
| --------------------- | --------- | ----------------------------------------- |
| **Core Quality**      | E, W, F   | pycodestyle errors/warnings, pyflakes     |
| **Import Management** | I, TID    | isort, tidy-imports                       |
| **Security**          | S, BLE    | bandit security checks, blind except      |
| **Performance**       | PERF, C4  | Performance optimizations, comprehensions |
| **Type Safety**       | TCH, UP   | Type checking, pyupgrade                  |
| **Code Style**        | N, Q, COM | PEP 8 naming, quotes, commas              |

#### Ignored Rules (Production Justified)

```toml
ignore = [
    "E501",   # Line too long - handled by formatter
    "S101",   # Use of assert detected - needed for tests
    "COM812", # Missing trailing comma - handled by formatter
    "C901",   # Too complex - addressed case by case
]
```

### Security Standards

- **Bandit Integration**: Security vulnerability scanning
- **No Hardcoded Secrets**: Enforced via S105-S108 rules
- **Safe File Handling**: PTH rules for pathlib usage
- **SQL Injection Prevention**: Parameterized queries enforced

### Testing Standards

- **Test Isolation**: Each test function focuses on single behavior
- **Assert Usage**: Allowed in tests (S101 ignored)
- **Mock Patterns**: Consistent async mock usage
- **Coverage Requirements**: 80%+ code coverage target

## Frontend Linting Standards

### ESLint Configuration

Comprehensive Vue 3 + JavaScript linting via `.eslintrc.json`:

- **Vue 3 Optimized**: vue/vue3-recommended rules
- **Prettier Integration**: @vue/eslint-config-prettier
- **TypeScript Ready**: .ts/.tsx support configured
- **Component Standards**: Enforced component organization

#### Key Frontend Rules

| Category           | Rules                         | Enforcement                    |
| ------------------ | ----------------------------- | ------------------------------ |
| **Vue Components** | vue/component-tags-order      | template, script, style order  |
| **Code Quality**   | no-console, no-debugger       | Warnings/errors for production |
| **ES6+ Standards** | prefer-const, arrow-functions | Modern JavaScript patterns     |
| **Accessibility**  | Vuetify compliance            | WCAG 2.1 AA standards          |

### Prettier Configuration

Consistent code formatting via `.prettierrc`:

```json
{
  "semi": false,
  "singleQuote": true,
  "tabWidth": 2,
  "printWidth": 100,
  "trailingComma": "all"
}
```

## Enforcement Procedures

### 1. Pre-commit Hooks

Automatic enforcement via `.pre-commit-config.yaml`:

```bash
# Install hooks
pre-commit install

# Run on staged files
pre-commit run

# Run on all files
pre-commit run --all-files
```

#### Hook Categories

- **Python Linting**: Ruff check + format
- **Security Scanning**: Bandit, detect-private-key
- **File Quality**: trailing-whitespace, end-of-file-fixer
- **Frontend Linting**: ESLint + Prettier
- **Documentation**: Codespell, markdown formatting

### 2. CI/CD Pipeline

Comprehensive GitHub Actions workflow (`.github/workflows/ci.yml`):

#### Pipeline Stages

1. **Linting & Security** (Parallel)

   - Python: Ruff + Bandit + MyPy
   - Frontend: ESLint + Prettier + Build
   - Security: Trivy vulnerability scanning

2. **Testing** (Matrix)

   - Unit tests across Python 3.9-3.11
   - Integration tests with PostgreSQL
   - Performance benchmarking

3. **Quality Gates**

   - 80%+ code coverage requirement
   - Zero critical security vulnerabilities
   - All linting rules must pass

4. **Deployment Readiness**
   - All checks must pass for deployment approval
   - Automatic artifact generation

### 3. Development Workflow

#### Before Committing

```bash
# Run auto-fixes
ruff check --fix src/ tests/
ruff format src/ tests/

# Frontend formatting
cd frontend && npm run lint && npm run format

# Verify all checks pass
pre-commit run --all-files
```

#### Branch Protection

- **Main/Master**: Require PR + all CI checks
- **Develop**: Require CI checks
- **Feature Branches**: Require linting checks

## Error Handling Standards

### Exception Handling

- **Specific Exceptions**: Avoid bare `except:` clauses
- **Logging**: Use structured logging over print statements
- **Context Preservation**: Include relevant context in error messages
- **Graceful Degradation**: Handle failures without crashing

### Production Standards

```python
# Good: Specific exception handling
try:
    result = risky_operation()
except SpecificError as e:
    logger.exception(f"Operation failed: {e}")
    return default_value

# Bad: Bare except
try:
    result = risky_operation()
except:
    pass  # Silent failure
```

## Performance Standards

### Code Performance

- **Import Optimization**: Top-level imports preferred
- **Comprehensions**: Prefer over manual loops where readable
- **Async/Await**: Proper async patterns for I/O operations
- **Database**: Use parameterized queries, connection pooling

### Monitoring

- **Ruff Performance Rules**: PERF category enabled
- **Benchmark Tests**: Performance regression testing
- **Memory Usage**: psutil monitoring in tests
- **Load Testing**: 100+ concurrent agent simulation

## Maintenance Procedures

### Regular Updates

1. **Monthly**: Update pre-commit hook versions
2. **Quarterly**: Review and update ruff rules
3. **Release**: Run comprehensive linting audit

### Rule Evolution

- **New Rules**: Evaluate impact before enabling
- **Deprecations**: Gradual migration with tooling support
- **Team Review**: Consensus required for standard changes

### Troubleshooting

#### Common Issues

1. **Import Organization**: Run `ruff check --select I001 --fix`
2. **Line Length**: Use formatter: `ruff format`
3. **Security Warnings**: Review Bandit output carefully
4. **Frontend Build**: Ensure `npm ci` before linting

#### Emergency Overrides

```python
# Temporary disable (use sparingly)
# ruff: noqa: E501
very_long_line_that_cannot_be_broken = "..."

# Disable for entire file (last resort)
# ruff: noqa
```

## Integration with Development Tools

### IDE Setup

#### VS Code

```json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "ruff",
  "eslint.workingDirectories": ["frontend"],
  "editor.formatOnSave": true
}
```

#### PyCharm

- Install Ruff plugin
- Configure external tool for auto-formatting
- Enable ESLint for frontend directory

### Command Line Tools

```bash
# Python linting
ruff check src/ tests/
ruff format src/ tests/

# Frontend linting
cd frontend
npm run lint
npm run format

# Full project check
pre-commit run --all-files

# CI simulation
act  # GitHub Actions locally
```

## Metrics & Reporting

### Quality Metrics

- **Linting Violations**: < 50 total project-wide
- **Security Issues**: Zero critical/high severity
- **Code Coverage**: 80%+ for production code
- **Build Success**: 100% on main branch

### Automated Reporting

- **GitHub Actions**: Violation summaries in PR comments
- **Codecov**: Coverage trend analysis
- **Security**: Automated vulnerability alerts
- **Performance**: Benchmark regression detection

## Conclusion

These linting standards ensure:

- **Consistent Code Quality**: Uniform style across all contributors
- **Security Assurance**: Proactive vulnerability prevention
- **Maintainability**: Clear, readable, and documented code
- **Performance**: Optimized patterns and practices
- **Reliability**: Comprehensive testing and validation

All developers must follow these standards. Questions or proposed changes should be discussed in team meetings or GitHub issues.
