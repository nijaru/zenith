# Linear Project Management

## Quick Setup (For Linear MCP Instance)

### Create Team & Projects
```bash
# Team: Zenith Framework (ZNTH)
# Projects:
- Core Framework (CORE) - App kernel, routing, contexts
- LiveView (LIVE) - Real-time UI components  
- Channels (CHAN) - WebSocket communication
- Database (DB) - ORM, migrations, queries
- Auth (AUTH) - Authentication & security
- CLI (CLI) - Command-line tools
- Docs (DOCS) - Documentation
- DevOps (OPS) - CI/CD, deployment
```

### Essential Labels
```yaml
Priority: P0 (critical), P1 (high), P2 (medium), P3 (low)
Type: feat, bug, task, docs, perf, spike
Status: blocked, needs-review, ready
Version: v0.1.0, v0.2.0, v0.3.0
```

### Workflow States
`Backlog → Todo → In Progress → In Review → Done → Closed`

## Issue Management

### Naming Convention
```
feat: Brief feature description
bug: What's broken and where
task: Administrative work needed
docs: Documentation to create/update
spike: Research question to answer
```

### Priority Guidelines
- **P0**: Security, production blockers
- **P1**: Core features, release blockers  
- **P2**: Important improvements
- **P3**: Nice to have, future

### Sprint Planning (2 weeks)
- Target: ~40 points team velocity
- Mix: 70% features, 20% bugs, 10% tech debt
- Buffer: 20% for unexpected issues

## Core Framework Issues (v0.1.0)

### Application Kernel
```yaml
title: "feat: Implement application kernel"
project: Core Framework
priority: P0
estimate: 8
description: |
  Core app class managing:
  - Supervisor tree
  - DI container  
  - Config loading
  - Lifecycle hooks
```

### Routing System  
```yaml
title: "feat: Basic HTTP routing"
project: Core Framework
priority: P0
estimate: 5
description: |
  HTTP routing with:
  - Route registration
  - Path matching
  - Parameter extraction
  - Method routing
```

### Context System
```yaml
title: "feat: Context system implementation" 
project: Core Framework
priority: P0
estimate: 8
description: |
  Phoenix-style contexts:
  - Context base class
  - Registration system
  - Event emission
  - Inter-context communication
```

### Additional v0.1.0 Issues
- Request/Response handling (5 points)
- Controller support (5 points)  
- Template rendering (3 points)
- Development server (5 points)
- CLI foundation (5 points)
- Basic testing (3 points)

## Templates

### Feature Template
```markdown
## Summary
[One-line description]

## API Example
```python
# Usage example
```

## Acceptance Criteria
- [ ] Core functionality works
- [ ] Tests written
- [ ] Documentation updated

## Notes
[Additional context]
```

### Bug Template
```markdown
## Problem
[What's broken]

## Steps to Reproduce
1. Step one
2. Step two
3. See error

## Expected vs Actual
- Expected: [should happen]
- Actual: [does happen]

## Fix Ideas
[Potential solutions]
```

## Automation Rules

### Auto-transitions
- PR created → "In Review"
- PR merged → "Done" 
- PR closed → "In Progress"

### Auto-assignment
- P0 issues → Team lead
- Security issues → Security team
- Documentation → Tech writer

## Views

### Current Sprint
- Filter: `cycle = current`
- Group by: Status
- Sort: Priority

### My Work
- Filter: `assignee = me AND status != done`
- Group by: Project
- Sort: Priority

### Bugs
- Filter: `label contains bug`
- Group by: Priority
- Sort: Created date

## Development Workflow

### Branch Strategy
```
main (production)
├── develop (integration)
│   ├── feat/ZNTH-123-feature-name
│   ├── fix/ZNTH-456-bug-name
│   └── docs/ZNTH-789-doc-update
└── release/v0.1.0 (release prep)
```

### Commit Format
```
[ZNTH-123] type: Description

Optional body with more details.

Closes ZNTH-123
```

### PR Requirements
- [ ] Tests pass
- [ ] Code review approved
- [ ] Linear issue linked
- [ ] No merge conflicts
- [ ] CI checks pass

## Metrics Tracking

### Velocity
- Points completed per sprint
- Trend over time
- Individual vs team

### Cycle Time
- In Progress → Done duration
- Target: <3 days average

### Bug Rate
- New bugs per sprint
- Bug resolution time
- Bug vs feature ratio

### Review Time
- PR review duration
- Target: <24 hours

## Quick Reference

### Issue Commands
```
/assign @nick     # Assign to user
/label P0         # Add priority
/estimate 5       # Set story points
/project Core     # Add to project
```

### Filters
```
is:open assignee:me          # My open issues
label:P0 status:"In Progress" # Critical work
project:"Core Framework"      # Core issues  
cycle:current                # Current sprint
```

### Keyboard Shortcuts
- `C` - Create issue
- `G I` - Go to issues
- `/` - Search
- `Cmd+K` - Command palette

---
*Internal Linear workflow - for core team*