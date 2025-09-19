#!/usr/bin/env node
/**
 * Auto-generate website example pages from GitHub examples
 * Eliminates duplication between examples/*.py and docs/src/content/docs/examples/
 */

import fs from 'fs/promises';
import path from 'path';

const GITHUB_API_BASE = 'https://api.github.com/repos/nijaru/zenith/contents/examples';
const EXAMPLES_DIR = 'src/content/docs/examples';
const GENERATED_DIR = path.join(EXAMPLES_DIR, 'auto-generated');

/**
 * Extract docstring and metadata from Python file content
 */
function parseExampleFile(filename, content) {
  // Extract docstring (first triple-quoted string)
  const docstringMatch = content.match(/^"""\s*([\s\S]*?)\s*"""/m);
  const docstring = docstringMatch ? docstringMatch[1].trim() : '';

  // Extract title from docstring first line or filename
  const titleMatch = docstring.match(/^(.+?)(?:\n|$)/);
  const title = titleMatch
    ? titleMatch[1].replace(/^🚀\s*|^📋\s*|^⚡\s*/, '').trim()
    : filename.replace(/^\d+-/, '').replace(/-/g, ' ').replace('.py', '');

  // Extract description (rest of docstring)
  const description = docstring.split('\n').slice(1).join('\n').trim();

  // Extract key features from docstring
  const features = [];
  const featureMatches = docstring.match(/^- (.+)$/gm);
  if (featureMatches) {
    features.push(...featureMatches.map(m => m.replace(/^- /, '')));
  }

  // Extract imports for complexity analysis
  const imports = content.match(/^from .+ import .+$/gm) || [];
  const hasDatabase = imports.some(imp => imp.includes('ZenithModel') || imp.includes('Model'));
  const hasAuth = imports.some(imp => imp.includes('Auth') || imp.includes('JWT'));
  const hasWebSocket = imports.some(imp => imp.includes('WebSocket'));

  return {
    title,
    description,
    features,
    hasDatabase,
    hasAuth,
    hasWebSocket,
    docstring,
    imports: imports.length,
    complexity: getComplexityLevel(content)
  };
}

/**
 * Determine example complexity level
 */
function getComplexityLevel(content) {
  const lines = content.split('\n').length;
  const classCount = (content.match(/^class /gm) || []).length;
  const routeCount = (content.match(/@app\.(get|post|put|delete)/g) || []).length;

  if (lines > 300 || classCount > 3 || routeCount > 10) return 'Advanced';
  if (lines > 150 || classCount > 1 || routeCount > 5) return 'Intermediate';
  return 'Beginner';
}

/**
 * Escape a string for safe use in YAML frontmatter
 */
function escapeYaml(str) {
  if (!str) return '""';

  // Escape curly braces for MDX compatibility (even in YAML frontmatter)
  str = str.replace(/{/g, '\\{').replace(/}/g, '\\}');

  // For multiline strings or strings with quotes, use literal block scalar
  if (str.includes('\n') || str.includes('"') || str.includes("'")) {
    return '|\n  ' + str.replace(/\n/g, '\n  ');
  }
  // For simple strings, just escape quotes and wrap in quotes
  return '"' + str.replace(/"/g, '\\"') + '"';
}

/**
 * Generate Astro MDX page for an example
 */
function generateExamplePage(filename, metadata, content) {
  const slug = filename.replace('.py', '');
  const number = filename.match(/^(\d+)-/)?.[1] || '00';

  return `---
title: ${escapeYaml(metadata.title)}
description: ${escapeYaml(metadata.description || 'Zenith framework example')}
---

import { Code } from '@astrojs/starlight/components';
import { Badge } from '@astrojs/starlight/components';

<div class="example-header">
  <Badge text="${metadata.complexity}" variant="${metadata.complexity === 'Beginner' ? 'success' : metadata.complexity === 'Intermediate' ? 'caution' : 'danger'}" />
  ${metadata.hasDatabase ? '<Badge text="Database" variant="note" />' : ''}
  ${metadata.hasAuth ? '<Badge text="Authentication" variant="note" />' : ''}
  ${metadata.hasWebSocket ? '<Badge text="WebSocket" variant="note" />' : ''}
</div>

## Overview

${metadata.description.replace(/{/g, '\\{').replace(/}/g, '\\}')}

${metadata.features.length > 0 ? `
## Key Features

${metadata.features.map(feature => `- ${feature.replace(/{/g, '\\{').replace(/}/g, '\\}')}`).join('\n')}
` : ''}

## Running This Example

\`\`\`bash
# Clone the repository
git clone https://github.com/nijaru/zenith.git
cd zenith

# Set required environment variable
export SECRET_KEY="your-secret-key-at-least-32-characters-long"

# Run the example
uv run python examples/${filename}
\`\`\`

## Source Code

<Code code={\`${content.replace(/`/g, '\\`').replace(/{/g, '\\{').replace(/}/g, '\\}')}\`} lang="python" title="examples/${filename}" />

## What This Example Demonstrates

${generateDemonstrationText(metadata, content).replace(/{/g, '\\{').replace(/}/g, '\\}')}

## Next Steps

- **Modify the code**: Try changing the routes or adding new features
- **Run tests**: Add test cases for your modifications
- **Explore more**: Check out other examples in the [examples directory](https://github.com/nijaru/zenith/tree/main/examples)
- **Read the docs**: Learn more about [Zenith concepts](/concepts/)

---

*This page is auto-generated from [\`examples/${filename}\`](https://github.com/nijaru/zenith/blob/main/examples/${filename}).
To suggest changes, edit the source file and the documentation will update automatically.*
`;
}

