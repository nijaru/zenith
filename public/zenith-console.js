// Zenith Framework Developer Console
if (typeof console !== 'undefined' && console.log) {
	const zenithStyle = 'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 4px 8px; border-radius: 3px; font-weight: bold;';
	const versionStyle = 'color: #667eea; font-weight: bold;';
	const linkStyle = 'color: #764ba2; text-decoration: underline;';

	console.log('%c⚡ Zenith Framework %cv0.3.0', zenithStyle, versionStyle);
	console.log('🚀 Modern Python web framework with clean architecture');
	console.log('📚 Docs: %chttps://nijaru.com/zenith', linkStyle);
	console.log('💻 GitHub: %chttps://github.com/nijaru/zenith', linkStyle);
	console.log('📦 Install: pip install zenith-web');
}