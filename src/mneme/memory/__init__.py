"""Phase One memory contracts and the durable interpretation boundary.

Response influence, route retrieval, identity, and adaptive learning remain
outside this package.  These exports validate source-backed residue, perform
explicit label resolution, materialize deterministic graph snapshots, and
publish an accepted interpretation atomically.
"""

from .cache import AnnotationCache, CacheError, CacheHit, CacheKey, build_cache_key
from .graph import (
    GraphConcept,
    GraphEdge,
    GraphRoute,
    GraphSnapshot,
    discover_routes,
    materialize_graph,
)
from .interpretation import (
    EXTRACTOR_VERSION,
    InterpretationError,
    InterpretationIdempotencyConflict,
    InterpretationNotReady,
    InterpretationReceipt,
    InterpretationService,
    InterpretationUncertain,
    InterpretationValidationError,
)
from .publication import (
    InterpretationPublisher,
    PublicationError,
    PublicationReceipt,
    StalePublication,
    publish_interpretation,
)
from .residue import (
    DEFAULT_ADMISSION_CONFIDENCE_THRESHOLD,
    Residue,
    ResidueValidationError,
    SourceSpan,
    canonical_json,
    normalize_label,
    validate_graph_admission,
    validate_residue,
)
from .resolution import (
    AmbiguousAliasError,
    ExplicitAliasResolver,
    ResolutionDecision,
    normalize_lookup_label,
    resolve_label,
)

__all__ = [
    "AmbiguousAliasError",
    "AnnotationCache",
    "CacheError",
    "CacheHit",
    "CacheKey",
    "DEFAULT_ADMISSION_CONFIDENCE_THRESHOLD",
    "EXTRACTOR_VERSION",
    "ExplicitAliasResolver",
    "GraphConcept",
    "GraphEdge",
    "GraphRoute",
    "GraphSnapshot",
    "discover_routes",
    "Residue",
    "ResidueValidationError",
    "ResolutionDecision",
    "SourceSpan",
    "canonical_json",
    "build_cache_key",
    "materialize_graph",
    "normalize_label",
    "normalize_lookup_label",
    "InterpretationPublisher",
    "InterpretationError",
    "InterpretationIdempotencyConflict",
    "InterpretationNotReady",
    "InterpretationReceipt",
    "InterpretationService",
    "InterpretationUncertain",
    "InterpretationValidationError",
    "PublicationError",
    "PublicationReceipt",
    "StalePublication",
    "publish_interpretation",
    "resolve_label",
    "validate_residue",
    "validate_graph_admission",
]
