from dataclasses import dataclass, field
from enum import Enum

class FieldType(str, Enum):
    TEXT = "text"
    CHECKBOX = "checkbox"
    CHECKBOX_GROUP = "checkbox_group"
    RADIO_GROUP = "radio_group"
    DROPDOWN = "dropdown"
    DATE = "date"
    SIGNATURE_PLACEHOLDER = "signature_placeholder"
    TABLE_CELL = "table_cell"

class ResolutionMethod(str, Enum):
    EXACT_MATCH = "exact_match"
    FUZZY_MATCH = "fuzzy_match"
    LLM_SEMANTIC_MAPPING = "llm_semantic_mapping"
    LLM_GENERATED = "llm_generated"
    HUMAN_OVERRIDE = "human_override"
    LLM_FAILED = "llm_failed"

CONFIDENCE_TABLE = {
    ResolutionMethod.EXACT_MATCH: 0.98,
    ResolutionMethod.FUZZY_MATCH: 0.85,
    ResolutionMethod.LLM_SEMANTIC_MAPPING: 0.75,
    ResolutionMethod.LLM_GENERATED: 0.60,
    ResolutionMethod.HUMAN_OVERRIDE: 1.00,
    ResolutionMethod.LLM_FAILED: 0.00,
}

@dataclass
class FormField:
    id: str                      # context-path based, lihat A12 — bukan dari label
    label: str
    field_type: FieldType
    context_labels: list[str] = field(default_factory=list)  # label tetangga, untuk disambiguasi (A12)

    # lokasi dokumen — hanya salah satu grup di bawah yang terisi tergantung format
    table_index: int | None = None
    row: int | None = None
    column: int | None = None
    paragraph_index: int | None = None
    page: int | None = None
    bbox: tuple[float, float, float, float] | None = None

    # checkbox
    checkbox_kind: str | None = None   # "symbol" | "sdt" — lihat A7
    options: list[str] | None = None

    # metadata operasional
    metadata: dict = field(default_factory=dict)  # mis. {"requires_field_update": True}

    # hasil resolve
    answer: str | list[str] | None = None
    source: str | None = None          # mis. "profile.identity.full_name" atau "llm_generated"
    method: ResolutionMethod | None = None
    confidence: float = 0.0
