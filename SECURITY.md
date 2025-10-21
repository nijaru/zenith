# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.0.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please follow these steps:

### 1. **Do Not** Open a Public Issue

Security vulnerabilities should **not** be reported via public GitHub issues as this could put users at risk.

### 2. Report Privately

Please report security vulnerabilities by:

- **Email**: nijaru7@gmail.com
- **Subject**: `[SECURITY] Zenith vulnerability report`

### 3. Include in Your Report

To help us address the issue quickly, please include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)
- Your contact information

### 4. What to Expect

- **Initial Response**: Within 48 hours
- **Status Updates**: Every 72 hours during investigation
- **Resolution Timeline**: Critical issues within 7 days, others within 30 days
- **Credit**: We'll acknowledge your contribution in the security advisory (unless you prefer to remain anonymous)

## Security Best Practices

When using Zenith in production:

### 1. Keep Dependencies Updated

```bash
uv pip list --outdated
uv pip install --upgrade zenithweb
```

### 2. Use Strong Secret Keys

```bash
# Generate a secure secret key
zen keygen

# Or use Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Enable Security Middleware

```python
from zenith import Zenith
from zenith.middleware import SecurityHeadersMiddleware, CSRFMiddleware

app = Zenith()
app.add_middleware(SecurityHeadersMiddleware, {
    "force_https": True,
    "hsts_max_age": 31536000,
})
app.add_middleware(CSRFMiddleware)
```

### 4. Regular Security Audits

```bash
# Check for known vulnerabilities
uv run pip-audit

# Run linting with security checks
uv run ruff check . --select S
```

### 5. Environment Variables

Never commit secrets to version control:

```bash
# .env (gitignored)
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:pass@localhost/db
```

## Known Security Issues

### Current Issues

- **pip CVE-2025-8869** (GHSA-4xh5-x5gv-qwph)
  - **Severity**: Moderate (CVSS score pending)
  - **Affected**: All pip versions ≤ 25.2
  - **Impact**: Tarfile extraction vulnerability requiring malicious sdist
  - **Status**: Fix planned for pip 25.3 (not yet released)
  - **Mitigation**: Avoid installing packages from untrusted sources
  - **Risk**: Low in typical development environments

### Past Issues

None reported yet.

## Security Features

Zenith includes several built-in security features:

### Authentication & Authorization
- JWT token authentication with secure defaults
- Password hashing with bcrypt
- Configurable token expiration

### Protection Middleware
- CSRF protection with token validation
- CORS with flexible origin control
- Rate limiting (memory and Redis backends)
- Security headers (HSTS, CSP, X-Frame-Options)

### Database Security
- Parameterized queries (SQLAlchemy)
- Connection pooling with limits
- Async query execution

### Input Validation
- Pydantic models for request validation
- Type-safe dependency injection
- Automatic sanitization

## Security Release Process

1. **Discovery**: Vulnerability reported or discovered
2. **Triage**: Assess severity and impact (CVSS scoring)
3. **Development**: Create and test fix in private branch
4. **Testing**: Comprehensive testing including regression tests
5. **Disclosure**: Coordinate with reporter for responsible disclosure
6. **Release**: Publish patched version with security advisory
7. **Notification**: Announce via GitHub Security Advisory and CHANGELOG

## Security Disclosure Timeline

- **Day 0**: Vulnerability reported
- **Day 1-2**: Initial assessment and acknowledgment
- **Day 3-7**: Fix development and testing (critical issues)
- **Day 7-30**: Fix development and testing (non-critical issues)
- **Day 30+**: Public disclosure if reporter agrees

## Attribution

We believe in giving credit where credit is due. Security researchers who report valid vulnerabilities will be:

- Acknowledged in the security advisory
- Listed in CHANGELOG.md (if they wish)
- Given credit in release notes

Thank you for helping keep Zenith and its users safe!
