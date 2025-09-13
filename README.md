# Zenith Framework Documentation

[![Built with Starlight](https://astro.badg.es/v2/built-with-starlight/tiny.svg)](https://starlight.astro.build)

This is the documentation site for the Zenith web framework, built with Astro Starlight.

## 🚀 Development

To work on the documentation:

```bash
cd docs
npm install
npm run dev
```

The site will be available at `http://localhost:4321`.

## 📁 Content Structure

Documentation content is organized in `src/content/docs/`:

```
src/content/docs/
├── index.mdx                  # Homepage
├── installation.md            # Installation guide
├── introduction.md            # Framework introduction
├── quick-start.mdx           # Getting started guide
├── project-structure.mdx     # Project organization
├── api/                      # API reference
├── concepts/                 # Core concepts
├── examples/                 # Usage examples
├── guides/                   # How-to guides
└── reference/                # Technical reference
```

## 🧞 Commands

All commands should be run from the `docs/` directory:

| Command                   | Action                                           |
| :------------------------ | :----------------------------------------------- |
| `npm install`             | Installs dependencies                            |
| `npm run dev`             | Starts local dev server at `localhost:4321`      |
| `npm run build`           | Build production site to `./dist/`              |
| `npm run preview`         | Preview build locally                            |
| `npm run astro ...`       | Run CLI commands like `astro add`, `astro check` |
| `npm run astro -- --help` | Get help using the Astro CLI                     |

## 📝 Writing Documentation

- Use `.mdx` for pages that need React components
- Use `.md` for simple markdown content
- All pages should have proper frontmatter with title and description
- Include code examples for all API documentation
- Test all code examples to ensure they work

## 🔗 Useful Links

- [Starlight Documentation](https://starlight.astro.build/)
- [Astro Documentation](https://docs.astro.build)
- [Zenith Framework Repository](https://github.com/nijaru/zenith)