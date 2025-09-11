// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
	site: 'https://nijaru.com',
	base: '/zenith',
	integrations: [
		starlight({
			title: '⚡ Zenith',
			description: 'Modern Python web framework with clean architecture and exceptional performance',
			social: [
				{ icon: 'github', label: 'GitHub', href: 'https://github.com/nijaru/zenith' },
			],
			editLink: {
				baseUrl: 'https://github.com/nijaru/zenith/edit/main/docs/',
			},
			credits: false,
			head: [
				{
					tag: 'link',
					attrs: {
						rel: 'icon',
						href: 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"%3E%3Ctext y=".9em" font-size="90"%3E⚡%3C/text%3E%3C/svg%3E',
					},
				},
			],
			customCss: [
				'./src/styles/custom.css',
			],
			components: {
				ThemeSelect: './src/components/overrides/ThemeSelect.astro',
			},
			pagefind: false,
			tableOfContents: { minHeadingLevel: 2, maxHeadingLevel: 4 },
			pagination: true,
			sidebar: [
				{
					label: 'Getting Started',
					collapsed: false,
					items: [
						{ label: 'Introduction', link: '/introduction' },
						{ label: 'Installation', link: '/installation' },
						{ label: 'Quick Start', link: '/quick-start' },
						{ label: 'Project Structure', link: '/project-structure' },
					],
				},
				{
					label: 'Core Concepts',
					collapsed: false,
					items: [
						{ label: 'Context System', link: '/concepts/contexts' },
						{ label: 'Routing', link: '/concepts/routing' },
						{ label: 'Middleware', link: '/concepts/middleware' },
						{ label: 'Database', link: '/concepts/database' },
						{ label: 'Authentication', link: '/concepts/authentication' },
					],
				},
				{
					label: 'Examples',
					collapsed: false,
					items: [
						{ label: 'Hello World', link: '/examples/hello-world' },
						{ label: 'Basic Routing', link: '/examples/basic-routing' },
						{ label: 'File Upload', link: '/examples/file-upload' },
						{ label: 'WebSocket Chat', link: '/examples/websocket-chat' },
						{ label: 'Blog API', link: '/examples/blog-api' },
						{ label: 'Chat Application', link: '/examples/chat' },
						{ label: 'Full-Stack SPA', link: '/examples/fullstack-spa' },
					],
				},
				{
					label: 'API Reference',
					collapsed: false,
					items: [
						{ label: 'Application', link: '/api/application' },
						{ label: 'Context', link: '/api/context' },
						{ label: 'Router', link: '/api/router' },
						{ label: 'Middleware', link: '/api/middleware' },
						{ label: 'Testing', link: '/api/testing' },
					],
				},
			],
		}),
	],
});