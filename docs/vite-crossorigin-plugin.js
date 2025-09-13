// Custom Vite plugin to add crossorigin="anonymous" to modulepreload links
export function crossoriginPlugin() {
  return {
    name: 'crossorigin-modulepreload',
    generateBundle(options, bundle) {
      // Find HTML files and add crossorigin to modulepreload links
      Object.keys(bundle).forEach(fileName => {
        const chunk = bundle[fileName];
        if (chunk.type === 'asset' && fileName.endsWith('.html')) {
          let html = chunk.source;

          // Add crossorigin="anonymous" to all modulepreload links
          html = html.replace(
            /<link\s+([^>]*?)rel="modulepreload"([^>]*?)>/g,
            (match, before, after) => {
              if (match.includes('crossorigin')) {
                return match; // Already has crossorigin
              }
              return `<link ${before}rel="modulepreload" crossorigin="anonymous"${after}>`;
            }
          );

          // Add data-cfasync="false" to script tags to prevent Cloudflare processing
          html = html.replace(
            /<script\s+([^>]*?)src="[^"]*\/_astro\/[^"]*"([^>]*?)>/g,
            (match, before, after) => {
              if (match.includes('data-cfasync')) {
                return match;
              }
              return `<script ${before}data-cfasync="false" src="${match.match(/src="([^"]*)"/)[1]}"${after}>`;
            }
          );

          chunk.source = html;
        }
      });
    },
    transformIndexHtml: {
      enforce: 'post',
      transform(html) {
        // Transform during development and ensure crossorigin is added
        let transformedHtml = html.replace(
          /<link\s+([^>]*?)rel="modulepreload"([^>]*?)>/g,
          (match, before, after) => {
            if (match.includes('crossorigin')) {
              return match;
            }
            return `<link ${before}rel="modulepreload" crossorigin="anonymous"${after}>`;
          }
        );

        // Add Cloudflare bypass for Astro scripts
        transformedHtml = transformedHtml.replace(
          /<script\s+([^>]*?)src="[^"]*\/_astro\/[^"]*"([^>]*?)>/g,
          (match, before, after) => {
            if (match.includes('data-cfasync')) {
              return match;
            }
            const srcMatch = match.match(/src="([^"]*)"/);
            if (srcMatch) {
              return `<script ${before}data-cfasync="false" src="${srcMatch[1]}"${after}>`;
            }
            return match;
          }
        );

        return transformedHtml;
      }
    }
  };
}