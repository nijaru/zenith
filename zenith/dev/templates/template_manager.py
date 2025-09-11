"""
Template manager for CLI project generation.

Handles loading, caching, and rendering templates with variable substitution.
"""

import importlib.resources
from pathlib import Path
from string import Template
from typing import Any
from dataclasses import dataclass


@dataclass
class TemplateContext:
    """Context for template variable substitution."""
    project_name: str
    secret_key: str
    db: str
    template_type: str  # "api" or "web"


class TemplateManager:
    """
    Manages CLI templates for project generation.
    
    Uses string.Template for variable substitution and importlib.resources
    for proper package bundling.
    """
    
    def __init__(self):
        self._template_cache: dict[str, Template] = {}
    
    def _load_template(self, template_name: str) -> Template:
        """Load template from resources with caching."""
        if template_name in self._template_cache:
            return self._template_cache[template_name]
        
        try:
            # Load template from package resources
            template_text = importlib.resources.read_text(
                "zenith.dev.templates", 
                f"{template_name}.template"
            )
            template = Template(template_text)
            self._template_cache[template_name] = template
            return template
        except FileNotFoundError:
            raise ValueError(f"Template '{template_name}' not found")
    
    def render_template(self, template_name: str, context: TemplateContext) -> str:
        """Render template with provided context variables."""
        template = self._load_template(template_name)
        
        # Compute template description based on type
        template_descriptions = {
            "web": "Full-stack web application",
            "api": "Production-ready API"
        }
        
        # Convert context to dict for substitution
        variables = {
            "project_name": context.project_name,
            "secret_key": context.secret_key,
            "db": context.db,
            "template_type": context.template_type,
            "template_description": template_descriptions.get(context.template_type, "Zenith application"),
        }
        
        return template.safe_substitute(**variables)
    
    def get_app_template(self, template_type: str) -> str:
        """Get the appropriate app.py template."""
        if template_type == "web":
            return "app_web"
        else:
            return "app_api"
    
    def get_all_templates_for_type(self, template_type: str) -> dict[str, str]:
        """Get all required template names for a project type."""
        base_templates = {
            "app.py": self.get_app_template(template_type),
            ".env": "env",
            ".gitignore": "gitignore", 
            "requirements.txt": "requirements",
            "requirements-dev.txt": "requirements_dev",
            "tests/test_app.py": "test_app",
            "README.md": "readme",
        }
        
        # Add web-specific templates
        if template_type == "web":
            base_templates.update({
                "templates/base.html": "html_base",
                "templates/index.html": "html_index", 
                "templates/about.html": "html_about",
                "static/css/main.css": "css_main",
            })
        
        return base_templates