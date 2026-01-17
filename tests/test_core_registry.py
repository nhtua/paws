
import pytest
from paws.core.registry import Registry
from paws.core.models import AOLExtension

def test_registry_initialization_defaults():
    registry = Registry()
    extensions = registry.discover_extensions()
    # Expect Bash to be there by default
    assert any(ext.name == "Bash" for ext in extensions)

def test_registry_register_extension():
    registry = Registry()
    new_ext = AOLExtension(name="NewExt", source="remote")
    registry.register_extension(new_ext)
    
    assert registry.get_extension("NewExt") == new_ext
    assert len(registry.discover_extensions()) >= 2

def test_registry_get_extension_found():
    registry = Registry()
    ext = registry.get_extension("Bash")
    assert ext is not None
    assert ext.name == "Bash"

def test_registry_get_extension_not_found():
    registry = Registry()
    ext = registry.get_extension("NonExistent")
    assert ext is None
