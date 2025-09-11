"""
Interactive shell for Zenith framework.

Provides an IPython shell with application context pre-loaded.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any


def create_shell_namespace(app_path: str | None = None) -> dict[str, Any]:
    """
    Create namespace for interactive shell with commonly used imports.
    
    Returns:
        Dictionary of name -> object mappings for shell namespace
    """
    import_errors = []
    namespace = {}
    
    # Core framework imports
    try:
        from zenith import Zenith, Config, Router, Context
        namespace.update({
            'Zenith': Zenith,
            'Config': Config,
            'Router': Router,
            'Context': Context,
        })
    except ImportError as e:
        import_errors.append(f"Core imports: {e}")
    
    # Database imports
    try:
        from zenith.db import Database, SQLModel, Field
        from zenith.db.migrations import MigrationManager
        namespace.update({
            'Database': Database,
            'SQLModel': SQLModel,
            'Field': Field,
            'MigrationManager': MigrationManager,
        })
    except ImportError as e:
        import_errors.append(f"Database imports: {e}")
    
    # Web utilities
    try:
        from zenith.web import metrics, health_manager
        namespace.update({
            'metrics': metrics,
            'health_manager': health_manager,
        })
    except ImportError as e:
        import_errors.append(f"Web imports: {e}")
    
    # Try to import user's app
    if app_path:
        try:
            # Add current directory to path
            sys.path.insert(0, str(Path.cwd()))
            
            # Try common app locations
            app = None
            for module_path in [app_path, 'main.app', 'app.app', 'main.application']:
                try:
                    module_name, attr_name = module_path.rsplit('.', 1)
                    module = __import__(module_name, fromlist=[attr_name])
                    app = getattr(module, attr_name)
                    namespace['app'] = app
                    print(f"✅ Loaded app from {module_path}")
                    break
                except (ImportError, AttributeError):
                    continue
            
            if not app:
                print(f"⚠️  Could not load app from {app_path}")
                print("   Use --app to specify: zen shell --app mymodule.app")
        except Exception as e:
            print(f"⚠️  Error loading app: {e}")
    
    # Try to import models and contexts from current project
    try:
        # Import all models if they exist
        from pathlib import Path
        models_path = Path.cwd() / "models"
        if models_path.exists():
            sys.path.insert(0, str(Path.cwd()))
            for model_file in models_path.glob("*.py"):
                if model_file.name != "__init__.py":
                    module_name = f"models.{model_file.stem}"
                    try:
                        module = __import__(module_name, fromlist=['*'])
                        # Import all uppercase names (likely models)
                        for name in dir(module):
                            if name[0].isupper() and not name.startswith('_'):
                                namespace[name] = getattr(module, name)
                    except ImportError:
                        pass
    except Exception:
        pass
    
    # Try to import contexts
    try:
        contexts_path = Path.cwd() / "contexts"
        if contexts_path.exists():
            for context_file in contexts_path.glob("*.py"):
                if context_file.name != "__init__.py":
                    module_name = f"contexts.{context_file.stem}"
                    try:
                        module = __import__(module_name, fromlist=['*'])
                        # Import all Context classes
                        for name in dir(module):
                            if name.endswith('Context') or name.endswith('Service'):
                                namespace[name] = getattr(module, name)
                    except ImportError:
                        pass
    except Exception:
        pass
    
    # Async helper functions
    namespace['run'] = asyncio.run
    namespace['create_task'] = asyncio.create_task
    namespace['gather'] = asyncio.gather
    
    # Add performance profiling utilities
    try:
        from zenith.performance import track_performance, profile_block
        namespace.update({
            'track_performance': track_performance,
            'profile_block': profile_block,
        })
    except ImportError:
        pass
    
    if import_errors:
        print("⚠️  Some imports failed:")
        for error in import_errors:
            print(f"   - {error}")
    
    return namespace


def run_shell(app_path: str | None = None, use_ipython: bool = True) -> None:
    """
    Start interactive shell with Zenith context.
    
    Args:
        app_path: Import path to application (e.g., 'main.app')
        use_ipython: Whether to use IPython if available
    """
    print("🚀 Starting Zenith interactive shell...")
    print("")
    
    # Create namespace
    namespace = create_shell_namespace(app_path)
    
    # Print what's available
    print("📦 Available imports:")
    categories = {
        'Framework': ['Zenith', 'Config', 'Router', 'Context'],
        'Database': ['Database', 'SQLModel', 'Field', 'MigrationManager'],
        'Web': ['metrics', 'health_manager'],
        'Async': ['run', 'create_task', 'gather'],
        'Profiling': ['track_performance', 'profile_block'],
    }
    
    for category, items in categories.items():
        available = [item for item in items if item in namespace]
        if available:
            print(f"   {category}: {', '.join(available)}")
    
    # Print loaded models/contexts
    models = [name for name in namespace if name[0].isupper() and not name in ['Zenith', 'Config', 'Router', 'Context', 'Database', 'SQLModel', 'Field', 'MigrationManager']]
    if models:
        print(f"   Models/Contexts: {', '.join(models[:5])}{' ...' if len(models) > 5 else ''}")
    
    if 'app' in namespace:
        print(f"   App: app (your application instance)")
    
    print("")
    print("💡 Tips:")
    print("   - Use run() to execute async functions: run(my_async_func())")
    print("   - Use await directly in IPython for async calls")
    print("   - Use track_performance() or profile_block() to measure performance")
    print("")
    
    # Try IPython first
    if use_ipython:
        try:
            from IPython import start_ipython
            from IPython.terminal.ipapp import TerminalIPythonApp
            
            # Configure IPython for async
            config = TerminalIPythonApp.instance().config
            config.TerminalInteractiveShell.autoawait = True
            
            start_ipython(argv=[], user_ns=namespace)
            return
        except ImportError:
            print("ℹ️  IPython not found, using standard Python shell")
            print("   Install with: pip install ipython")
            print("")
    
    # Fallback to standard Python shell
    import code
    
    # Enable async in standard shell (Python 3.8+)
    try:
        import asyncio
        import types
        
        # Create async REPL
        console = code.InteractiveConsole(namespace)
        
        # Monkey-patch to support await
        original_runsource = console.runsource
        
        def async_runsource(source, filename="<console>", symbol="single"):
            # Check if source contains await
            if 'await' in source:
                # Wrap in async function and run
                async_source = f"async def __async_runner():\n"
                for line in source.split('\n'):
                    async_source += f"    {line}\n"
                async_source += "asyncio.run(__async_runner())"
                return original_runsource(async_source, filename, symbol)
            return original_runsource(source, filename, symbol)
        
        console.runsource = async_runsource
        console.interact(banner="Python shell with Zenith context (use 'exit()' to quit)")
    except Exception:
        # Ultimate fallback
        code.interact(banner="Python shell with Zenith context", local=namespace)