/**
 * Generate contextual demonstration text based on example content
 */
function generateDemonstrationText(metadata, content) {
  const demonstrations = [];

  if (metadata.hasDatabase) {
    demonstrations.push('**Database Integration**: ZenithModel usage with automatic session management');
  }

  if (metadata.hasAuth) {
    demonstrations.push('**Authentication**: JWT token handling and user management');
  }

  if (metadata.hasWebSocket) {
    demonstrations.push('**Real-time Communication**: WebSocket connections and message handling');
  }

  if (content.includes('app.add_auth()')) {
    demonstrations.push('**One-liner Features**: Using convenience methods for rapid development');
  }

  if (content.includes('@app.get') || content.includes('@app.post')) {
    demonstrations.push('**Route Handlers**: HTTP endpoint definition and request handling');
  }

  if (content.includes('BackgroundTasks')) {
    demonstrations.push('**Background Processing**: Asynchronous task execution');
  }

  if (demonstrations.length === 0) {
    return 'This example showcases core Zenith framework patterns and usage.';
  }

  return demonstrations.join('\n\n');
}

/**
 * Main function to generate all example pages
 */
async function generateExamplePages() {
  console.log('🚀 Generating example pages from GitHub...');

  try {
    // Fetch examples from GitHub API
    const response = await fetch(GITHUB_API_BASE);
    const files = await response.json();

    if (!Array.isArray(files)) {
      throw new Error('Failed to fetch examples from GitHub API');
    }

    // Filter Python files
    const pythonFiles = files.filter(file =>
      file.name.endsWith('.py') &&
      file.name.match(/^\d+-/) // Numbered examples only
    );

    // Create output directory
    await fs.mkdir(GENERATED_DIR, { recursive: true });

    // Generate index page
    const indexContent = generateIndexPage(pythonFiles);
    await fs.writeFile(path.join(GENERATED_DIR, 'index.mdx'), indexContent);

    // Process each example file
    for (const file of pythonFiles) {
      console.log(`📝 Processing ${file.name}...`);

      // Fetch file content
      const contentResponse = await fetch(file.download_url);
      const content = await contentResponse.text();

      // Parse and generate page
      const metadata = parseExampleFile(file.name, content);
      const pageContent = generateExamplePage(file.name, metadata, content);

      // Write page file
      const outputFile = path.join(GENERATED_DIR, file.name.replace('.py', '.mdx'));
      await fs.writeFile(outputFile, pageContent);
    }

    console.log(`✅ Generated ${pythonFiles.length} example pages`);
    console.log(`📁 Output directory: ${GENERATED_DIR}`);

  } catch (error) {
    console.error('❌ Error generating example pages:', error);
    process.exit(1);
  }
}

/**
 * Generate index page listing all examples
 */
function generateIndexPage(files) {
  const examples = files.map(file => {
    const number = file.name.match(/^(\d+)-/)?.[1] || '00';
    const title = file.name.replace(/^\d+-/, '').replace(/-/g, ' ').replace('.py', '');
    const slug = file.name.replace('.py', '');

    return { number, title, slug, filename: file.name };
  });

  // Group by category based on number ranges
  const categories = {
    'Getting Started (00-03)': examples.filter(e => parseInt(e.number) <= 3),
    'Essential Features (04-09)': examples.filter(e => parseInt(e.number) >= 4 && parseInt(e.number) <= 9),
    'Advanced Features (10-19)': examples.filter(e => parseInt(e.number) >= 10 && parseInt(e.number) <= 19),
    'Production Patterns (20+)': examples.filter(e => parseInt(e.number) >= 20),
  };

  return `---
title: Examples
description: Learn Zenith through practical examples
---

import { Card, CardGrid } from '@astrojs/starlight/components';

# Zenith Examples

Learn Zenith framework through practical, working examples. Each example builds on previous concepts while introducing new features.

${Object.entries(categories)
  .filter(([_, examples]) => examples.length > 0)
  .map(([category, examples]) => `
## ${category}

<CardGrid>
${examples.map(example => `  <Card title="${example.title}" link="./${example.slug}">
    Example ${example.number}: ${example.title}
  </Card>`).join('\n')}
</CardGrid>
`).join('\n')}

## Running Examples

All examples are available in the [GitHub repository](https://github.com/nijaru/zenith/tree/main/examples):

\`\`\`bash
# Clone and run any example
git clone https://github.com/nijaru/zenith.git
cd zenith
export SECRET_KEY="your-secret-key-at-least-32-characters-long"
uv run python examples/[example-name].py
\`\`\`

---

*This page is auto-generated from the examples directory. Each example page shows the complete source code and explanation.*
`;
}

// Run the generator
if (import.meta.url === `file://${process.argv[1]}`) {
  generateExamplePages();
}

export { generateExamplePages };