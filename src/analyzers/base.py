from abc import ABC, abstractmethod
from typing import List
from src.fields.models import FormField

class AbstractAnalyzer(ABC):
    """
    Abstract base class for format-specific document layout analyzers.
    Analyzes document structures to detect empty fields, tables, paragraphs, and checkboxes.
    """
    
    @abstractmethod
    def analyze(self, file_path: str) -> List[FormField]:
        """
        Parses the document at the given file path.
        Returns a list of detected FormField objects.
        """
        pass
