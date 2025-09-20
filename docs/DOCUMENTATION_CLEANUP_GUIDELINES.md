# Documentation Cleanup Guidelines

## What to Remove

### 1. Marketing Language
- **Percentages**: "85% less", "80% reduction", "100x faster"
- **Superlatives**: "exceptional", "revolutionary", "game-changing", "unprecedented"
- **Emotional appeals**: "developer joy", "happiness", "amazing", "incredible"
- **Hype words**: "supercharge", "blazing fast", "lightning", "rocket"
- **Overselling**: "eliminate", "zero", "never", "always"

### 2. Excessive Punctuation & Emojis
- **Multiple exclamation marks**: "!!!"
- **Emojis in code comments**: ❌, ✅, 🚀, 🔥, ⚡ (keep ⚡ only in title)
- **Emojis in prose**: Remove unless absolutely necessary
- **Dramatic punctuation**: "!" at end of feature descriptions

### 3. Unprofessional Patterns
- **"Zero-config"** → "Automatic configuration"
- **"One-liner"** → "Built-in" or "Single method"
- **"Boilerplate"** → "Configuration" or "Setup code"
- **"Enhanced DX"** → "Developer tools" or specific features
- **"Modern"** → Remove or use "Current"
- **"Intuitive"** → Let code speak for itself

## What to Replace With

### Professional Alternatives
| Instead of | Use |
|------------|-----|
| "85% less boilerplate" | "Reduced configuration" |
| "Exceptional performance" | "High performance" or specific metrics |
| "Developer joy" | Remove entirely |
| "Zero-config setup" | "Automatic configuration" |
| "One-liner features" | "Built-in methods" |
| "Eliminates X" | "Reduces X" or "Handles X" |
| "Revolutionary" | "New" or feature description |
| "Blazing fast" | Specific performance metrics |

### Tone Guidelines

1. **Be Factual**: State what the framework does, not how amazing it is
2. **Be Technical**: Use precise technical terms
3. **Be Modest**: Let features speak for themselves
4. **Be Specific**: Use numbers and examples, not adjectives
5. **Be Professional**: Write like Django/Rails/FastAPI docs

## Code Comment Standards

### Remove
```python
# ❌ Business logic mixed with web layer
# ✅ Clean separation of concerns
# 🚀 Super fast performance!
# 🔥 This is amazing!
```

### Replace With
```python
# Business logic mixed with web layer
# Clean separation of concerns
# Optimized for performance
# Efficient implementation
```

## Example Transformations

### Before
```markdown
## 🚀 Revolutionary Zero-Config Setup!!!

Zenith delivers an exceptional developer experience with 85% less boilerplate!
Our one-liner features eliminate tedious setup and maximize developer joy!
```

### After
```markdown
## Automatic Configuration

Zenith includes automatic configuration with sensible defaults.
Built-in methods handle common setup tasks.
```

## Checklist for Each Page

- [ ] Remove percentage claims
- [ ] Remove superlatives and hype words
- [ ] Remove excessive exclamation marks
- [ ] Remove emojis from code and most prose
- [ ] Replace marketing terms with technical terms
- [ ] Ensure professional, factual tone
- [ ] Check code comments are professional
- [ ] Verify examples are realistic
- [ ] Remove promises, focus on features
- [ ] Match tone of FastAPI/Django docs