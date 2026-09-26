"""CPU-first local NLI assessor for the Phase Two semantic boundary.

This module deliberately keeps the language model's job small.  A pinned
DeBERTa NLI model scores source-window/hypothesis pairs; deterministic code
owns source coverage, windowing, aggregation, evidence binding, and the
existing ``p2-assessor-v6`` result shape.  The optional ``transformers`` and
``torch`` dependencies are imported only when the real backend is created, so
the core package remains network-free and installable without ML packages.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, cast

from ..contracts import (
    Capability,
    GenerationRequest,
    GenerationResult,
    HostCapabilities,
    HostError,
    HostFingerprint,
    TokenUsage,
)
from ..development.assessment import (
    ASSESSOR_SCHEMA_VERSION,
    AssessorMonitor,
    AssessorRequest,
    AssessorSource,
)

LOCAL_NLI_MODEL_ID = "cross-encoder/nli-deberta-v3-xsmall"
# Immutable Hugging Face commit resolved on 2026-09-26.  Callers may override
# this only when deliberately qualifying a new prospective model revision.
LOCAL_NLI_MODEL_REVISION = "a150876415327c80daeff35ca6f68f5ed8cf5c24"
LOCAL_NLI_CONFIG_SHA256 = "8d9f07bf7ba54a6fc3b1962483056f94c39dcf188db4cf61843e1c88f94b2342"
LOCAL_NLI_VERSION = "p2-local-nli-deberta-v3-xsmall-v2-real-corpus"
# Compatibility name used by the experiment harness while the assessor
# contract is versioned independently from the model fingerprint.
LOCAL_NLI_ASSESSOR_VERSION = LOCAL_NLI_VERSION
LOCAL_NLI_RUNTIME = "transformers-torch"


@dataclass(frozen=True)
class NliScores:
    """Normalized entailment/contradiction/neutral scores for one pair."""

    entailment: float
    contradiction: float
    neutral: float


class NliBackend(Protocol):
    """Minimal score-only backend used by the deterministic assessor."""

    model_id: str
    model_revision: str
    runtime_version: str

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[NliScores, ...]: ...


class PairClassifier(Protocol):
    """Tiny test/benchmark seam for deterministic or measured classifiers."""

    def predict(self, premise: str, hypothesis: str) -> tuple[float, float, float]: ...


class _ClassifierBackend:
    """Adapt the focused ``predict`` seam to the production batch interface."""

    model_id = LOCAL_NLI_MODEL_ID
    model_revision = LOCAL_NLI_MODEL_REVISION
    runtime_version = "test-classifier"

    def __init__(self, classifier: PairClassifier) -> None:
        self.classifier = classifier

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[NliScores, ...]:
        return tuple(
            NliScores(*self.classifier.predict(premise, hypothesis))
            for premise, hypothesis in pairs
        )


@dataclass(frozen=True)
class NliThresholds:
    """Conservative decision thresholds; values are qualification metadata."""

    entailment_min: float = 0.60
    contradiction_min: float = 0.60
    margin_min: float = 0.10

    def __post_init__(self) -> None:
        for name in ("entailment_min", "contradiction_min", "margin_min"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between zero and one")


@dataclass(frozen=True)
class SourceWindow:
    """A deterministic, lossless source slice sent to the NLI backend."""

    source_slot: str
    text: str
    start: int
    end: int
    chunk_index: int


def source_windows(
    source_slot: str,
    text: str,
    *,
    max_chars: int = 1800,
    overlap_chars: int = 200,
) -> tuple[SourceWindow, ...]:
    """Split long source text without silently truncating it.

    Character windows are intentionally boring and reproducible.  The model's
    tokenizer applies its own token bound inside each window; coverage remains
    explicit when this function cannot produce a complete source.
    """

    if max_chars <= 0 or overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("invalid source window bounds")
    if not isinstance(text, str) or not text:
        return ()
    windows: list[SourceWindow] = []
    start = 0
    index = 0
    step = max_chars - overlap_chars
    while start < len(text):
        end = min(len(text), start + max_chars)
        windows.append(SourceWindow(source_slot, text[start:end], start, end, index))
        if end == len(text):
            break
        start += step
        index += 1
    return tuple(windows)


def _semantic_windows(
    source_slot: str,
    text: str,
    monitor: AssessorMonitor,
    *,
    max_chars: int,
    overlap_chars: int,
) -> tuple[SourceWindow, ...]:
    """Choose bounded, proposition-focused windows before whole-source chunks.

    The prior adapter scored a long mixed conversation window.  Any unrelated
    ``would``/``planning`` language could then make a clear proposition look
    uncertain.  Sentence windows retain exact offsets and keep the specialist
    focused on the candidate's source evidence.  Long sources still fall back
    to the lossless bounded windows, so coverage is never silently truncated.
    """

    if not text:
        return ()
    all_sentences: list[SourceWindow] = []
    pattern = re.compile(r"[^.!?\n]+(?:[.!?](?:\s+|$)|\n+|$)", re.S)
    for index, match in enumerate(pattern.finditer(text)):
        sentence = match.group(0).strip()
        if not sentence:
            continue
        start = match.start() + len(match.group(0)) - len(match.group(0).lstrip())
        end = start + len(sentence)
        all_sentences.append(SourceWindow(source_slot, sentence, start, end, index))
    endpoint_sentences = [
        window for window in all_sentences if _source_mentions_proposition(window.text, monitor)
    ]
    cue_sentences = [
        window for window in all_sentences if _relation_is_expressed(window.text, monitor)
    ]
    # Markdown lists often split the subject heading from the predicate at a
    # newline.  Join adjacent bounded fragments when one carries the
    # endpoints and the other carries the relation cue.
    joined: list[SourceWindow] = []
    for index, window in enumerate(all_sentences):
        neighbors: tuple[SourceWindow, ...] = (window,)
        if index > 0:
            neighbors = (all_sentences[index - 1],) + neighbors
        if index + 1 < len(all_sentences):
            neighbors += (all_sentences[index + 1],)
        start = min(item.start for item in neighbors)
        end = max(item.end for item in neighbors)
        combined = text[start:end].strip()
        if _source_mentions_proposition(combined, monitor) and _relation_is_expressed(
            combined, monitor
        ):
            joined.append(SourceWindow(source_slot, combined, start, end, index))
    sentences = joined or endpoint_sentences or cue_sentences
    if sentences and all(len(window.text) <= max_chars for window in sentences):
        return tuple(sentences)
    return source_windows(
        source_slot,
        text,
        max_chars=max_chars,
        overlap_chars=overlap_chars,
    )


_WORD_RE = re.compile(r"[\w]+", re.UNICODE)
_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "by",
        "for",
        "from",
        "in",
        "of",
        "on",
        "the",
        "to",
        "with",
    }
)

_TERM_ALIASES = {
    "damp": "moisture",
    "moist": "moisture",
    "moisture": "moisture",
    "wet": "moisture",
    "dry": "moisture",
    "dried": "moisture",
    "potting": "soil",
    "mix": "soil",
    "wicking": "wick",
    "kept": "maintain",
    "keep": "maintain",
    "maintains": "maintain",
    "maintain": "maintain",
    "retains": "maintain",
    "retained": "maintain",
}

_RELATION_CUES = {
    "maintains": (
        "keep", "kept", "maintain", "retained", "retain", "stay", "stayed", "remain",
        "holds", "hold", "holding",
    ),
    "retains": (
        "keep", "kept", "maintain", "retains", "retained", "retain", "stay", "stayed", "remain",
        "holds", "hold", "holding",
    ),
    "causes": (
        "cause", "caused", "causes", "because", "led", "release", "released", "result"
    ),
    "raises": ("raise", "raised", "raises", "lift", "lifted", "increase", "increased"),
    "stops": ("stop", "stopped", "stops", "halt", "prevent", "prevents", "prevented"),
    "associated_with": ("associated", "related", "connected", "link", "linked"),
    "associated-with": ("associated", "related", "connected", "link", "linked"),
    "related": ("associated", "related", "connected", "link", "linked"),
    "part_of": ("part of", "component", "inside", "within", "belong", "included"),
    "part-of": ("part of", "component", "inside", "within", "belong", "included"),
    "depends_on": ("depends", "depend", "relies", "rely", "requires", "require", "contingent"),
    "depends-on": ("depends", "depend", "relies", "rely", "requires", "require", "contingent"),
    "supports": ("supports", "support", "helps", "help", "enables", "enable", "keeps", "keep"),
    "prevents": ("prevents", "prevent", "reduces", "reduce", "slows", "slow", "avoids", "avoid"),
}

_RELATION_TEMPLATES = {
    "causes": "{from_} causes {to}.",
    "caused_by": "{from_} is caused by {to}.",
    "caused-by": "{from_} is caused by {to}.",
    "depends_on": "{from_} depends on {to}.",
    "depends-on": "{from_} depends on {to}.",
    "dependency": "{from_} depends on {to}.",
    "part_of": "{from_} is part of {to}.",
    "part-of": "{from_} is part of {to}.",
    "retains": "{from_} retains {to}.",
    "maintains": "{from_} maintains {to}.",
    "prevents": "{from_} prevents {to}.",
    "supports": "{from_} supports {to}.",
    "enables": "{from_} enables {to}.",
    "explains": "{from_} explains {to}.",
    "related": "{from_} is related to {to}.",
    "associated_with": "{from_} is associated with {to}.",
    "associated-with": "{from_} is associated with {to}.",
}

_UNCERTAINTY_OR_INTENT = re.compile(
    r"\b(?:might|may|could|perhaps|maybe|would|plan|planning|tomorrow|not sure)\b|\?",
    re.IGNORECASE,
)
_UNSETTLED_OR_ATTEMPT = re.compile(
    r"\b(?:bought|haven't|hasn't|didn't|not yet|try|trying|failed|fails|"
    r"might|may|could|perhaps|maybe|plan|planning|tomorrow)\b",
    re.IGNORECASE,
)
_NEGATED_OUTCOME = re.compile(
    r"\b(?:didn't|did not|doesn't|does not|never|failed|fails|dried out|dry out|dead)\b",
    re.IGNORECASE,
)


def _terms(value: str) -> frozenset[str]:
    return frozenset(
        _TERM_ALIASES.get(token.casefold(), token.casefold())
        for token in _WORD_RE.findall(value.replace("_", " "))
        if token.casefold() not in _STOP_WORDS and len(token) > 1
    )


def _proposition_text(value: str) -> str:
    """Normalize model-produced labels for semantic comparison only.

    GLiNER source-side labels sometimes contain Markdown residue (for example
    ``usage* profile``).  This never changes immutable source quotations or
    the persisted raw candidate.
    """

    return re.sub(r"\s+", " ", re.sub(r"[`*_]", " ", str(value))).strip()


def _hypothesis(monitor: AssessorMonitor) -> str:
    relation = str(monitor.relation["relation"]).casefold()
    from_ = _proposition_text(str(monitor.relation["from"]))
    to = _proposition_text(str(monitor.relation["to"]))
    template = _RELATION_TEMPLATES.get(relation)
    if template is not None:
        return template.format(from_=from_, to=to)
    return f"{from_} {relation.replace('_', ' ')} {to}."


def _source_mentions_proposition(source: str, monitor: AssessorMonitor) -> bool:
    source_terms = _terms(source)
    subject_terms = _terms(_proposition_text(str(monitor.relation["from"])))
    object_terms = _terms(_proposition_text(str(monitor.relation["to"])))
    return bool(subject_terms & source_terms) and bool(object_terms & source_terms)


def _relation_is_expressed(source: str, monitor: AssessorMonitor) -> bool:
    relation = str(monitor.relation["relation"]).casefold()
    cues = _RELATION_CUES.get(relation)
    if cues is None:
        return False
    return any(cue in source.casefold() for cue in cues)


def _relation_is_negated(source: str, monitor: AssessorMonitor) -> bool:
    """Recognize bounded outcome language that contradicts a relation."""

    return str(monitor.relation["relation"]) in {"maintains", "retains"} and bool(
        _NEGATED_OUTCOME.search(source)
    )


def _evidence_quote(source: str, monitor: AssessorMonitor) -> str:
    """Choose a unique exact source quotation for a present assessment."""

    # Keep punctuation and formatting in the returned quotation.  A sentence
    # is preferable to the entire source because full-source quotations can be
    # ambiguous when a source repeats a passage.
    candidates = [
        match.group(0).strip()
        for match in re.finditer(r".*?(?:[.!?](?:\s+|$)|$)", source, flags=re.S)
        if match.group(0).strip()
        and _source_mentions_proposition(match.group(0), monitor)
    ]
    candidates.extend([source] if source else [])
    for candidate in candidates:
        if source.count(candidate) == 1:
            return candidate
    raise ValueError(
        f"source evidence for monitor {monitor.monitor_id} has no unique exact quotation"
    )


def _json_payload(content: str) -> Mapping[str, Any]:
    """Recover the final assessor request object from the shared prompt."""

    decoder = json.JSONDecoder()
    marker = '"schema_version"'
    # ``prompt_payload`` uses sorted keys, so ``schema_version`` is not
    # necessarily the first member of the actual object.  Scan every object
    # boundary and select the complete request by its schema marker; the
    # earlier prose example is intentionally ignored.
    starts = [match.start() for match in re.finditer(r"\{", content)]
    for start in reversed(starts):
        try:
            value, _ = decoder.raw_decode(content[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, Mapping) and value.get("schema_version") == ASSESSOR_SCHEMA_VERSION:
            return value
    raise HostError(f"local NLI assessor could not find {marker} payload")


def assessor_request_from_payload(payload: Mapping[str, Any]) -> AssessorRequest:
    """Deserialize the shared production request for local assessment."""

    sources = tuple(
        AssessorSource(
            str(item["slot"]),
            str(item["role"]),
            bool(item["available"]),
            item.get("text"),
            item.get("source_id"),
        )
        for item in payload.get("sources", [])
        if isinstance(item, Mapping)
    )
    monitors = tuple(
        AssessorMonitor(
            str(item["monitor_id"]),
            item["relation"],
            tuple(item.get("required_source_slots", [])),
            tuple(item.get("evidence_source_slots", [])),
            tuple(item.get("correspondence_source_slots", [])),
            str(item.get("context", "general")),
        )
        for item in payload.get("monitors", [])
        if isinstance(item, Mapping)
    )
    return AssessorRequest(
        candidate=payload["candidate"],
        sources=sources,
        monitors=monitors,
        memory_exposure=tuple(payload.get("memory_exposure", [])),
        replay_ancestry=tuple(payload.get("replay_ancestry", [])),
        context=payload.get("context", {}),
        source_purpose_mask=tuple(payload.get("source_purpose_mask", [])),
        assessor_version=str(payload.get("prompt_version", "p2-local-nli")),
    )


class LocalNliAssessor:
    """Map specialist NLI scores into the existing semantic assessor contract."""

    def __init__(
        self,
        backend: NliBackend,
        *,
        thresholds: NliThresholds = NliThresholds(),
        max_window_chars: int = 1800,
        overlap_chars: int = 200,
    ) -> None:
        self.backend = backend
        self.thresholds = thresholds
        self.max_window_chars = max_window_chars
        self.overlap_chars = overlap_chars

    def _scores(
        self,
        monitor: AssessorMonitor,
        sources: Mapping[str, AssessorSource],
        slots: Sequence[str],
    ) -> dict[str, tuple[SourceWindow, NliScores]]:
        windows: list[SourceWindow] = []
        for slot in slots:
            source = sources[slot]
            if source.available and source.text:
                windows.extend(
                    _semantic_windows(
                        slot,
                        source.text,
                        monitor,
                        max_chars=self.max_window_chars,
                        overlap_chars=self.overlap_chars,
                    )
                )
        hypothesis = _hypothesis(monitor)
        scored = self.backend.score_pairs([(window.text, hypothesis) for window in windows])
        if len(scored) != len(windows):
            raise ValueError("NLI backend returned a score count different from its input")
        selected: dict[str, tuple[SourceWindow, NliScores]] = {}
        for window, score in zip(windows, scored):
            prior = selected.get(window.source_slot)
            quality = (
                not bool(_UNCERTAINTY_OR_INTENT.search(window.text)),
                _source_mentions_proposition(window.text, monitor),
                _relation_is_expressed(window.text, monitor),
                max(score.entailment, score.contradiction),
                -window.chunk_index,
            )
            prior_quality = (
                (
                    not bool(_UNCERTAINTY_OR_INTENT.search(prior[0].text)),
                    _source_mentions_proposition(prior[0].text, monitor),
                    _relation_is_expressed(prior[0].text, monitor),
                    max(prior[1].entailment, prior[1].contradiction),
                    -prior[0].chunk_index,
                )
                if prior is not None
                else None
            )
            if prior is None or (
                prior_quality is not None and quality > prior_quality
            ):
                selected[window.source_slot] = (window, score)
        return selected

    def assess(self, request: AssessorRequest) -> dict[str, Any]:
        """Return an ordinary v6 JSON result suitable for existing validation."""

        source_map = {source.slot: source for source in request.sources}
        rows: list[dict[str, Any]] = []
        for monitor in request.monitors:
            required = tuple(monitor.required_source_slots)
            available = [slot for slot in required if source_map[slot].available]
            complete = len(available) == len(required)
            coverage: dict[str, Any] = {
                "complete": complete,
                "source_slots": available,
                "reason": None if complete else "required source unavailable",
            }
            if not complete:
                rows.append(
                    {
                        "monitor_id": monitor.monitor_id,
                        "status": "unknown",
                        "relation_support": "unknown",
                        "expression_status": "unknown",
                        "coverage": coverage,
                        "evidence": None,
                        "corresponding_source_slots": [],
                    }
                )
                continue

            score_by_source = self._scores(monitor, source_map, available)
            if not score_by_source:
                raise ValueError(f"monitor {monitor.monitor_id} has no source windows")
            relevant_slots = tuple(
                slot
                for slot in available
                if _source_mentions_proposition(source_map[slot].text or "", monitor)
                or _relation_is_expressed(source_map[slot].text or "", monitor)
            )
            score_candidates = {
                slot: score_by_source[slot]
                for slot in relevant_slots
                if slot in score_by_source
            } or score_by_source
            best_slot, (best_window, best) = max(
                score_candidates.items(),
                key=lambda item: (
                    max(item[1][1].entailment, item[1][1].contradiction),
                    item[0],
                ),
            )
            # Restrict uncertainty/intent and relation cues to the selected
            # evidence window.  Looking across every covered source slot made
            # an unrelated ``would`` or ``planning`` sentence poison an
            # otherwise explicit proposition.
            best_text = best_window.text
            entailment = best.entailment
            contradiction = best.contradiction
            thresholds = self.thresholds
            strongly_entails = (
                entailment >= thresholds.entailment_min
                and entailment - max(contradiction, best.neutral) >= thresholds.margin_min
            )
            strongly_contradicts = (
                contradiction >= thresholds.contradiction_min
                and contradiction - max(entailment, best.neutral) >= thresholds.margin_min
            )
            mentioned = any(
                _source_mentions_proposition(source_map[slot].text or "", monitor)
                for slot in available
            )
            relation_negated = any(
                _relation_is_negated(source_map[slot].text or "", monitor)
                and _source_mentions_proposition(source_map[slot].text or "", monitor)
                for slot in available
            )
            uncertain_or_intended = bool(_UNCERTAINTY_OR_INTENT.search(best_text))
            unsettled_or_attempt = bool(_UNSETTLED_OR_ATTEMPT.search(best_text))
            best_relation_expressed = _relation_is_expressed(best_text, monitor)
            best_mentioned = _source_mentions_proposition(best_text, monitor)
            self_relation = _terms(_proposition_text(str(monitor.relation["from"]))) == _terms(
                _proposition_text(str(monitor.relation["to"]))
            )
            addressed = unsettled_or_attempt or (
                best_mentioned
                and (best_relation_expressed or relation_negated)
            ) or (
                strongly_entails
                and (best_relation_expressed or relation_negated)
            )
            # NLI contradiction can be spuriously high when a hypothesis
            # contains an entity absent from the premise (for example,
            # ``rain_jacket -> raises -> shade`` against a rain-only source).
            # The specialist may classify lexical incompatibility, but it
            # cannot establish that the proposition is addressed unless both
            # proposition sides occur in the covered source.  Keep the
            # existing semantic boundary fail-closed for those cases.
            if self_relation:
                status, support, expression = "absent", "unsupported", "not_expressed"
                coverage["reason"] = "self-relation is not a distinct proposition"
            elif (
                (strongly_contradicts or relation_negated)
                and best_mentioned
                and (best_relation_expressed or relation_negated)
                and not uncertain_or_intended
                and not self_relation
            ):
                status, support, expression = "present", "contradicted", "negated"
            elif (
                (strongly_entails or (best_relation_expressed and best_mentioned))
                and addressed
                and not uncertain_or_intended
                and not self_relation
            ):
                status, support, expression = "present", "supported", "affirmed"
            elif addressed or mentioned:
                status, support, expression = "present", "unsupported", "unknown"
            else:
                status, support, expression = "absent", "unsupported", "not_expressed"
                coverage["reason"] = "proposition not addressed by the covered source"

            evidence: dict[str, str] | None = None
            if status == "present":
                evidence_slot = best_slot
                if not _source_mentions_proposition(
                    source_map[evidence_slot].text or "", monitor
                ) and mentioned:
                    evidence_slot = next(
                        slot
                        for slot in available
                        if _source_mentions_proposition(source_map[slot].text or "", monitor)
                    )
                source_text = source_map[evidence_slot].text
                if source_text is None:
                    raise ValueError("present NLI assessment selected an unavailable source")
                evidence = {
                    "source_slot": evidence_slot,
                    "quote": _evidence_quote(source_text, monitor),
                }

            correspondence: list[str] = []
            if source_map[best_slot].role == "model_output":
                for slot in monitor.correspondence_source_slots:
                    antecedent = source_map[slot]
                    if not antecedent.available or not antecedent.text:
                        continue
                    antecedent_score = self._scores(monitor, source_map, (slot,)).get(slot)
                    if antecedent_score is None:
                        continue
                    if antecedent_score[1].entailment >= thresholds.entailment_min:
                        correspondence.append(slot)

            rows.append(
                {
                    "monitor_id": monitor.monitor_id,
                    "status": status,
                    "relation_support": support,
                    "expression_status": expression,
                    "coverage": coverage,
                    "evidence": evidence,
                    "corresponding_source_slots": correspondence,
                }
            )
        return {"schema_version": ASSESSOR_SCHEMA_VERSION, "assessments": rows}


class TransformersNliBackend:
    """Pinned CPU implementation backed by ``transformers`` and ``torch``."""

    def __init__(
        self,
        *,
        model_id: str = LOCAL_NLI_MODEL_ID,
        revision: str = LOCAL_NLI_MODEL_REVISION,
        device: str = "cpu",
        batch_size: int = 8,
        max_length: int = 512,
        local_files_only: bool = False,
    ) -> None:
        if device != "cpu":
            raise ValueError("CPU is the default qualified execution target")
        if batch_size <= 0 or max_length <= 0:
            raise ValueError("batch_size and max_length must be positive")
        try:
            import torch  # type: ignore[import-not-found]
            from transformers import (  # type: ignore[import-not-found]
                AutoModelForSequenceClassification,
                AutoTokenizer,
            )
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise HostError(
                "local NLI requires optional dependencies: torch, transformers, and sentencepiece"
            ) from exc
        started = time.perf_counter()
        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(
            model_id, revision=revision, local_files_only=local_files_only
        )
        self._model = AutoModelForSequenceClassification.from_pretrained(
            model_id, revision=revision, local_files_only=local_files_only
        ).to(device)
        self._model.eval()
        self.model_id = model_id
        self.model_revision = revision
        self.runtime_version = f"torch-{torch.__version__}"
        self.device = device
        self.batch_size = batch_size
        self.max_length = max_length
        self.load_seconds = time.perf_counter() - started
        raw_labels = getattr(self._model.config, "id2label", {})
        self._labels = {int(key): str(value).casefold() for key, value in raw_labels.items()}

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[NliScores, ...]:
        results: list[NliScores] = []
        for start in range(0, len(pairs), self.batch_size):
            batch = pairs[start : start + self.batch_size]
            premises = [pair[0] for pair in batch]
            hypotheses = [pair[1] for pair in batch]
            encoded = self._tokenizer(
                premises,
                hypotheses,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            )
            with self._torch.inference_mode():
                logits = self._model(**encoded).logits
                probabilities = self._torch.softmax(logits, dim=-1).cpu().tolist()
            for row in probabilities:
                by_label = {self._labels[index]: float(value) for index, value in enumerate(row)}
                results.append(
                    NliScores(
                        entailment=by_label.get("entailment", 0.0),
                        contradiction=by_label.get("contradiction", 0.0),
                        neutral=by_label.get("neutral", 0.0),
                    )
                )
        return tuple(results)


class LocalNliAssessorHost:
    """Host adapter retaining the existing GenerationRequest boundary."""

    def __init__(
        self,
        backend: NliBackend | None = None,
        *,
        classifier: PairClassifier | None = None,
        thresholds: NliThresholds = NliThresholds(),
        max_window_chars: int = 1800,
        overlap_chars: int = 200,
    ) -> None:
        if backend is None and classifier is None:
            raise ValueError("local NLI assessor requires backend or classifier")
        if backend is not None and classifier is not None:
            raise ValueError("supply backend or classifier, not both")
        self.backend = backend or _ClassifierBackend(cast(PairClassifier, classifier))
        self.assessor = LocalNliAssessor(
            self.backend,
            thresholds=thresholds,
            max_window_chars=max_window_chars,
            overlap_chars=overlap_chars,
        )

    def capabilities(self) -> HostCapabilities:
        return HostCapabilities(frozenset({Capability.TEXT_GENERATION, Capability.LOCAL_WEIGHTS}))

    def fingerprint(self) -> HostFingerprint:
        return HostFingerprint(
            model_family="DeBERTa NLI cross-encoder",
            model_id=self.backend.model_id,
            model_revision=self.backend.model_revision,
            tokenizer_id=self.backend.model_id,
            tokenizer_revision=self.backend.model_revision,
            chat_template=None,
            quantization=None,
            runtime=LOCAL_NLI_RUNTIME,
            runtime_version=self.backend.runtime_version,
            provider="local-cpu",
            execution={
                "thresholds": self.assessor.thresholds.__dict__,
                "max_window_chars": self.assessor.max_window_chars,
                "overlap_chars": self.assessor.overlap_chars,
                "config_sha256": LOCAL_NLI_CONFIG_SHA256,
            },
            capabilities=self.capabilities().supported,
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        self.capabilities().require(Capability.TEXT_GENERATION)
        if not request.messages:
            raise HostError("local NLI assessor requires the serialized assessor request")
        payload = _json_payload(request.messages[-1]["content"])
        assessor_request = assessor_request_from_payload(payload)
        started = time.perf_counter()
        result = self.assessor.assess(assessor_request)
        elapsed = (time.perf_counter() - started) * 1000
        return GenerationResult(
            content=json.dumps(result, ensure_ascii=False, sort_keys=True),
            model_id=self.backend.model_id,
            provider="local-cpu",
            effective_parameters=dict(request.parameters),
            seed=request.seed,
            token_usage=TokenUsage(),
            latency_ms=elapsed,
            finish_reason="stop",
            raw_metadata={"assessor_version": LOCAL_NLI_VERSION},
            provenance={"host": self.fingerprint().to_dict()},
        )


__all__ = [
    "LOCAL_NLI_MODEL_ID",
    "LOCAL_NLI_CONFIG_SHA256",
    "LOCAL_NLI_MODEL_REVISION",
    "LOCAL_NLI_RUNTIME",
    "LOCAL_NLI_VERSION",
    "LOCAL_NLI_ASSESSOR_VERSION",
    "LocalNliAssessor",
    "LocalNliAssessorHost",
    "NliBackend",
    "PairClassifier",
    "NliScores",
    "NliThresholds",
    "SourceWindow",
    "TransformersNliBackend",
    "assessor_request_from_payload",
    "source_windows",
]
