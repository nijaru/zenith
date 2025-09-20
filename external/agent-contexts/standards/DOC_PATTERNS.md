# Documentation Organization Patterns for AI Agent Contexts

This document defines standards for organizing internal documentation that serves both human developers and AI agents effectively.

## Core Principles

### 1. Dual-Purpose Documentation
- **Human-Readable**: Clear structure, practical examples, decision rationale
- **AI-Parseable**: Consistent formatting, structured data, context preservation

### 2. Information Hierarchy
- **Strategic** (long-term): Vision, roadmap, architectural decisions
- **Tactical** (current): Status, priorities, active development context
- **Operational** (immediate): Commands, patterns, troubleshooting

### 3. Context Preservation
- Maintain historical context in archive/
- Preserve user feedback and real-world usage patterns
- Document decision rationale, not just decisions

## Directory Structure Standard

```
docs/internal/
├── README.md              # Navigation hub and current state summary
├── DEVELOPMENT.md          # Current development context for AI agents
├── STRATEGY.md            # Product strategy and competitive positioning
├── PERFORMANCE.md         # Performance standards and optimization guide
├── feedback/             # Real-world usage feedback and migration experiences
│   ├── project-name-migration.md
│   └── user-experience-reports.md
└── archive/              # Historical documents and deprecated plans
    ├── old-strategies/
    ├── completed-roadmaps/
    └── deprecated-features/
```

## File Naming Conventions

### Core Documents (Always Present)
- `README.md` - Current state summary and navigation
- `DEVELOPMENT.md` - Active development context
- `STRATEGY.md` - Strategic direction and positioning

### Context-Specific Documents
- `PERFORMANCE.md` - Performance standards and optimization
- `ARCHITECTURE.md` - Technical architecture decisions
- `ROADMAP.md` - Future planning and milestones

### User Feedback (feedback/ directory)
- `{project-name}-migration.md` - Migration experiences from real projects
- `{user-type}-feedback.md` - Feedback from specific user segments
- `{feature}-usage-patterns.md` - Real-world usage data

### Historical Context (archive/ directory)
- `{date}-{topic}.md` - Timestamped historical documents
- `v{version}-roadmap.md` - Version-specific planning documents
- `deprecated-{feature}.md` - Removed feature documentation

## Content Structure Standards

### DEVELOPMENT.md Template
```markdown
# Framework Development Context

## Current Status (v{version})
- **Version**: Current version and key characteristics
- **Tests**: Test coverage and health metrics
- **Performance**: Key performance indicators
- **Priorities**: Current development focus

## Code Patterns (v{version})
- Import patterns
- Common code examples
- Best practices
- Anti-patterns to avoid

## Development Workflow
- Testing commands
- Build commands
- Release process
- Quality gates

## For AI Agents
- Key context for code generation
- Framework-specific patterns
- Common troubleshooting
```

### STRATEGY.md Template
```markdown
# Framework Strategy

## Vision Statement
- Core mission and values
- Target market definition
- Competitive advantages

## Market Position
- Target users and use cases
- Differentiation from competitors
- Value proposition

## Development Roadmap
- Short-term priorities (1-3 months)
- Medium-term goals (3-12 months)
- Long-term vision (1+ years)

## Success Metrics
- Adoption metrics
- Performance targets
- Quality standards
```

### Feedback Document Template
```markdown
# {Project Name} - Framework Feedback

## Overview
- Project description
- Framework usage context
- Migration/adoption experience

## What Worked Well
- Successful patterns
- Positive experiences
- Efficiency gains

## Pain Points
- Challenges encountered
- Missing features
- Improvement suggestions

## Recommendations
- Framework improvements
- Documentation needs
- Feature requests

## Impact Assessment
- Time savings/costs
- Performance impact
- Developer experience rating
```

## AI Agent Optimization

### Structured Data Sections
Use consistent section headers for AI parsing:
- `## Current Status` - Always present in DEVELOPMENT.md
- `## Code Patterns` - Framework-specific patterns
- `## Success Metrics` - Measurable outcomes
- `## Recommendations` - Actionable next steps

### Context Markers
Use consistent markers for AI context:
- `**Version**: x.y.z` - Current version references
- `**Status**: [In Progress|Completed|Planned]` - Task status
- `**Priority**: [High|Medium|Low]` - Importance ranking
- `**Impact**: [High|Medium|Low]` - Change significance

### Code Examples
Always include working code examples:
```python
# Pattern: Enhanced model usage (v0.3.1)
from zenith.db import ZenithModel
from sqlmodel import Field

class User(ZenithModel, table=True):
    id: int | None = Field(primary_key=True)
    name: str

# Usage (no session management needed)
users = await User.where(active=True).limit(10)
```

## Maintenance Guidelines

### Regular Reviews
- **Monthly**: Update DEVELOPMENT.md with current status
- **Quarterly**: Review and update STRATEGY.md
- **Per Release**: Archive completed roadmap items
- **Continuous**: Add user feedback as received

### Archive Management
- Move completed/outdated content to archive/
- Maintain README.md links to important archived content
- Use timestamps in archived file names
- Preserve historical context for future reference

### Quality Standards
- Keep documents under 200 lines for readability
- Use clear section headers for navigation
- Include practical examples in all technical docs
- Validate links and references quarterly

---

*This pattern ensures documentation serves both immediate development needs and long-term context preservation while remaining accessible to both human developers and AI agents.*