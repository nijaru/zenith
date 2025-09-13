// Custom Vite plugin to add crossorigin="anonymous" to modulepreload links
export function crossoriginPlugin() {
  return {
    name: 'crossorigin-modulepreload',
    generateBundle(options, bundle) {
      // Find HTML files and add crossorigin to modulepreload links
      Object.keys(bundle).forEach(fileName => {
        const chunk = bundle[fileName];
        if (chunk.type === 'asset' && fileName.endsWith('.html')) {
          // Add crossorigin="anonymous" to all modulepreload links
          chunk.source = chunk.source.replace(
            /<link\s+rel="modulepreload"\s+href="[^"]+"/g,
            (match) => {
              if (match.includes('crossorigin')) {
                return match; // Already has crossorigin
              }
              return match.replace('href="', 'crossorigin="anonymous" href="');
            }
          );
        }
      });
    },
    transformIndexHtml: {
      enforce: 'post',
      transform(html) {
        // Also transform during development
        return html.replace(
          /<link\s+rel="modulepreload"\s+href="[^"]+"/g,
          (match) => {
            if (match.includes('crossorigin')) {
              return match;
            }
            return match.replace('href="', 'crossorigin="anonymous" href="');
          }
        );
      }
    }
  };
}