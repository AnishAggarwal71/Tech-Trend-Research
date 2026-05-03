"""
State Management Module
Defines Pydantic models and graph state matching Excel schema from 03_Retail_Trends_Appendix_Workbook_Template_v2.xlsx
"""

from typing import TypedDict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import date


# ============================================================================
# PYDANTIC MODELS (Matching Excel Schema from Template 03)
# ============================================================================

class Pulse(BaseModel):
    """
    Represents one retailer activation (unique event).
    Maps to: Appendix 1 - Pulse Ledger
    """
    pulse_id: str = Field(description="Unique pulse identifier (P001, P002, ...)")
    retailer_parent: str = Field(description="Parent retailer name")
    banner_unit: Optional[str] = Field(default=None, description="Banner, format, or subsidiary")
    date_published: date = Field(description="Publication date (YYYY-MM-DD)")
    action_summary: str = Field(max_length=100, description="Summary under 100 words")
    attributes: List[str] = Field(min_length=1, max_length=3, description="1-3 coded attributes")
    primary_whispertag_id: Optional[str] = Field(default=None, description="Assigned Whisper Tag ID")
    primary_macrotrend_id: Optional[str] = Field(default=None, description="Inherited Macro Trend ID")
    source_name: str = Field(description="Publication name (Tier 1/2/3)")
    source_url: str = Field(description="Direct live URL")
    
    @field_validator('attributes')
    @classmethod
    def validate_attributes_count(cls, v):
        if not (1 <= len(v) <= 3):
            raise ValueError("Must have 1-3 attributes")
        return v


class WhisperTag(BaseModel):
    """
    Micro-trend cluster of pulses showing repeated mechanism.
    Maps to: Appendix 2 - Whisper Tags
    """
    whispertag_id: str = Field(description="Unique tag ID (WT01, WT02, ...)")
    whispertag_name: str = Field(description="Plain English name")
    primary_macrotrend_id: Optional[str] = Field(
        default="Unassigned",
        description="Assigned Macro Trend ID or 'Unassigned'"
    )
    micro_story: str = Field(
        min_length=50,
        max_length=120,
        description="Evidence-led story (50-120 words)"
    )
    pulse_ids_used: List[str] = Field(min_length=4, description="Minimum 4 pulse IDs")
    dominant_mechanism: str = Field(description="Core repeated mechanism")
    
    # For validation tracking
    distinct_retailers: List[str] = Field(default_factory=list, description="Distinct parent retailers")
    
    @field_validator('pulse_ids_used')
    @classmethod
    def validate_pulse_threshold(cls, v):
        if len(v) < 4:
            raise ValueError("Whisper Tag requires minimum 4 pulses")
        return v
    
    def validate_retailer_threshold(self) -> bool:
        """Check if >=3 distinct retailers"""
        return len(set(self.distinct_retailers)) >= 3


class MacroTrend(BaseModel):
    """
    High-level trend synthesized from Whisper Tags.
    Maps to: Appendix 3 - Macro Trend Map
    """
    macrotrend_id: str = Field(description="Unique Macro ID (MT01-MT06)")
    macrotrend_name: str = Field(
        min_length=3,
        max_length=6,
        description="3-6 words, country-specific, mechanism-based"
    )
    whispertag_ids_used: List[str] = Field(min_length=3, description="Minimum 3 Whisper Tags")
    proofpoint_pulse_ids: List[str] = Field(
        min_length=5,
        max_length=8,
        description="Top 5-8 proof points (max 2 per retailer)"
    )
    narrative: str = Field(max_length=300, description="What is changing (up to 300 words)")
    key_drivers: List[str] = Field(
        min_length=2,
        max_length=4,
        description="2-4 evidence-only drivers"
    )
    
    # For validation tracking
    total_pulses: int = Field(default=0, description="Aggregate pulse count")
    distinct_retailers: List[str] = Field(default_factory=list, description="Distinct retailers")
    
    @field_validator('whispertag_ids_used')
    @classmethod
    def validate_whispertag_threshold(cls, v):
        if len(v) < 3:
            raise ValueError("Macro Trend requires minimum 3 Whisper Tags")
        return v
    
    def validate_thresholds(self) -> bool:
        """Check if >=8 pulses and >=5 retailers"""
        return self.total_pulses >= 8 and len(set(self.distinct_retailers)) >= 5


class CIPHERRegrouping(BaseModel):
    """
    Secondary lens regrouping Whisper Tags through CIPHER.
    Maps to: Appendix 4 - Whisper Tag CIPHER Map
    """
    whispertag_id: str
    whispertag_name: str
    primary_cipher_bucket: Literal[
        "Contradictions",
        "Inflections",
        "Practices",
        "Hacks",
        "Extremes",
        "Rarities"
    ]
    why_assigned: str = Field(description="Evidence-only reason for bucket assignment")


class AttributeLedRegrouping(BaseModel):
    """
    Secondary lens regrouping Whisper Tags through attributes.
    Maps to: Appendix 5 - Whisper Tag Attribute-led Map
    """
    whispertag_id: str
    whispertag_name: str
    attribute_led_macro_name: str = Field(description="Cleaner macro name for bucket")
    linked_attribute_buckets: List[str] = Field(description="Originating attribute(s)")
    why_assigned: str = Field(description="Story the bucket tells")


