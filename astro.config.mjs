// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
	site: 'https://nijaru.com',
	base: '/zenith',
	integrations: [
		starlight({
			title: 'Zenith',
			description: 'Modern Python web framework with clean architecture and exceptional performance',
			logo: {
				light: './src/assets/zenith-logo.svg',
				dark: './src/assets/zenith-logo.svg',
				replacesTitle: false,
			},
			defaultTheme: 'dark',
			social: [
				{ icon: 'github', label: 'GitHub', href: 'https://github.com/nijaru/zenith' },
				{ icon: 'x.com', label: 'Twitter', href: 'https://twitter.com/zenithframework' },
				{ icon: 'discord', label: 'Discord', href: 'https://discord.gg/zenith' },
			],
			editLink: {
				baseUrl: 'https://github.com/nijaru/zenith/edit/main/docs-new/',
			},
			customCss: [
				'./src/styles/custom.css',
			],
			sidebar: [
				{
					label: 'Getting Started',
					items: [
						{ label: 'Introduction', slug: 'introduction' },
						{ label: 'Installation', slug: 'installation' },
						{ label: 'Quick Start', slug: 'quick-start' },
						{ label: 'Project Structure', slug: 'project-structure' },
					],
				},
				{
					label: 'Core Concepts',
					items: [
						{ label: 'Application', slug: 'concepts/application' },
						{ label: 'Context System', slug: 'concepts/contexts' },
						{ label: 'Routing', slug: 'concepts/routing' },
						{ label: 'Middleware', slug: 'concepts/middleware' },
						{ label: 'Dependency Injection', slug: 'concepts/dependency-injection' },
					],
				},
				{
					label: 'Database',
					items: [
						{ label: 'SQLModel Integration', slug: 'database/sqlmodel' },
						{ label: 'Migrations', slug: 'database/migrations' },
						{ label: 'Query Patterns', slug: 'database/queries' },
						{ label: 'Relationships', slug: 'database/relationships' },
					],
				},
				{
					label: 'Features',
					items: [
						{ label: 'Authentication', slug: 'features/authentication' },
						{ label: 'Background Tasks', slug: 'features/background-tasks' },
						{ label: 'WebSockets', slug: 'features/websockets' },
						{ label: 'File Uploads', slug: 'features/file-uploads' },
						{ label: 'SPA Serving', slug: 'features/spa-serving' },
						{ label: 'Testing', slug: 'features/testing' },
					],
				},
				{
					label: 'Deployment',
					items: [
						{ label: 'Docker', slug: 'deployment/docker' },
						{ label: 'Production Config', slug: 'deployment/production' },
						{ label: 'Environment Variables', slug: 'deployment/environment' },
						{ label: 'Monitoring', slug: 'deployment/monitoring' },
						{ label: 'Performance', slug: 'deployment/performance' },
					],
				},
				{
					label: 'API Reference',
					autogenerate: { directory: 'api' },
				},
			],
			defaultLocale: 'en',
			lastUpdated: true,
			pagination: true,
			tableOfContents: {
				minHeadingLevel: 2,
				maxHeadingLevel: 3,
			},
		}),
	],
});