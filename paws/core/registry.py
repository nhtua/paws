from typing import List, Dict, Optional
from .models import AOLExtension

class Registry:
    def __init__(self):
        self._extensions: Dict[str, AOLExtension] = {}
        # In a real system, this would scan a directory or database.
        # For PoC, we manually register the Bash extension if available.
        self._register_defaults()

    def _register_defaults(self):
        # We will register 'Bash' as a default available extension.
        # The source would point to the implementation module.
        self.register_extension(AOLExtension(
            name="Bash",
            source="paws.extensions.bash"
        ))

    def register_extension(self, extension: AOLExtension):
        self._extensions[extension.name] = extension

    def discover_extensions(self) -> List[AOLExtension]:
        return list(self._extensions.values())

    def get_extension(self, name: str) -> Optional[AOLExtension]:
        return self._extensions.get(name)
