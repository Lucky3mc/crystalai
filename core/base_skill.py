from abc import ABC, abstractmethod
import psutil

class Skill(ABC):
    name = "base_skill"
    description = "Base class for all assistant skills"
    keywords = []
    min_ram_required = 0 

    def check_requirements(self):
        """Health check before running."""
        available_ram = psutil.virtual_memory().available / (1024**3)
        if available_ram < self.min_ram_required:
            return False, f"Memory low. I need {self.min_ram_required}GB, but only have {available_ram:.2f}GB."
        return True, "OK"

    @abstractmethod
    def run(self, parameters: dict):
        """Main execution logic."""
        pass
class Skill:
    name = ""
    description = ""
    icon = ""
    supported_intents = []
