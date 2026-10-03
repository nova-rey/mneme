#!/usr/bin/env python3
# ruff: noqa: E501
"""Create compact read-only ON-25 to ON-30 influence receipts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path("/home/nyx/mneme")
ART = Path("/home/nyx/mneme_artifacts/mneme-reasoning-on-25-to-30-20261003")
OUT = ROOT / "docs/receipts"

CLASS = {
    (26, 0): ("ambiguous", "The payload concerned components and systems; reasoning discussed water ingress and internal components, but this is also the direct repair context and is not uniquely attributable to SAA."),
    (27, 2): ("ambiguous", "The payload mentioned supporting conditions and larger systems; reasoning recommended one-area-at-a-time work, but the user directly asked about layout sequencing."),
    (30, 1): ("ambiguous", "The payload mentioned downstream effects and structured unequal possibilities; reasoning integrated a hybrid access plan, but the user had already proposed that plan."),
    (30, 3): ("ambiguous", "The payload mentioned enabling conditions and shared roles; the closing answer endorsed the user's hybrid plan, without a distinct nudge-specific transformation."),
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compact(text: str, limit: int = 500) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def main() -> None:
    rows = [json.loads(line) for line in (ART / "coordinate-evidence.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    data = json.loads((ART / "final-evidence.json").read_text(encoding="utf-8"))
    derived = []
    for row in rows:
        key = (int(row["thread"]), int(row["turn"]))
        category, basis = CLASS.get(key, ("no_detectable_uptake", "The reasoning and final answer stayed on the immediate user task; no nudge-specific consideration or transformation is defensible from the recorded text."))
        meta = row["gemma"]["raw_metadata"]
        derived.append({
            "lineage": "ON",
            "thread": row["thread"],
            "turn": row["turn"],
            "classification": category,
            "classification_basis": basis,
            "participant_input": row["participant_input"],
            "payload": row["saa"].get("payload", ""),
            "field_seed": row["saa"].get("field_seed"),
            "selected_landing": row["saa"].get("selected_landing"),
            "total_pressure": row["saa"].get("total_pressure"),
            "landing_component": row["saa"].get("landing_component"),
            "candidate_component": next((c.get("candidate_component") for c in row["saa"].get("contributions", []) if c.get("component") == "landing"), None),
            "reasoning": meta.get("reasoning_content", ""),
            "final_response": row["gemma"].get("output", ""),
            "request_sha256": meta.get("request_sha256"),
            "reasoning_sha256": meta.get("reasoning_sha256"),
            "reasoning_bytes": meta.get("reasoning_bytes"),
            "finish_reason": row["gemma"].get("finish_reason"),
            "state_digest_before": row["state_digest_before"],
            "state_digest_after": row["state_digest_after"],
            "extraction": row["assessment"],
            "admitted": row["admitted"],
        })
    counts = {k: sum(1 for x in derived if x["classification"] == k) for k in ("no_detectable_uptake", "reasoning_only_consideration", "considered_and_rejected", "literal_direct_uptake", "transformed_integration", "bridge_extension", "dominant_intrusive", "ambiguous")}
    by_thread = []
    for thread in range(26, 31):
        items = [x for x in derived if x["thread"] == thread]
        by_thread.append({"thread": thread, "coordinates": len(items), "classifications": {k: sum(1 for x in items if x["classification"] == k) for k in counts}, "extraction_candidates": sum(x["extraction"]["extracted"] for x in items), "admitted": sum(x["extraction"]["accepted"] for x in items), "landings": len({x["selected_landing"] for x in items})})
    summary = {
        "schema": "mneme.on25-on30.saa-influence-summary.v1",
        "run_id": data["run_id"],
        "parent_run_id": "mneme-reasoning-25-fresh-20261003-r1",
        "schedule_sha256": data["schedule_sha256"],
        "coordinates": len(derived),
        "healthy_coordinates": len(derived),
        "nonempty_payloads": sum(bool(x["payload"]) for x in derived),
        "selected_landings": sum(bool(x["selected_landing"]) for x in derived),
        "reasoning_text_present": sum(bool(x["reasoning"]) for x in derived),
        "classification_counts": counts,
        "strict_conclusion": "No coordinate provides direct evidence that Gemma explicitly noticed, rejected, or transformed the administered SAA wording. Four coordinates are ambiguous because their responses share broad themes with the payload; sixteen show no detectable uptake. No literal, reasoning-only, considered-rejected, bridge, or dominant uptake was defensibly observed.",
        "by_thread": by_thread,
        "coordinate_records": derived,
        "artifact_hashes": {name: sha(ART / name) for name in ("coordinate-evidence.jsonl", "development-evidence.json", "final-evidence.json")},
        "live": data["live"],
        "checkpoint": data["checkpoint"],
    }
    json_path = OUT / "MNEME_ON25_ON30_SAA_Influence_Observation_20261003.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = []
    md += ["# MNEME ON-25 → ON-30 SAA Influence Observation", "", "## Plain-English answer", "", "**Thinking Gemma did not provide direct, defensible evidence of engaging with the administered SAA influence in these five threads.** All 20 healthy coordinates delivered a nonempty payload and a selected landing, and all 20 retained complete reasoning text. Under a strict reading of the traces, 16 coordinates show no detectable uptake. Four remain ambiguous because their responses share broad themes with the payload, but those themes were already present in the user's request. No coordinate supports a confident claim of reasoning-only consideration, explicit rejection, literal uptake, transformed integration, bridge/extension, or intrusive capture.", "", "This is a valid negative observation about the retained evidence, not proof that SAA had no latent effect. The renderer supplied highly abstract, generic tendencies, and a five-thread ON-only continuation cannot establish matched ON/OFF behavior.", ""]
    md += ["## Scope and durability", "", f"- Run: `{data['run_id']}`; exactly 20 coordinates (T26–T30 × 4 turns).", f"- Schedule SHA-256: `{data['schedule_sha256']}`.", f"- Healthy payloads/landings: {summary['nonempty_payloads']}/{summary['coordinates']} and {summary['selected_landings']}/{summary['coordinates']}.", f"- Reasoning text present: {summary['reasoning_text_present']}/{summary['coordinates']}; total bytes: {sum(x['reasoning_bytes'] or 0 for x in derived)}.", "- Each coordinate journal row retains context, full SAA field, exact request JSON/text, reasoning, final response, extraction JSON, candidate-level NLI scores/decisions, publication, and state digests.", "- The initial provider-token interruption after T26 turn 0 is preserved as an invalid apparatus attempt. T26 turn 0 was not replayed.", ""]
    md += ["## Influence classifications", "", "| Category | Count |", "|---|---:|"]
    labels = {"no_detectable_uptake": "No detectable uptake", "reasoning_only_consideration": "Reasoning-only consideration", "considered_and_rejected": "Considered and rejected", "literal_direct_uptake": "Literal/direct uptake", "transformed_integration": "Transformed integration", "bridge_extension": "Bridge/extension", "dominant_intrusive": "Dominant/intrusive", "ambiguous": "Ambiguous"}
    md += [f"| {labels[k]} | {v} |" for k, v in counts.items()]
    md += ["", "The classification is based on semantic traceability, not lexical overlap. ON reasoning can reveal consideration; here no trace explicitly identifies the supplied framing as an object of evaluation. The generic phrases such as ‘conditions’, ‘components’, ‘arrangements’, and ‘support’ were already licensed by the user contexts, so they are not counted as uptake.", ""]
    md += ["## Representative coordinates", ""]
    examples = [(26, 0), (27, 2), (28, 1), (30, 1), (30, 3)]
    for key in examples:
        x = next(item for item in derived if (item['thread'], item['turn']) == key)
        md += [f"### T{x['thread']} turn {x['turn']} — {labels[x['classification']]}", "", f"**Context:** {compact(x['participant_input'], 350)}", "", f"**SAA payload:** `{compact(x['payload'], 450)}`", "", f"**Reasoning excerpt:** {compact(x['reasoning'], 650)}", "", f"**Final excerpt:** {compact(x['final_response'], 650)}", "", f"**Why:** {x['classification_basis']}", "", f"**Encoding:** {x['extraction']['extracted']} candidates, {x['extraction']['accepted']} admitted; landing `{x['selected_landing']}`; pressure `{x['total_pressure']}`.", ""]
    md += ["## Extraction/NLI observation", "", "The continuation kept the encoder diagnostic separate from SAA uptake. Across T26–T30, GLiNER proposed 41 relationship candidates and the local NLI/admission path accepted 2. The accepted items were T28 turn 0 (‘day trip’ depends on ‘weather’) and T28 turn 3 (Gemma can help check the weather forecast enables that forecast). This shows that candidate-level evidence is now retained, but it does not establish that those admitted relations were caused by SAA or that SAA was behaviorally used.", "", "## Thread summary", "", "| Thread | Coordinates | Candidates | Admitted | Distinct landings |", "|---:|---:|---:|---:|---:|"]
    md += [f"| {x['thread']} | {x['coordinates']} | {x['extraction_candidates']} | {x['admitted']} | {x['landings']} |" for x in by_thread]
    md += ["", "## Limits", "", "- This is an ON-only continuation; there is no matched OFF continuation for T26–T30.", "- Reasoning from T01–T25 remains unavailable in the historical parent; this report does not reconstruct it.", "- A generic renderer payload may exert a subtle effect that is not identifiable from a single response trace. No causal claim is made from textual similarity alone.", "- This does not establish population-level behavior, general reasoning quality, or a normative/golden MNEME.", "", "## Artifacts", "", f"- Live ON-30: `{data['live']['path']}`; SHA-256 `{data['live']['sha256']}`; state digest `{data['live']['state_digest']}`.", f"- Immutable checkpoint: `{data['checkpoint']['path']}`; SHA-256 `{data['checkpoint']['sha256']}`.", f"- Full external coordinate evidence: `{ART / 'coordinate-evidence.jsonl'}`; SHA-256 `{summary['artifact_hashes']['coordinate-evidence.jsonl']}`.", f"- Full external final evidence: `{ART / 'final-evidence.json'}`; SHA-256 `{summary['artifact_hashes']['final-evidence.json']}`.", ""]
    md_path = OUT / "MNEME_ON25_ON30_SAA_Influence_Observation_20261003.md"
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"markdown": str(md_path), "json": str(json_path), "coordinates": len(derived), "classification_counts": counts}, indent=2))


if __name__ == "__main__":
    main()
