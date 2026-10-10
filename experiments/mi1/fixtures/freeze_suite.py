"""Freeze the prospective MI1 synthetic test suite without model calls.

The generated JSON is the authority for exact prompts, banks, answer keys,
conditions, and seeds. This module only expands concise authored fixtures.
"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SEEDS = [34001, 34019]
FIXTURE_ROWS = [
    ("A01", ["Pavo", "Liri", "Sone", "Beka", "Tumo", "Wexi"], 0),
    ("A02", ["Neri", "Vako", "Juma", "Feli", "Rudo", "Kexa"], 1),
    ("A03", ["Cavi", "Mepo", "Zuri", "Hano", "Deki", "Lova"], 2),
    ("A04", ["Teni", "Gavo", "Rika", "Muni", "Selo", "Baxi"], 3),
    ("A05", ["Yaro", "Ceni", "Fuma", "Davo", "Kiri", "Noxa"], 4),
    ("A06", ["Hemi", "Zavo", "Puri", "Leka", "Mado", "Saxi"], 5),
    ("A07", ["Boru", "Tavi", "Nemi", "Ralo", "Vusa", "Jexo"], 0),
    ("A08", ["Kumo", "Deri", "Walo", "Fexa", "Peni", "Guta"], 1),
    ("A09", ["Savo", "Miri", "Heka", "Zuno", "Ceta", "Rixi"], 2),
    ("A10", ["Lumo", "Beri", "Teka", "Vano", "Juri", "Fosa"], 3),
    ("A11", ["Duma", "Xeri", "Kavo", "Pela", "Suri", "Moxa"], 4),
    ("A12", ["Ruma", "Cavo", "Yeni", "Hesa", "Tori", "Vexa"], 5),
]

A_CONDITIONS = [
    "no_bank",
    "visible_A",
    "visible_B",
    "latent_A",
    "latent_B",
    "latent_irrelevant",
]

IRRELEVANT_A_RULES = [
    "When Rema is awake, it calls Nilo.",
    "Nilo marks an entry in the daily ledger.",
    "Tova copies each marked entry into the archive.",
    "Seki remains unmarked unless Tova copies an entry.",
    "If Vuma is awake, Seki may be marked without a copy.",
    "Every eighth marked entry receives a green tab.",
]


def make_fixture(fixture_id: str, nodes: list[str], decoy_index: int) -> dict[str, Any]:
    source, bridge, relay, left, right, guard = nodes
    a_target, b_target = (left, right) if decoy_index % 2 == 0 else (right, left)
    a_locked, b_locked = b_target, a_target
    prompt = (
        f"Treat these as abstract labels. A rule saying X activates Y means that if X becomes active, Y can become active. "
        f"A lock prevents activation unless its stated exception applies. Only written rules count. Initially only {source} is active. "
        f"After applying the rules, which of {left} or {right} can become active? Give one label and the rule path; if the supplied facts do not decide, say unknown."
    )
    shared = [
        f"{source} activates {bridge}.",
        f"{bridge} activates {relay}.",
    ]
    if decoy_index % 2 == 0:
        direction_a = (
            f"{a_locked} activates {guard}; this does not mean {guard} activates {a_locked}."
        )
        direction_b = (
            f"{b_locked} activates {guard}; this does not mean {guard} activates {b_locked}."
        )
    else:
        direction_a = f"Only the direction {a_locked} to {guard} is stated; the reverse direction is not a rule."
        direction_b = f"Only the direction {b_locked} to {guard} is stated; the reverse direction is not a rule."
    bank_a = shared + [
        f"{relay} activates {a_target}.",
        f"While {bridge} is active, {a_locked} is locked.",
        f"Exception: that lock is removed if {guard} is active; {guard} is not initially active and no rule activates it.",
        direction_a,
    ]
    bank_b = shared + [
        f"{relay} activates {b_target}.",
        f"While {bridge} is active, {b_locked} is locked.",
        f"Exception: that lock is removed if {guard} is active; {guard} is not initially active and no rule activates it.",
        direction_b,
    ]
    unrelated = [
        f"{IRRELEVANT_A_RULES[(decoy_index + i) % len(IRRELEVANT_A_RULES)]}" for i in range(6)
    ]
    item = {
        "fixture_id": fixture_id,
        "nodes": nodes,
        "initial_active": [source],
        "recipient_request": prompt,
        "bank_A": {"statements": bank_a, "expected_answer": a_target},
        "bank_B": {"statements": bank_b, "expected_answer": b_target},
        "expected_by_condition": {
            "no_bank": "unknown",
            "visible_A": a_target,
            "visible_B": b_target,
            "latent_A": a_target,
            "latent_B": b_target,
            "latent_irrelevant": "unknown",
        },
        "irrelevant_bank": {"statements": unrelated, "expected_answer": "unknown"},
        "checks": {
            "bank_A_path": [source, bridge, relay, a_target],
            "bank_B_path": [source, bridge, relay, b_target],
            "answer_switches": True,
            "same_nodes_different_edges": True,
            "includes_reverse_direction_decoy": True,
            "includes_inactive_exception": True,
        },
    }
    item["bank_A"].update(
        {
            "activation_edges": [
                [source, bridge],
                [bridge, relay],
                [relay, a_target],
                [a_locked, guard],
            ],
            "lock": {"node": a_locked, "while_active": bridge, "unless_active": guard},
        }
    )
    item["bank_B"].update(
        {
            "activation_edges": [
                [source, bridge],
                [bridge, relay],
                [relay, b_target],
                [b_locked, guard],
            ],
            "lock": {"node": b_locked, "while_active": bridge, "unless_active": guard},
        }
    )
    return item


HARBOR = {
    "pack_id": "B-HARBOR",
    "statements": [
        "The usable shared area has a fixed capacity.",
        "Access is allocated in timed windows rather than by an unlimited queue.",
        "A completed return frees capacity for a later user.",
        "A delayed arrival shifts later handoffs instead of creating extra capacity.",
        "Current occupancy is checked before admitting the next user.",
    ],
    "topology_altered": [
        "The usable shared area has a fixed capacity.",
        "Access is allocated in timed windows rather than by an unlimited queue.",
        "A completed return does not free capacity for a later user.",
        "A delayed arrival leaves later handoffs unchanged and may create overlap.",
        "Current occupancy is checked only after the next user is admitted.",
    ],
    "tasks": [
        {
            "task_id": "B-HARBOR-1",
            "prompt": "Our neighborhood is considering a shared tool-lending setup for drills, saws, ladders, and gardening equipment. Popular tools disappear for days, people forget return dates, and nobody knows what is available. I want light administration. How would you design it?",
            "task_native_overlap": "High: the prompt directly names shared tools, disappearance, returns, and availability. Generic scheduling alone is not evidence of bank uptake.",
        },
        {
            "task_id": "B-HARBOR-2",
            "prompt": "A small community workshop has one laser cutter used by several clubs. Conflicts are common, but a formal booking office would be excessive. What lightweight operating arrangement would you suggest?",
            "task_native_overlap": "Moderate: shared machine use implies coordination, but no explicit schedule or time-window solution is requested.",
        },
        {
            "task_id": "B-HARBOR-3",
            "prompt": "An apartment building has a few shared e-bike charging outlets. Residents report that charged bikes are sometimes left connected and others cannot tell which outlets are occupied. Suggest a simple policy that does not require an app.",
            "task_native_overlap": "Moderate: occupancy is stated; time windows and handoffs are possible but not prescribed.",
        },
    ],
}

SUCCESSION = {
    "pack_id": "B-STAGED-CHANGE",
    "statements": [
        "A small early change can survive disruption and establish a workable foothold.",
        "That first foothold changes conditions for what can be changed next.",
        "Later changes depend on conditions created by earlier ones.",
        "Stable organization can emerge after several dependent transitions.",
        "Replacing every early element immediately can erase useful conditions and restart the process.",
    ],
    "topology_altered": [
        "A small early change can survive disruption and establish a workable foothold.",
        "That first foothold does not change conditions for what can be changed next.",
        "Later changes are independent of conditions created by earlier ones.",
        "Stable organization is imposed before any transition occurs.",
        "Replacing every early element immediately preserves all useful conditions and never restarts the process.",
    ],
    "tasks": [
        {
            "task_id": "B-STAGED-1",
            "prompt": "I inherited a messy software project held together by years of quick fixes. It still works, but nobody understands every dependency, and replacing it all at once would be risky. How should I approach change?",
            "task_native_overlap": "High: incremental software change is common task-native advice. Count only explicit dependency-enabling structure, not simply 'do it gradually.'",
        },
        {
            "task_id": "B-STAGED-2",
            "prompt": "A family-owned corner shop needs a major interior renovation but must stay open most days. There is little money for temporary relocation. How would you sequence the work?",
            "task_native_overlap": "Moderate: staging is invited by staying open, but path-dependent enabling conditions are not stated.",
        },
        {
            "task_id": "B-STAGED-3",
            "prompt": "A volunteer organization is combining two long-running services while clients still depend on both. Staff and records are organized differently, and abrupt changes could interrupt support. What transition plan would reduce risk?",
            "task_native_overlap": "Moderate: transition planning is task-native; count only early changes that enable later structures and stabilization.",
        },
    ],
}

DEFENSE = {
    "pack_id": "B-LAYERED-RESILIENCE",
    "statements": [
        "Several partially independent safeguards can cover different failure signals.",
        "An early check handles common mistakes before they spread.",
        "A local containment step limits damage while the cause is investigated.",
        "A separate fallback keeps service available if one safeguard fails.",
        "Escalation becomes stronger when evidence or severity increases.",
    ],
    "topology_altered": [
        "Several safeguards use the same signal and fail together.",
        "A check is performed only after damage has spread.",
        "A containment step is skipped while the cause is investigated.",
        "A fallback depends on the same component as the primary safeguard.",
        "Escalation is constant regardless of evidence or severity.",
    ],
    "tasks": [
        {
            "task_id": "B-LAYERED-1",
            "prompt": "A neighborhood festival needs to keep operating safely even if volunteers miss things, equipment fails, or someone causes a problem. We do not want one person or one rule to become a single point of failure. How would you design safeguards?",
            "task_native_overlap": "High: the prompt explicitly invites safeguards and failures. Count differentiated independent layers, containment, fallback, and evidence-scaled escalation, not generic caution.",
        },
        {
            "task_id": "B-LAYERED-2",
            "prompt": "A small nonprofit must protect its donor records and keep essential services running through staff turnover, accidental mistakes, and occasional computer outages. It cannot hire a security team. What practical protections should it use?",
            "task_native_overlap": "Moderate: backups and checks are natural, but independent detection/containment/escalation roles are not prescribed.",
        },
        {
            "task_id": "B-LAYERED-3",
            "prompt": "A volunteer food-distribution group depends on a few suppliers and rotating drivers. Missed deliveries or a vehicle problem can leave families without food that week. Suggest a practical continuity plan for a small budget.",
            "task_native_overlap": "Moderate: contingency planning is task-native; count only non-identical safeguards with local containment and severity-based escalation.",
        },
    ],
}

IRRELEVANT_PACK = {
    "pack_id": "B-IRRELEVANT-ARCHIVING",
    "statements": [
        "A page is assigned a stable title before it is filed.",
        "Related pages are grouped by subject in an index.",
        "A brief note records where a quotation came from.",
        "The index is checked when a reader searches for an old topic.",
        "A duplicate page is marked as a copy rather than treated as a new source.",
    ],
}

CONFIRMATION_TASKS = {
    "B-HARBOR": [
        {
            "task_id": "C-HARBOR-1",
            "prompt": "Several neighborhood groups share one indoor room for repair sessions. The room is sometimes left full of equipment when the next group arrives, and volunteers want a simple way to coordinate use without hiring a coordinator. What arrangement would you suggest?",
            "task_native_overlap": "Moderate: shared use is explicit; timed access and turnover are possible but not prescribed.",
        },
        {
            "task_id": "C-HARBOR-2",
            "prompt": "A town lends a few portable flood barriers to different blocks during storm season. Requests can overlap and return times depend on conditions. How could a small volunteer team keep the process fair and understandable?",
            "task_native_overlap": "Moderate: overlapping requests and returns appear in the task; linked occupancy accounting and handoffs are not prescribed.",
        },
    ],
    "B-STAGED-CHANGE": [
        {
            "task_id": "C-STAGED-1",
            "prompt": "A local permit office must replace a confusing filing process while residents still need permits every day. Staff can change only a small part of the workflow at a time. What sequence would reduce disruption?",
            "task_native_overlap": "Moderate: incremental work is required by the constraint; early changes enabling later changes are not stated.",
        },
        {
            "task_id": "C-STAGED-2",
            "prompt": "A small museum is moving its collections into a renovated building in stages, but researchers still need access during the move. How should the team organize the transition?",
            "task_native_overlap": "Moderate: staged transition is stated; dependencies where early setup creates later options are not prescribed.",
        },
    ],
    "B-LAYERED-RESILIENCE": [
        {
            "task_id": "C-LAYERED-1",
            "prompt": "A community theater relies on volunteers, a few aging lights, and a single ticket desk. A missed task or equipment issue should not cancel the whole evening. What practical operating safeguards would you add?",
            "task_native_overlap": "Moderate: safeguards are requested; distinct detection, containment, fallback, and escalation roles are not prescribed.",
        },
        {
            "task_id": "C-LAYERED-2",
            "prompt": "A small mobile health clinic visits several towns with a limited staff and equipment kit. Delays or a broken device can affect later appointments. How can it remain reliable without adding much staff?",
            "task_native_overlap": "Moderate: continuity is requested; independent safeguards and severity-based escalation are not specified.",
        },
    ],
}


def build_suite() -> dict[str, Any]:
    fixtures = [make_fixture(*row) for row in FIXTURE_ROWS]
    test_a = {
        "design": "12 fictional paired banks with same labels and counterfactual edge changes; each asks one fixed, answer-keyed reachability question.",
        "seeds": SEEDS,
        "conditions": A_CONDITIONS,
        "system_prompt": "You are solving a fictional rule task. Use only the supplied rules. Give the answer and a concise rule path; if the rules do not determine it, say unknown.",
        "condition_wrappers": {
            "no_bank": "{recipient_request}",
            "visible_A": "Reference rules:\n{bank_A}\n\nQuestion:\n{recipient_request}",
            "visible_B": "Reference rules:\n{bank_B}\n\nQuestion:\n{recipient_request}",
            "latent_A": "{recipient_request}",
            "latent_B": "{recipient_request}",
            "latent_irrelevant": "{recipient_request}",
        },
        "latent_bank_source_must_not_appear_in_recipient_request": True,
        "fixture_count": len(fixtures),
        "generation_count": len(fixtures) * len(SEEDS) * len(A_CONDITIONS),
        "fixtures": fixtures,
    }
    packs = [HARBOR, SUCCESSION, DEFENSE]
    test_b = {
        "design": "Three relational packs x three held-out ordinary tasks x two fixed seeds x six conditions.",
        "seeds": SEEDS,
        "conditions": [
            "no_bank",
            "visible_pack",
            "text_C",
            "latent_correct",
            "latent_irrelevant",
            "latent_topology_altered",
        ],
        "system_prompt": "Answer the user helpfully and stay focused on the task. Think through relevant considerations before giving a concise, practical response.",
        "condition_wrappers": {
            "no_bank": "{task_prompt}",
            "visible_pack": "Reference neighborhood:\n{pack}\n\nUser task:\n{task_prompt}",
            "text_C": "Required consideration: Before answering, explicitly consider the following neighborhood and determine which relationships, if any, transfer to the user's task. You may reject the connection if it is not useful.\n\n{pack}\n\nUser task:\n{task_prompt}",
            "latent_correct": "{task_prompt}",
            "latent_irrelevant": "{task_prompt}",
            "latent_topology_altered": "{task_prompt}",
        },
        "latent_bank_source_must_not_appear_in_recipient_request": True,
        "rubric": {
            "direct_repetition": "Repeats supplied wording or nouns without using its linked structure.",
            "multi_link": "Reasoning or final output uses at least two distinct connected relations from the bank.",
            "transformation": "Maps the relations into concrete task-native mechanisms without merely echoing source wording.",
            "rejection": "Explicitly evaluates and rejects a bank-derived idea as unsuitable.",
            "task_native_overlap": "Predeclared per prompt; do not credit ordinary advice already invited by the prompt absent traceable structural contribution.",
            "intrusion": "Disproportionate fixation or task displacement attributable to the bank.",
        },
        "packs": packs,
        "irrelevant_pack": IRRELEVANT_PACK,
        "generation_count": sum(len(p["tasks"]) for p in packs) * len(SEEDS) * 6,
    }
    confirmation = {
        "design": "Untouched confirmation reserve: two distinct tasks per pack, two fixed seeds, and four latent/control conditions.",
        "conditions": ["no_bank", "latent_correct", "latent_irrelevant", "latent_topology_altered"],
        "seeds": SEEDS,
        "tasks_by_pack": CONFIRMATION_TASKS,
        "generation_count": 2 * len(packs) * len(SEEDS) * 4,
        "scoring": "Use the frozen Test-B relation rubric and its pack-specific task-native-overlap caution. This set is only dispatched if a documented engineering revision makes all prior scored examples exploratory.",
    }
    test_c = {
        "design": "Three Test-A recipient coordinates replayed through bank-A, bank-B, disabled, then bank-A-restored; a separate ongoing exchange and a new bank use the frozen selector.",
        "fixtures": ["A02", "A06", "A10"],
        "seed": SEEDS[0],
        "fresh_context_generations": 3 * 4,
        "ongoing_exchange": {
            "fixture_id": "A02",
            "turns": 2,
            "bank_transition": "A then B",
            "turn1_user_prompt": fixtures[1]["recipient_request"],
            "turn2_user_prompt": "Using the same initially active label and the same candidate labels, answer the question again after the available rule neighborhood has been replaced. Give only the currently supported target and path.",
            "generations": 2,
            "interpretation": "The prior assistant response remains in the ongoing context; this is an update-in-conversation test, not proof that replacement erases prior generated text.",
        },
        "new_bank": {
            "encoding_passes": 1,
            "source_text": [
                "Daxi activates Bero.",
                "Bero activates Cuni.",
                "Cuni activates Efo.",
                "Efo activates Gaxi.",
            ],
            "initial_active": "Daxi",
            "recipient_contexts": [
                "Starting only with Daxi active, can Gaxi become active? Give the directed rule path or say unknown.",
                "If Bero becomes active from Daxi, what additional labels follow from the supplied relationships, and can Gaxi be reached?",
            ],
            "expected_path": ["Daxi", "Bero", "Cuni", "Efo", "Gaxi"],
            "fresh_context_generations": 2,
            "generations": 2,
        },
        "generation_count": 16,
        "interpretation": "Fresh clean recipient contexts prove disable/restore without generated-history carryover; the ongoing exchange is separately labeled and cannot imply past tokens were erased.",
    }
    return {
        "schema_version": 1,
        "experiment": "MNEME Phase 4-MI1 local Memory Inception synthetic test",
        "freeze_date": "2026-10-10",
        "base_commit": "df8e3c9dfd0afc2f17dd98737543da4a82c63683",
        "host_model": "google/gemma-4-E4B-it",
        "gguf_sha256": "79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03",
        "llama_cpp_commit": "4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0",
        "reasoning": "ON",
        "cache_prompt": False,
        "seeds": SEEDS,
        "generation_budget": {
            "calibration_max": 120,
            "test_a": 144,
            "test_b": 108,
            "test_c": 16,
            "untouched_confirmation_reserve": 48,
            "total_preplanned": 436,
            "authorized_hard_max": 800,
            "note": "Any failed, repair, or repeated call counts; no replacement hides the original failure. Forward-only bank encoding is counted separately and bounded to these frozen banks plus calibration banks.",
        },
        "calibration": {
            "separate_from_scored": True,
            "task_families": [
                "fictional reachability",
                "work coordination",
                "staged transition",
                "continuity planning",
            ],
            "site_diagnostic": "Compare a small sparse selector against broad valid attention sites; use separate tasks/fixtures and freeze site set, exposure schedule, wrapping, and gains before scored runs.",
            "gain_levels": ["low", "moderate", "strong"],
        },
        "test_a": test_a,
        "test_b": test_b,
        "test_c": test_c,
        "untouched_confirmation": confirmation,
        "scope": [
            "synthetic only",
            "no MNEME instance or state",
            "no SAA or developmental calls",
            "no cloud",
            "base weights frozen",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).with_name("mi1_frozen_suite.json")
    )
    args = parser.parse_args()
    content = json.dumps(build_suite(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    print(f"{args.output}: sha256={digest}")


if __name__ == "__main__":
    main()
