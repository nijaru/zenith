// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
	output: 'static',
	site: 'https://zenith.nijaru.com',
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
					tag: 'meta',
					attrs: {
						name: 'cf-settings',
						content: 'rocket_loader:off'
					}
				},
				{
					tag: 'link',
					attrs: {
						rel: 'icon',
						href: 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"%3E%3Ctext y=".9em" font-size="90"%3E⚡%3C/text%3E%3C/svg%3E',
					},
				},
				{
					tag: 'script',
					attrs: {
						src: '/zenith/zenith-console.js',
						'data-cfasync': 'false',
						defer: true
					},
				},
			],
			customCss: [
				'./src/styles/custom.css',
			],
			components: {
				ThemeSelect: './src/components/overrides/ThemeSelect.astro',
			},
			sidebar: [
				{
					label: 'Start Here',
					items: [
						{ label: 'Introduction', link: '/introduction/' },
						{ label: 'Installation', link: '/installation/' },
						{ label: 'Quick Start', link: '/quick-start/' },
						{ label: 'Project Structure', link: '/project-structure/' },
					],
				},
				{
					label: 'Concepts',
					autogenerate: { directory: 'concepts' },
				},
				{
					label: 'API Reference',
					autogenerate: { directory: 'api' },
				},
				{
					label: 'Examples',
					items: [
						{ label: 'Overview', link: '/examples/' },
						{ label: 'Modern DX', link: '/examples/modern-dx/' },
						{ label: 'One-liner Features', link: '/examples/one-liner-features/' },
						{ label: 'Auto-generated', link: '/examples/auto-generated/' },
					],
				},
				{
					label: 'Guides',
					autogenerate: { directory: 'guides' },
				},
			],
		}),
	],
	// Examples auto-generated via package.json build script
});