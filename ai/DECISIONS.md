# Architecture Decisions

<!--
## [YYYY-MM-DD] [Title]

**Context:**
[Problem statement and constraints]

**Decision:**
[The decision made]

**Rationale:**
[Why this decision was made]

**Consequences:**
[Pros, cons, and side effects]
-->

## 2025-10-01 Password Hashing
**Context:**
Need secure password hashing defaults.

**Decision:**
Use Argon2 instead of bcrypt.

**Rationale:**
Argon2 is the modern standard and resistant to GPU/ASIC attacks.

**Consequences:**
Requires `pwdlib[argon2]`.
