/**
 * Zenith Framework Website JavaScript
 */

(function() {
    'use strict';

    // Initialize when DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
        initializeNavigation();
        initializeCodeCopy();
        initializeScrollEffects();
        initializeMobileMenu();
    });

    /**
     * Navigation functionality
     */
    function initializeNavigation() {
        // Smooth scrolling for anchor links
        const anchorLinks = document.querySelectorAll('a[href^="#"]');
        
        anchorLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                
                const targetId = this.getAttribute('href').substring(1);
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    const headerHeight = document.querySelector('.header').offsetHeight;
                    const targetPosition = targetElement.offsetTop - headerHeight - 20;
                    
                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });
                }
            });
        });

        // Active navigation highlighting
        const sections = document.querySelectorAll('section[id]');
        const navLinks = document.querySelectorAll('.nav__link[href^="#"]');

        function updateActiveNav() {
            const scrollPosition = window.scrollY + 100;

            sections.forEach(section => {
                const sectionTop = section.offsetTop;
                const sectionHeight = section.offsetHeight;
                const sectionId = section.getAttribute('id');

                if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
                    navLinks.forEach(link => {
                        link.classList.remove('active');
                        if (link.getAttribute('href') === `#${sectionId}`) {
                            link.classList.add('active');
                        }
                    });
                }
            });
        }

        window.addEventListener('scroll', updateActiveNav);
    }

    /**
     * Code copy functionality
     */
    function initializeCodeCopy() {
        // Initialize clipboard.js if available
        if (typeof ClipboardJS !== 'undefined') {
            const clipboard = new ClipboardJS('.copy-button');
            
            clipboard.on('success', function(e) {
                const button = e.trigger;
                const originalText = button.textContent;
                
                button.textContent = 'Copied!';
                button.style.backgroundColor = '#10b981'; // Success green
                
                setTimeout(() => {
                    button.textContent = originalText;
                    button.style.backgroundColor = ''; // Reset to original
                }, 2000);
                
                e.clearSelection();
            });
            
            clipboard.on('error', function(e) {
                const button = e.trigger;
                const originalText = button.textContent;
                
                button.textContent = 'Failed';
                button.style.backgroundColor = '#ef4444'; // Error red
                
                setTimeout(() => {
                    button.textContent = originalText;
                    button.style.backgroundColor = '';
                }, 2000);
            });
        }
    }

    /**
     * Scroll effects and animations
     */
    function initializeScrollEffects() {
        // Header background on scroll
        const header = document.querySelector('.header');
        
        function updateHeaderBackground() {
            if (window.scrollY > 50) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }
        }

        window.addEventListener('scroll', updateHeaderBackground);

        // Intersection Observer for fade-in animations
        if ('IntersectionObserver' in window) {
            const observerOptions = {
                threshold: 0.1,
                rootMargin: '0px 0px -50px 0px'
            };

            const observer = new IntersectionObserver(function(entries) {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('animate-in');
                    }
                });
            }, observerOptions);

            // Observe elements for animation
            const animateElements = document.querySelectorAll('.feature, .example, .install-step');
            animateElements.forEach(el => {
                el.classList.add('animate-on-scroll');
                observer.observe(el);
            });
        }
    }

    /**
     * Mobile menu functionality
     */
    function initializeMobileMenu() {
        const menuToggle = document.getElementById('nav-toggle');
        const navMenu = document.querySelector('.nav__menu');
        const body = document.body;

        if (menuToggle && navMenu) {
            menuToggle.addEventListener('click', function() {
                const isOpen = navMenu.classList.contains('open');
                
                if (isOpen) {
                    navMenu.classList.remove('open');
                    body.classList.remove('menu-open');
                    menuToggle.setAttribute('aria-expanded', 'false');
                } else {
                    navMenu.classList.add('open');
                    body.classList.add('menu-open');
                    menuToggle.setAttribute('aria-expanded', 'true');
                }
            });

            // Close menu when clicking on links
            const mobileNavLinks = navMenu.querySelectorAll('.nav__link');
            mobileNavLinks.forEach(link => {
                link.addEventListener('click', function() {
                    navMenu.classList.remove('open');
                    body.classList.remove('menu-open');
                    menuToggle.setAttribute('aria-expanded', 'false');
                });
            });

            // Close menu when clicking outside
            document.addEventListener('click', function(e) {
                if (!navMenu.contains(e.target) && !menuToggle.contains(e.target)) {
                    navMenu.classList.remove('open');
                    body.classList.remove('menu-open');
                    menuToggle.setAttribute('aria-expanded', 'false');
                }
            });
        }
    }

    /**
     * Performance monitoring (optional)
     */
    function trackPagePerformance() {
        if ('performance' in window) {
            window.addEventListener('load', function() {
                setTimeout(function() {
                    const perfData = performance.timing;
                    const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
                    
                    console.log(`Page loaded in ${pageLoadTime}ms`);
                    
                    // You could send this data to analytics here
                    // analytics.track('page_load_time', { duration: pageLoadTime });
                }, 0);
            });
        }
    }

    /**
     * Feature detection and progressive enhancement
     */
    function enhanceForModernBrowsers() {
        const html = document.documentElement;
        
        // Add classes for feature detection
        if ('scrollBehavior' in document.documentElement.style) {
            html.classList.add('smooth-scroll');
        }
        
        if ('IntersectionObserver' in window) {
            html.classList.add('intersection-observer');
        }
        
        if ('fetch' in window) {
            html.classList.add('fetch');
        }
        
        // Check for reduced motion preference
        if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            html.classList.add('reduced-motion');
        }
    }

    // Initialize enhancements
    enhanceForModernBrowsers();
    trackPagePerformance();

})();

/* Additional CSS for animations */
const animationStyles = `
<style>
.animate-on-scroll {
    opacity: 0;
    transform: translateY(20px);
    transition: opacity 0.6s ease-out, transform 0.6s ease-out;
}

.animate-on-scroll.animate-in {
    opacity: 1;
    transform: translateY(0);
}

.header.scrolled {
    background-color: rgba(255, 255, 255, 0.98);
    box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
}

/* Mobile menu styles */
@media (max-width: 768px) {
    .nav__menu {
        position: fixed;
        top: 100%;
        left: 0;
        right: 0;
        background-color: var(--color-bg);
        border-top: 1px solid var(--color-border);
        padding: var(--spacing-lg);
        transform: translateY(-100%);
        opacity: 0;
        visibility: hidden;
        transition: all var(--transition-normal);
        flex-direction: column;
        gap: var(--spacing-md);
    }
    
    .nav__menu.open {
        transform: translateY(0);
        opacity: 1;
        visibility: visible;
    }
    
    .body.menu-open {
        overflow: hidden;
    }
    
    .nav__toggle span:nth-child(1) {
        transform-origin: center;
    }
    
    .nav__toggle[aria-expanded="true"] span:nth-child(1) {
        transform: rotate(45deg) translate(5px, 5px);
    }
    
    .nav__toggle[aria-expanded="true"] span:nth-child(2) {
        opacity: 0;
    }
    
    .nav__toggle[aria-expanded="true"] span:nth-child(3) {
        transform: rotate(-45deg) translate(7px, -6px);
    }
}

/* Reduced motion support */
.reduced-motion *,
.reduced-motion *::before,
.reduced-motion *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
}
</style>
`;

// Inject additional styles
document.head.insertAdjacentHTML('beforeend', animationStyles);