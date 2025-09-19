"""
Generator utility functions.
"""

from pathlib import Path

from .api import APIGenerator
from .model import ModelGenerator
from .service import ServiceGenerator


def parse_field_spec(spec: str) -> dict[str, str]:
    """
    Parse field specification string.

    Examples:
        "name:str email:str age:int"
        "title:str content:text published:bool?"
    """
    fields = {}
    for field_spec in spec.split():
        if ":" in field_spec:
            name, field_type = field_spec.split(":", 1)
            fields[name] = field_type
    return fields


def generate_code(generator_type: str, name: str, **options) -> dict[str, str]:
    """
    Generate code using appropriate generator.

    Returns dict of file_path -> content.
    """
    generators = {
        "model": ModelGenerator,
        "service": ServiceGenerator,
        "api": APIGenerator,
    }

    generator_class = generators.get(generator_type)
    if not generator_class:
        raise ValueError(f"Unknown generator type: {generator_type}")

    generator = generator_class(name, **options)
    return generator.generate()


def write_generated_files(files: dict[str, str], dry_run: bool = False) -> list[str]:
    """
    Write generated files to disk.

    Returns list of created file paths.
    """
    created = []

    for path, content in files.items():
        file_path = Path(path)

        if dry_run:
            print(f"Would create: {file_path}")
            print(f"{'=' * 40}")
            print(content)
            print(f"{'=' * 40}\n")
        else:
            # Create directory if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Check if file exists
            if file_path.exists():
                print(f"⚠️  File already exists: {file_path}")
                response = input("Overwrite? (y/N): ")
                if response.lower() != "y":
                    continue

            # Write file
            file_path.write_text(content)
            created.append(str(file_path))
            print(f"✅ Created: {file_path}")

    return created
