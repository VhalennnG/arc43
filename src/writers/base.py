from abc import ABC, abstractmethod
from typing import List
from src.fields.models import FormField

class DocumentWriter(ABC):
    """
    Abstract base class for format-specific document writers.
    Mutates form field values directly inside the template file.
    """

    @abstractmethod
    def fill(self, source_path: str, fields: List[FormField], output_path: str) -> None:
        """
        Loads the template document at source_path, writes the resolved field values,
        and saves the resulting document to output_path.
        
        CRITICAL RULE: Never create a new document from scratch. Always mutate the
        original template document in-place and save to the destination.
        """
        pass
