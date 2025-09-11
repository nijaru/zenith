"""
Base code generator class.
"""

import re
from typing import Any


class CodeGenerator:
    """Base class for code generators."""
    
    def __init__(self, name: str, **options):
        self.name = name
        self.options = options
        self.class_name = self._to_class_name(name)
        self.variable_name = self._to_variable_name(name)
        self.table_name = self._to_table_name(name)
    
    def _to_class_name(self, name: str) -> str:
        """Convert to PascalCase class name."""
        # user_profile -> UserProfile
        parts = name.split('_')
        return ''.join(part.capitalize() for part in parts)
    
    def _to_variable_name(self, name: str) -> str:
        """Convert to snake_case variable name."""
        # UserProfile -> user_profile
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _to_table_name(self, name: str) -> str:
        """Convert to plural table name."""
        variable = self._to_variable_name(name)
        # Simple pluralization
        if variable.endswith('y'):
            return variable[:-1] + 'ies'
        elif variable.endswith('s'):
            return variable + 'es'
        else:
            return variable + 's'
    
    def generate(self) -> dict[str, str]:
        """Generate code files. Returns dict of path -> content."""
        raise NotImplementedError