class TechTrend(BaseModel):
    """
    Technology trend extracted from pulses (NOT Whisper Tags).
    Maps to: Appendix 6 - Technology Trend Map
    """
    techtrend_id: str = Field(description="Unique tech trend ID (TT01, TT02, ...)")
    techtrend_name: str = Field(description="Technology trend name")
    primary_cipher_bucket: Literal[
        "Contradictions",
        "Inflections",
        "Practices",
        "Hacks",
        "Extremes",
        "Rarities"
    ]
    pulse_ids_used: List[str] = Field(description="Tech-eligible pulse IDs")
    evidence_readout: str = Field(
        max_length=200,
        description="1-2 sentence evidence-only readout"
    )
    source_urls: List[str] = Field(description="Source URLs from pulses")
    retailer_breadth: int = Field(default=0, description="Number of distinct retailers")


class RetailerStructureMap(BaseModel):
    """
    Coverage control map for banners, formats, subsidiaries.
    Helper structure (not in main appendix but referenced in methodology)
    """
    parent_retailer: str
    country: str
    banners: List[str] = Field(default_factory=list)
    formats: List[str] = Field(default_factory=list)
    owned_brands: List[str] = Field(default_factory=list)
    key_subsidiaries: List[str] = Field(default_factory=list)


class FalsificationRecord(BaseModel):
    """
    Counter-evidence that narrows/drops weak tags or Macro Trends.
    Maps to: Falsification_Log sheet
    """
    item_type: Literal["WhisperTag", "MacroTrend"]
    item_id: str
    counter_evidence: str
    source_name: str
    source_url: str
    action_taken: Literal["Narrowed", "Dropped", "Retained"]
    rationale: str


class QACheckItem(BaseModel):
    """
    Individual QA validation check.
    Maps to: QA_Check sheet
    """
    check_number: int = Field(ge=1, le=11, description="QA checklist item number (1-11)")
    check_description: str
    status: Literal["Pass", "Fail", "Warning"]
    notes: Optional[str] = None


# ============================================================================
# GRAPH STATE (TypedDict for LangGraph)
# ============================================================================

class AgentState(TypedDict):
    """
    Complete state passed through the LangGraph workflow.
    Holds inputs, intermediate data, and final formatted outputs.
    """
    
    # ========== INPUTS (from run parameters) ==========
    country: str
    timeline_start: date
    timeline_end: date
    retailers_in_scope: List[str]
    
    # ========== RAW RESEARCH DATA ==========
    raw_articles: List[str]  # Mocked web scraping results
    
    # ========== RETAILER STRUCTURE MAPPING ==========
    retailer_structure_maps: List[RetailerStructureMap]
    
    # ========== CORE DATA MODELS (matching Excel schema) ==========
    pulses: List[Pulse]  # Exactly 100 pulses
    whisper_tags: List[WhisperTag]  # Up to 30 tags
    macro_trends: List[MacroTrend]  # Exactly 6 Macro Trends
    
    # ========== SECONDARY REGROUPINGS ==========
    cipher_regroupings: List[CIPHERRegrouping]
    attribute_regroupings: List[AttributeLedRegrouping]
    
    # ========== TECHNOLOGY TRENDS (separate pulse-only pass) ==========
    tech_trends: List[TechTrend]
    
    # ========== UNASSIGNED ITEMS ==========
    unassigned_whispertags: List[dict]  # {"name": str, "reason": str}
    
    # ========== VALIDATION & QA ==========
    falsification_records: List[FalsificationRecord]
    qa_checks: List[QACheckItem]
    qa_passed: bool
    
    # ========== FORMATTED OUTPUTS ==========
    excel_dataframes: dict  # Prepared DataFrames for Excel export
    front_section_markdown: str  # Executive readout following 02.md format
    
    # ========== ERROR TRACKING ==========
    errors: List[str]
    warnings: List[str]


# ============================================================================
# ATTRIBUTE LIBRARY (from methodology 01.md)
# ============================================================================

ATTRIBUTE_KEYWORDS = [
    "AI Operations",
    "Emerging capabilities",
    "Network operations",
    "Workforce Operations",
    "Sustainable operations",
    "Belonging among groups",
    "B2B service partnerships",
    "B2C Service partnerships",
    "Fulfillment partnerships",
    "Other Partnerships",
    "Investment activity",
    "Disinvestments",
    "Corporate governance",
    "Digital Stores",
    "Loyalty",
    "Pricing & promotion",
    "Physical stores",
    "Owned Brands",
    "Marketplaces"
]

CIPHER_BUCKETS = [
    "Contradictions",
    "Inflections",
    "Practices",
    "Hacks",
    "Extremes",
    "Rarities"
]

SOURCE_TIERS = {
    "Tier1": [
        "Official websites", "Retailer websites", "Brand websites",
        "Official press releases", "Investor presentations",
        "Corporate newsrooms", "Company reports",
        "Government reports", "Central bank reports", "Statistical agencies"
    ],
    "Tier2": [
        "Wall Street Journal", "Financial Times", "Reuters", "Bloomberg",
        "The Economist", "CNBC", "Business Insider", "Retail Dive",
        "The Information", "Wired", "TechCrunch", "The Verge",
        "Modern Retail", "Grocery Dive", "Supply Chain Dive", "Ad Age"
    ],
    "Tier3": [
        "Bain", "BCG", "McKinsey", "EY", "PwC", "KPMG", "Deloitte",
        "Coresight Research", "Chain Store Age", "NRF", "Shoptalk",
        "Kirk Palmer Associates", "Eye on Retail"
    ]
}

PROHIBITED_SOURCES = [
    "Wikipedia", "Quora", "third-party blogs", "personal blogs",
    "vlogs", "Reddit", "social media", "forums", "user-generated content"
]