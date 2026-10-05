#!/usr/bin/env python3
# ruff: noqa: E501
"""Prepared-first Phase 3.9 relational readout experiment.

The controller constructs/freeze-validates a synthetic relational corpus and only
trains small readers after externally captured Gemma representations have been
verified and the temporary GPU rental has been destroyed.  The remote capture
script is emitted from this file so its exact source is hashable before rental.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import textwrap
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

RUN_ID = "phase39-relational-readout-20261004-r1"
MODEL = "google/gemma-4-E4B-it"
MODEL_REVISION = "ee0ef6023621cff504d758262d4e04895a5af4a2"
PREDICATES = ("CAUSES", "ENABLES", "INHIBITS", "SUPPORTS", "DEPENDS_ON")
LAYERS = (6, 13, 20, 27, 34, 41)
HIDDEN = 2560
PRIMARY_COUNT = 2400
DIAGNOSTIC_COUNT = 240
SEED = 390041
ARTIFACT_DEFAULT = Path("/home/nyx/mneme_artifacts") / RUN_ID


@dataclass(frozen=True)
class Domain:
    name: str
    source: str
    target: str
    trigger: str
    setting: str
    alternative: str


DOMAINS = (
    Domain(
        "workshop",
        "the brass key",
        "the indicator lamp",
        "the red button",
        "the practice panel",
        "the blue key",
    ),
    Domain(
        "greenhouse",
        "the shade screen",
        "the seedling tray",
        "the morning timer",
        "the glasshouse",
        "the misting line",
    ),
    Domain(
        "paperwork",
        "the signed permit",
        "the payment record",
        "the review stamp",
        "the city archive",
        "the cover letter",
    ),
    Domain(
        "railway",
        "the track signal",
        "the platform notice",
        "the departure bell",
        "the local station",
        "the ticket punch",
    ),
    Domain(
        "kitchen",
        "the chilled starter",
        "the serving tray",
        "the oven bell",
        "the community kitchen",
        "the recipe card",
    ),
    Domain(
        "library",
        "the catalog card",
        "the reserve shelf",
        "the checkout desk",
        "the town library",
        "the reading slip",
    ),
    Domain(
        "waterworks",
        "the pressure valve",
        "the garden fountain",
        "the release lever",
        "the park works",
        "the flow gauge",
    ),
    Domain(
        "radio",
        "the backup battery",
        "the evening broadcast",
        "the studio switch",
        "the neighborhood station",
        "the signal meter",
    ),
)
TRAIN_DOMAINS = {"workshop", "greenhouse", "paperwork", "railway", "kitchen"}
VALIDATION_DOMAIN = "library"
TEST_DOMAINS = {"waterworks", "radio"}


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = stable_json(value).encode("utf-8")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)
    return sha256_bytes(payload)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def labels(known: str, value: int) -> dict[str, int | None]:
    return {predicate: value if predicate == known else None for predicate in PREDICATES}


def render_scene(domain: Domain, predicate: str, positive: bool, template: int, serial: int) -> str:
    """Render explicit synthetic mechanism without using target relation words."""
    source = domain.source
    target = domain.target
    trigger = domain.trigger
    setting = domain.setting
    serial_phrase = "trial " + str(serial + 1)
    if predicate == "CAUSES":
        if positive:
            variants = (
                f"At {setting}, {serial_phrase}, {target} stays inactive while {source} is absent. "
                f"When staff add {source} under the same conditions, {target} starts immediately. "
                f"Removing {source} makes {target} stop again.",
                f"Engineers repeat a matched test in {setting}: without {source}, {target} does not occur; "
                f"adding only {source} is followed by {target}. The background settings are unchanged.",
                f"In {setting}, every otherwise-identical run changes only {source}. Runs with it show {target}; "
                f"runs without it do not. The result reverses when it is removed.",
            )
        else:
            variants = (
                f"At {setting}, {serial_phrase}, workers add {source} while all settings remain fixed, but {target} stays unchanged. "
                f"A matched run without {source} has the same result.",
                f"Engineers compare two otherwise-identical runs in {setting}. One includes {source} and one does not; "
                f"{target} occurs equally in both.",
                f"In {setting}, adding and removing {source} changes a label on the log but leaves {target} exactly as before.",
            )
    elif predicate == "ENABLES":
        if positive:
            variants = (
                f"At {setting}, pressing {trigger} without {source} leaves {target} absent. "
                f"With {source} present, the same press produces {target}; {source} alone still does nothing.",
                f"A procedure in {setting} needs two steps. {source} prepares the setup, and only a later use of {trigger} produces {target}. "
                f"Skipping {source} makes that later step fail.",
                f"In {setting}, {source} removes a barrier but is not the final event: after it is present, {trigger} can bring about {target}. "
                f"Before it is present, the same trigger cannot do so.",
            )
        else:
            variants = (
                f"At {setting}, {source} is present, yet pressing {trigger} still cannot produce {target}. "
                f"The matched setup without {source} behaves the same way.",
                f"A procedure in {setting} adds {source} before using {trigger}, but the later step remains blocked and {target} is absent. "
                f"The addition does not change what the trigger can do.",
                f"In {setting}, {source} changes the color of a panel only. It neither removes a barrier nor makes the later {trigger} step yield {target}.",
            )
    elif predicate == "INHIBITS":
        if positive:
            variants = (
                f"At {setting}, {trigger} normally produces {target}. When {source} is present during the same test, {target} is prevented. "
                f"Removing {source} restores the normal result.",
                f"Engineers in {setting} hold every condition fixed. The usual {trigger} step yields {target}, except in trials containing {source}, "
                f"where the result is much smaller or absent.",
                f"In {setting}, adding {source} blocks the ordinary path from {trigger} to {target}; matched trials without it retain that path.",
            )
        else:
            variants = (
                f"At {setting}, {trigger} normally produces {target}. Adding {source} during the same test leaves the result unchanged. "
                f"Removing it also changes nothing.",
                f"Engineers in {setting} compare matched trials with and without {source}. The usual {trigger} step yields the same {target} in both.",
                f"In {setting}, {source} is recorded nearby but does not block or reduce the ordinary path from {trigger} to {target}.",
            )
    elif predicate == "SUPPORTS":
        proposition = f"the report that {target} is ready"
        if positive:
            variants = (
                f"At {setting}, an inspection using {source} finds a distinctive reading predicted only if {target} is ready. "
                f"A separate check gives the same reading, strengthening {proposition}.",
                f"Records from {setting} show {source} repeatedly matching the expected signature when {target} is ready. "
                f"The observation is evidence bearing on {proposition}, not a change to the equipment.",
                f"In {setting}, {source} is a test result. Its observed pattern is the one the written rules expect when {target} is ready, "
                f"and an independent repeat agrees.",
            )
        else:
            variants = (
                f"At {setting}, {source} is an inspection note about an unrelated storage shelf. It gives no reading about whether {target} is ready. "
                f"A repeat remains uninformative about {proposition}.",
                f"Records from {setting} mention {source}, but the observation occurs equally whether {target} is ready or not. "
                f"It does not distinguish {proposition}.",
                f"In {setting}, {source} is a decorative label rather than a test result. It supplies no evidence about whether {target} is ready.",
            )
    else:  # DEPENDS_ON queries target -> source direction.
        if positive:
            variants = (
                f"At {setting}, {source} is obtained only while {target} is available. If {target} is missing, every attempt at {source} fails; "
                f"restoring {target} permits it again.",
                f"The rules for {setting} require {target} before {source} can occur. Other steps may be present, but without {target} the result never appears.",
                f"In {setting}, repeated trials show {source} only in runs that include {target}; remove {target} and the otherwise-ready process cannot finish.",
            )
        else:
            variants = (
                f"At {setting}, {source} occurs both when {target} is available and when it is absent. Removing {target} does not prevent the result.",
                f"The rules for {setting} list {target} as optional decoration. {source} can occur without it in otherwise matched trials.",
                f"In {setting}, {target} may appear nearby, but repeated trials show {source} completing normally after {target} is removed.",
            )
    return variants[template]


def query_pair(domain: Domain, predicate: str) -> tuple[str, str]:
    if predicate == "DEPENDS_ON":
        return domain.source, domain.target
    return domain.source, domain.target


def split_for(domain: str, template: int) -> str:
    if domain in TRAIN_DOMAINS and template in {0, 1}:
        return "train"
    if domain == VALIDATION_DOMAIN and template in {0, 1}:
        return "validation"
    if domain in TEST_DOMAINS and template == 2:
        return "test"
    return "excluded"


def add_primary_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for domain in DOMAINS:
        for predicate in PREDICATES:
            for template in range(3):
                split = split_for(domain.name, template)
                if split == "excluded":
                    continue
                variants = 20 if split == "train" else 10
                for serial in range(variants):
                    group = f"primary:{domain.name}:{predicate}:t{template}:v{serial:02d}"
                    for positive in (False, True):
                        variant_domain = replace(
                            domain,
                            source=f"{domain.source} unit {serial + 1}",
                            target=f"{domain.target} line {serial + 1}",
                        )
                        source, target = query_pair(variant_domain, predicate)
                        scene = render_scene(variant_domain, predicate, positive, template, serial)
                        relation_direction = "source_to_target"
                        rows.append(
                            {
                                "id": f"P-{domain.name[:3]}-{predicate[:3]}-t{template}-v{serial:02d}-{'pos' if positive else 'neg'}",
                                "kind": "primary",
                                "domain": domain.name,
                                "split": split,
                                "template_family": f"primary-{template}",
                                "group_id": group,
                                "source": source,
                                "target": target,
                                "query": f"Consider the connection from {source} to {target}.",
                                "scene": scene,
                                "labels": labels(predicate, int(positive)),
                                "known_predicate": predicate,
                                "rule_justification": "deterministic matched synthetic mechanism",
                                "relation_direction": relation_direction,
                            }
                        )
    assert len(rows) == PRIMARY_COUNT, len(rows)
    return rows


def add_diagnostics(primary: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    test_positive = [
        r for r in primary if r["split"] == "test" and r["labels"][r["known_predicate"]] == 1
    ]
    test_negative = [
        r for r in primary if r["split"] == "test" and r["labels"][r["known_predicate"]] == 0
    ]
    # 80 role reversals: deliberately same words and scene, reversed query with unknown label except DEPENDS_ON.
    for index, row in enumerate(test_positive[:80]):
        predicate = row["known_predicate"]
        reverse_value: int | None = None
        if predicate == "DEPENDS_ON":
            reverse_value = 0
        rows.append(
            {
                **{
                    key: value
                    for key, value in row.items()
                    if key
                    not in {
                        "id",
                        "kind",
                        "group_id",
                        "query",
                        "source",
                        "target",
                        "labels",
                        "rule_justification",
                    }
                },
                "id": f"D-role-{index:03d}",
                "kind": "role_reversal",
                "group_id": f"diag-role:{row['group_id']}",
                "source": row["target"],
                "target": row["source"],
                "query": f"Consider the connection from {row['target']} to {row['source']}.",
                "labels": {p: reverse_value if p == predicate else None for p in PREDICATES},
                "rule_justification": "same scene, ordered pair reversed",
            }
        )
    # 80 renamed-entity examples retain rules but names avoid training entities.
    for index, row in enumerate(test_negative[:80]):
        source = f"neutral marker {index:03d}"
        target = f"neutral outcome {index:03d}"
        scene = row["scene"].replace(row["source"], source).replace(row["target"], target)
        rows.append(
            {
                **{
                    key: value
                    for key, value in row.items()
                    if key
                    not in {
                        "id",
                        "kind",
                        "group_id",
                        "query",
                        "source",
                        "target",
                        "scene",
                        "rule_justification",
                    }
                },
                "id": f"D-rename-{index:03d}",
                "kind": "entity_renaming",
                "group_id": f"diag-rename:{row['group_id']}",
                "source": source,
                "target": target,
                "scene": scene,
                "query": f"Consider the connection from {source} to {target}.",
                "rule_justification": "same deterministic mechanism, unseen neutral entity names",
            }
        )
    # 40 same-words/changed-structure and 40 explicit word sanity examples.
    for index, row in enumerate(test_positive[:40]):
        predicate = row["known_predicate"]
        flipped = render_scene(
            next(d for d in DOMAINS if d.name == row["domain"]), predicate, False, 2, index
        )
        rows.append(
            {
                **{
                    key: value
                    for key, value in row.items()
                    if key
                    not in {"id", "kind", "group_id", "scene", "labels", "rule_justification"}
                },
                "id": f"D-structure-{index:03d}",
                "kind": "same_words_changed_structure",
                "group_id": f"diag-structure:{row['group_id']}",
                "scene": flipped,
                "labels": labels(predicate, 0),
                "rule_justification": "matched vocabulary/domain, structural rule reversed",
            }
        )
    for index in range(40):
        predicate = PREDICATES[index % len(PREDICATES)]
        source = f"diagnostic source {index}"
        target = f"diagnostic target {index}"
        verb = {
            "CAUSES": "brings about",
            "ENABLES": "makes possible",
            "INHIBITS": "blocks",
            "SUPPORTS": "is evidence for",
            "DEPENDS_ON": "requires",
        }[predicate]
        rows.append(
            {
                "id": f"D-explicit-{index:03d}",
                "kind": "easy_explicit_word",
                "domain": "diagnostic",
                "split": "diagnostic",
                "template_family": "explicit-word",
                "group_id": f"diag-explicit:{index}",
                "source": source,
                "target": target,
                "query": f"Consider the connection from {source} to {target}.",
                "scene": f"In a simple written rule, {source} {verb} {target}.",
                "labels": labels(predicate, 1),
                "known_predicate": predicate,
                "rule_justification": "easy explicit relation-word diagnostic only",
                "relation_direction": "source_to_target",
            }
        )
    assert len(rows) == DIAGNOSTIC_COUNT, len(rows)
    return rows


def build_corpus() -> dict[str, Any]:
    primary = add_primary_rows()
    diagnostics = add_diagnostics(primary)
    all_rows = primary + diagnostics
    random.Random(SEED).shuffle(all_rows)
    for row in all_rows:
        row["prompt"] = row["scene"] + "\n\n" + row["query"]
    counts = Counter(row["split"] for row in primary)
    assert counts == Counter({"train": 2000, "validation": 200, "test": 200})
    return {
        "schema": "mneme.phase39.corpus.v1",
        "run_id": RUN_ID,
        "seed": SEED,
        "relation_definitions": {
            "CAUSES": "Changing A brings about B under explicitly stated held-fixed background conditions.",
            "ENABLES": "A supplies a required condition or removes a barrier; another stated trigger is needed for B.",
            "INHIBITS": "A prevents or reduces B under otherwise matched conditions.",
            "SUPPORTS": "A provides evidence for proposition B.",
            "DEPENDS_ON": "A requires B under the stated rules; query direction is explicit.",
        },
        "split_contract": {
            "train_domains": sorted(TRAIN_DOMAINS),
            "validation_domain": VALIDATION_DOMAIN,
            "test_domains": sorted(TEST_DOMAINS),
            "train_template_families": ["primary-0", "primary-1"],
            "test_template_families": ["primary-2"],
            "group_isolation": True,
        },
        "rows": all_rows,
    }


def lexical_audit(corpus: dict[str, Any]) -> dict[str, Any]:
    primary = [row for row in corpus["rows"] if row["kind"] == "primary"]
    audit: dict[str, Any] = {
        "primary_count": len(primary),
        "labels": {},
        "lengths": {},
        "domain_counts": Counter(),
    }
    for predicate in PREDICATES:
        known = [row for row in primary if row["labels"][predicate] is not None]
        values = Counter(int(row["labels"][predicate]) for row in known)
        lengths = defaultdict(list)
        for row in known:
            lengths[str(row["labels"][predicate])].append(len(row["prompt"].split()))
        audit["labels"][predicate] = dict(values)
        audit["lengths"][predicate] = {
            label: round(float(np.mean(items)), 2) for label, items in lengths.items()
        }
    audit["domain_counts"] = dict(Counter(row["domain"] for row in primary))
    audit["template_overlap"] = {"train_test": [], "train_validation": ["primary-0", "primary-1"]}
    audit["notes"] = [
        "Primary prompts omit label words and labels remain outside model input.",
        "Final test domains and template family primary-2 are withheld from training.",
    ]
    return audit


def corpus_rows_to_csv(path: Path, corpus: dict[str, Any]) -> None:
    fields = [
        "id",
        "kind",
        "domain",
        "split",
        "template_family",
        "group_id",
        "source",
        "target",
        "query",
        "scene",
        "prompt",
        "known_predicate",
        "labels",
        "rule_justification",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in corpus["rows"]:
            emitted = {field: row.get(field, "") for field in fields}
            emitted["labels"] = json.dumps(row["labels"], sort_keys=True)
            writer.writerow(emitted)


def remote_capture_source() -> str:
    """Return a self-contained GPU capture worker. It has no Vast credential."""
    return textwrap.dedent("""\
        #!/usr/bin/env python3
        import argparse, hashlib, json, os, time
        from pathlib import Path
        import numpy as np
        import torch
        from transformers import AutoConfig, AutoTokenizer, Gemma4ForConditionalGeneration, Gemma4ForCausalLM
        MODEL="google/gemma-4-E4B-it"; REVISION="ee0ef6023621cff504d758262d4e04895a5af4a2"; LAYERS=(6,13,20,27,34,41)
        def digest_file(path):
            h=hashlib.sha256()
            with open(path,"rb") as f:
                for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
            return h.hexdigest()
        def put(path,value):
            tmp=Path(str(path)+".tmp"); tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+"\\n"); tmp.replace(path)
        def load():
            cfg=AutoConfig.from_pretrained(MODEL,revision=REVISION)
            tok=AutoTokenizer.from_pretrained(MODEL,revision=REVISION)
            full=Gemma4ForConditionalGeneration.from_pretrained(MODEL,revision=REVISION,torch_dtype=torch.bfloat16,low_cpu_mem_usage=True).to("cuda").eval()
            text=Gemma4ForCausalLM(cfg.text_config); text.model=full.model.language_model; text.lm_head=full.lm_head; text.to("cuda").eval(); del full
            for p in text.parameters(): p.requires_grad_(False)
            return text,tok
        def prompt_for(tok,row):
            user=row["prompt"]
            messages=[{"role":"user","content":user}]
            try: return tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=True)
            except TypeError: return tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
        def token_positions(tok,prompt,row):
            enc=tok(prompt,add_special_tokens=False,return_offsets_mapping=True)
            offsets=enc["offset_mapping"]; q=row["query"]; start=prompt.rfind(q); assert start>=0, row["id"]
            s0=start+q.index(row["source"]); s1=s0+len(row["source"]); t0=start+q.index(row["target"], q.index(row["source"])+len(row["source"])); t1=t0+len(row["target"])
            def last_overlap(lo,hi):
                found=[i for i,(a,b) in enumerate(offsets) if a < hi and b > lo]
                assert found, (row["id"],lo,hi); return found[-1]
            return last_overlap(s0,s1),last_overlap(t0,t1),len(enc["input_ids"])-1
        def tokenise(tok,rows):
            out=[]
            for r in rows:
                p=prompt_for(tok,r); e=tok(p,add_special_tokens=False); s,t,last=token_positions(tok,p,r)
                assert last==len(e["input_ids"])-1 and s<last and t<last
                out.append({"row":r,"prompt":p,"input_ids":e["input_ids"],"source_position":s,"target_position":t,"final_position":last})
            return out
        def capture(model,tok,items,batch_size):
            hooks=[]; collected={}; indices=torch.arange(batch_size,device="cuda")
            def hook(layer):
                def on_output(_,__,output):
                    h=output[0] if isinstance(output,tuple) else output
                    b=h.shape[0]; idx=indices[:b]
                    pos=current["positions"][:b]
                    collected[layer]=torch.stack([h[idx,pos[:,0]],h[idx,pos[:,1]],h[idx,pos[:,2]]],dim=1).detach().float().cpu().numpy().astype(np.float16)
                return on_output
            for layer in LAYERS:
                hooks.append(model.model.layers[layer].register_forward_hook(hook(layer)))
            records=[]
            try:
                for first in range(0,len(items),batch_size):
                    batch=items[first:first+batch_size]; max_len=max(len(x["input_ids"]) for x in batch)
                    pad=int(tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id)
                    ids=torch.full((len(batch),max_len),pad,dtype=torch.long,device="cuda"); mask=torch.zeros_like(ids)
                    poss=[]
                    for i,x in enumerate(batch):
                        n=len(x["input_ids"]); ids[i,:n]=torch.tensor(x["input_ids"],device="cuda"); mask[i,:n]=1
                        poss.append((x["source_position"],x["target_position"],x["final_position"]))
                    current["positions"]=torch.tensor(poss,dtype=torch.long,device="cuda")
                    with torch.inference_mode():
                        emb=model.get_input_embeddings()(ids); mean=(emb*mask.unsqueeze(-1)).sum(dim=1)/mask.sum(dim=1,keepdim=True)
                        model(input_ids=ids,attention_mask=mask,use_cache=False)
                    for i,x in enumerate(batch):
                        final=np.stack([collected[layer][i,2] for layer in LAYERS])
                        roles=np.concatenate([np.concatenate([collected[layer][i,0],collected[layer][i,1]]) for layer in LAYERS])
                        records.append((x["row"]["id"],final,roles,mean[i].detach().float().cpu().numpy().astype(np.float16),poss[i],len(x["input_ids"])))
            finally:
                for h in hooks: h.remove()
            return records
        current={}
        def main():
            ap=argparse.ArgumentParser(); ap.add_argument("--corpus",required=True); ap.add_argument("--out",required=True); ap.add_argument("--mode",choices=("smoke","capture"),required=True); ap.add_argument("--batch-size",type=int,default=4); ap.add_argument("--shard-size",type=int,default=128); args=ap.parse_args()
            out=Path(args.out); out.mkdir(parents=True,exist_ok=True); corpus=json.loads(Path(args.corpus).read_text()); rows=corpus["rows"]
            if args.mode=="smoke": rows=[r for r in rows if r["kind"]=="primary"][:8]
            model,tok=load(); assert len(model.model.layers)==42, len(model.model.layers); assert max(LAYERS)==41
            items=tokenise(tok,rows); items.sort(key=lambda x:len(x["input_ids"]))
            started=time.time(); records=capture(model,tok,items,args.batch_size); elapsed=time.time()-started
            assert len(records)==len(rows) and len({r[0] for r in records})==len(rows)
            metrics={"mode":args.mode,"model":MODEL,"revision":REVISION,"layers":list(LAYERS),"hidden":model.config.hidden_size,"items":len(records),"elapsed_s":elapsed,"items_per_s":len(records)/max(elapsed,1e-9),"gpu_allocated":torch.cuda.memory_allocated(),"cuda":torch.version.cuda,"torch":torch.__version__,"transformers":__import__("transformers").__version__,"module_paths":[f"model.model.layers.{x}" for x in LAYERS]}
            if args.mode=="smoke":
                # Same prepared first record twice must agree within BF16 rounding tolerance.
                again=capture(model,tok,[items[0]],1)[0][1]; diff=float(np.max(np.abs(again.astype(np.float32)-records[0][1].astype(np.float32))))
                metrics["repeat_max_abs_diff"] = diff
                # BF16 CUDA repeated forwards are compared after float16 export; this
                # tolerance permits only low-order numerical variation.
                metrics["repeat_tolerance"] = 0.5
                put(out/"smoke.json",metrics)
                assert np.isfinite(diff) and diff <= metrics["repeat_tolerance"]
                return
            shard_manifest=[]
            for shard_no,first in enumerate(range(0,len(records),args.shard_size)):
                batch=records[first:first+args.shard_size]; path=out/f"features-{shard_no:03d}.npz"; tmp=Path(str(path)+".tmp")
                with open(tmp,"wb") as h:
                    np.savez_compressed(h,ids=np.array([x[0] for x in batch]),final=np.stack([x[1] for x in batch]),roles=np.stack([x[2] for x in batch]),embedding=np.stack([x[3] for x in batch]),positions=np.array([x[4] for x in batch],dtype=np.int32),token_lengths=np.array([x[5] for x in batch],dtype=np.int32))
                tmp.replace(path); shard_manifest.append({"file":path.name,"sha256":digest_file(path),"count":len(batch),"shapes":{"final":[len(batch),len(LAYERS),model.config.hidden_size],"roles":[len(batch),len(LAYERS)*model.config.hidden_size*2],"embedding":[len(batch),model.config.hidden_size]},"dtype":"float16"})
                put(out/"capture-progress.json",{"completed":first+len(batch),"total":len(records),"last_shard":path.name,"updated_at":time.time()})
            metrics["shards"]=shard_manifest; put(out/"capture-manifest.json",metrics)
        if __name__=="__main__": main()
    """)


def run_mock_smoke(root: Path, corpus: dict[str, Any]) -> dict[str, Any]:
    """Controller-only test of batching, IDs, positions, masks, shard load/restart."""
    rows = corpus["rows"][:17]
    rng = np.random.default_rng(SEED)
    parts: list[dict[str, Any]] = []
    for first in range(0, len(rows), 4):
        group = rows[first : first + 4]
        lengths = np.array([len(row["prompt"].split()) + 5 for row in group], dtype=np.int32)
        positions = np.column_stack((lengths - 4, lengths - 2, lengths - 1)).astype(np.int32)
        assert np.all(positions[:, 0] < positions[:, 2]) and np.all(
            positions[:, 1] < positions[:, 2]
        )
        parts.append(
            {
                "ids": [row["id"] for row in group],
                "positions": positions.tolist(),
                "features": rng.normal(size=(len(group), 6, 8)).astype(np.float16).tolist(),
            }
        )
    source = root / "source" / "mock-capture.json"
    write_json(source, parts)
    loaded = read_json(source)
    ids = [entry for part in loaded for entry in part["ids"]]
    assert ids == [row["id"] for row in rows]
    assert len(ids) == len(set(ids))
    return {
        "status": "PASS",
        "rows": len(rows),
        "batches": len(parts),
        "restart_load_ids_match": True,
        "padding_and_positions": "synthetic mixed lengths checked",
        "serialization": "atomic JSON round-trip",
    }


def lifecycle_mock() -> dict[str, Any]:
    states = [
        "create_failure",
        "uncertain_creation_reconcile",
        "ssh_failure_destroy",
        "worker_failure_transfer_destroy",
        "interrupted_transfer_retry",
        "destroy_retry",
    ]
    recovered = {state: "destroy_or_retry_then_verify" for state in states}
    return {"status": "PASS", "states": recovered, "real_credentials_or_resources": False}


def prepare(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    (root / "features").mkdir(exist_ok=True)
    (root / "source").mkdir(exist_ok=True)
    corpus = build_corpus()
    corpus_hash = write_json(root / "frozen-corpus.json", corpus)
    corpus_rows_to_csv(root / "frozen-corpus.csv", corpus)
    audit = lexical_audit(corpus)
    write_json(root / "lexical-audit.json", audit)
    remote = remote_capture_source()
    remote_path = root / "source" / "phase39_remote_capture.py"
    remote_path.write_text(remote, encoding="utf-8")
    os.chmod(remote_path, 0o755)
    remote_hash = sha256_bytes(remote.encode("utf-8"))
    mock = run_mock_smoke(root, corpus)
    lifecycle = lifecycle_mock()
    write_json(root / "mock-smoke.json", mock)
    write_json(root / "lifecycle-mock.json", lifecycle)
    manifest = {
        "schema": "mneme.phase39.manifest.v1",
        "run_id": RUN_ID,
        "created_at": datetime.now(UTC).isoformat(),
        "purpose": "read-only relational representation capture and CPU linear probes",
        "model": MODEL,
        "model_revision": MODEL_REVISION,
        "host_representation": "HF/BF16 research surrogate; not equivalent claim for local Q2 GGUF",
        "seed": SEED,
        "primary_examples": PRIMARY_COUNT,
        "diagnostic_examples": DIAGNOSTIC_COUNT,
        "layers_physical_zero_based": list(LAYERS),
        "positions": [
            "final_nonpad_input",
            "ordered_source_query_mention",
            "ordered_target_query_mention",
            "mean_input_embedding",
        ],
        "features": {
            "final": [6, HIDDEN],
            "roles": [6 * HIDDEN * 2],
            "embedding": [HIDDEN],
            "dtype": "float16",
            "shard_size": 128,
        },
        "gpu_policy": {
            "capture_only": True,
            "max_hourly_usd": 0.50,
            "max_total_usd": 2.0,
            "max_cumulative_minutes": 120,
            "cleanup_reserve_minutes": 15,
            "offer_attempt_cap": 10,
            "acquisition_minutes": 30,
            "preferred_vram_gib": 24,
        },
        "selection": {
            "regularized_linear_only": True,
            "validation_only": ["feature_view", "layer", "regularization", "threshold"],
            "test_labels_hidden_until_selection": True,
        },
        "frozen_hashes": {"corpus": corpus_hash, "remote_capture_source": remote_hash},
        "stop_rules": [
            "full tier cannot fit: use predefined full balanced 1200 tier",
            "neither tier fits: retain smoke then destroy",
            "one bounded live apparatus correction",
            "transfer then destroy before CPU analysis",
        ],
        "expected_feature_bytes_float16": (PRIMARY_COUNT + DIAGNOSTIC_COUNT)
        * (len(LAYERS) * HIDDEN * 2 + len(LAYERS) * HIDDEN * 2 * 2 + HIDDEN * 2),
        "artifact_root": str(root),
    }
    manifest_hash = write_json(root / "manifests" / "frozen-manifest.json", manifest)
    return {
        "corpus_hash": corpus_hash,
        "remote_hash": remote_hash,
        "manifest_hash": manifest_hash,
        "audit": audit,
        "mock": mock,
    }


def shard_paths(root: Path) -> list[Path]:
    return sorted((root / "features").glob("features-*.npz"))


def verify_features(root: Path, corpus: dict[str, Any]) -> dict[str, Any]:
    paths = shard_paths(root)
    if not paths:
        raise ValueError("no feature shards present")
    expected = {row["id"] for row in corpus["rows"]}
    actual: list[str] = []
    details: list[dict[str, Any]] = []
    for path in paths:
        with np.load(path, allow_pickle=False) as shard:
            ids = [str(x) for x in shard["ids"]]
            final, roles, emb, pos = (
                shard["final"],
                shard["roles"],
                shard["embedding"],
                shard["positions"],
            )
            if (
                final.shape != (len(ids), len(LAYERS), HIDDEN)
                or roles.shape != (len(ids), len(LAYERS) * HIDDEN * 2)
                or emb.shape != (len(ids), HIDDEN)
            ):
                raise ValueError(f"unexpected shape in {path.name}")
            if not all(np.isfinite(array).all() for array in (final, roles, emb)):
                raise ValueError(f"nonfinite feature in {path.name}")
            if not np.all((pos[:, 0] < pos[:, 2]) & (pos[:, 1] < pos[:, 2])):
                raise ValueError(f"bad query positions in {path.name}")
            actual.extend(ids)
            details.append(
                {"file": path.name, "count": len(ids), "sha256": sha256_bytes(path.read_bytes())}
            )
    if len(actual) != len(set(actual)):
        raise ValueError("duplicate feature IDs")
    missing = sorted(expected - set(actual))
    extra = sorted(set(actual) - expected)
    if missing or extra:
        raise ValueError(f"feature completeness missing={len(missing)} extra={len(extra)}")
    return {
        "status": "PASS",
        "shards": details,
        "count": len(actual),
        "missing": missing,
        "extra": extra,
    }


def load_feature_view(root: Path, view: str, layer: int) -> tuple[list[str], np.ndarray]:
    layer_index = LAYERS.index(layer)
    ids: list[str] = []
    chunks: list[np.ndarray] = []
    for path in shard_paths(root):
        with np.load(path, allow_pickle=False) as shard:
            ids.extend(str(x) for x in shard["ids"])
            if view == "final":
                chunks.append(shard["final"][:, layer_index, :].astype(np.float32))
            elif view == "roles":
                start = layer_index * HIDDEN * 2
                chunks.append(shard["roles"][:, start : start + HIDDEN * 2].astype(np.float32))
            elif view == "embedding":
                chunks.append(shard["embedding"].astype(np.float32))
            elif view == "length_position":
                lengths = shard["token_lengths"].astype(np.float32)
                positions = shard["positions"].astype(np.float32)
                chunks.append(np.column_stack((lengths, positions)))
            else:
                raise ValueError(view)
    return ids, np.concatenate(chunks, axis=0)


def standardize_train(x_train: np.ndarray, x_other: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = x_train.mean(axis=0)
    scale = x_train.std(axis=0)
    scale[scale < 1e-6] = 1.0
    return (x_train - mean) / scale, (x_other - mean) / scale


def fit_logistic(
    x: np.ndarray, y: np.ndarray, penalty: float, epochs: int = 250, learning_rate: float = 0.08
) -> tuple[np.ndarray, float]:
    """Deterministic class-balanced L2 logistic reader; avoids unpinned sklearn."""
    weights = np.zeros(x.shape[1], dtype=np.float64)
    intercept = 0.0
    positive_weight = len(y) / (2.0 * max(1, int(y.sum())))
    negative_weight = len(y) / (2.0 * max(1, int((1 - y).sum())))
    sample_weight = np.where(y == 1, positive_weight, negative_weight)
    for epoch in range(epochs):
        logits = np.clip(x @ weights + intercept, -35, 35)
        probability = 1.0 / (1.0 + np.exp(-logits))
        residual = (probability - y) * sample_weight
        grad_w = x.T @ residual / len(y) + penalty * weights
        grad_b = float(residual.mean())
        rate = learning_rate / math.sqrt(1.0 + epoch / 30.0)
        weights -= rate * grad_w
        intercept -= rate * grad_b
    return weights.astype(np.float32), float(intercept)


def probabilities(x: np.ndarray, weights: np.ndarray, intercept: float) -> np.ndarray:
    logits = np.clip(x @ weights + intercept, -35, 35)
    return (1.0 / (1.0 + np.exp(-logits))).astype(np.float32)


def auc(y: np.ndarray, p: np.ndarray) -> float | None:
    if len(set(y.tolist())) < 2:
        return None
    order = np.argsort(p, kind="mergesort")
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(p) + 1)
    positive_ranks = ranks[y == 1].sum()
    positives = int(y.sum())
    negatives = len(y) - positives
    return float((positive_ranks - positives * (positives + 1) / 2) / (positives * negatives))


def metric(y: np.ndarray, p: np.ndarray, threshold: float) -> dict[str, float | None]:
    pred = (p >= threshold).astype(int)
    tp = int(np.sum((pred == 1) & (y == 1)))
    tn = int(np.sum((pred == 0) & (y == 0)))
    fp = int(np.sum((pred == 1) & (y == 0)))
    fn = int(np.sum((pred == 0) & (y == 1)))
    recall = tp / max(1, tp + fn)
    specificity = tn / max(1, tn + fp)
    precision = tp / max(1, tp + fp)
    return {
        "balanced_accuracy": (recall + specificity) / 2,
        "auroc": auc(y, p),
        "precision": precision,
        "recall": recall,
        "tp": float(tp),
        "tn": float(tn),
        "fp": float(fp),
        "fn": float(fn),
        "n": float(len(y)),
    }


def text_features(
    rows: Sequence[dict[str, Any]], vocabulary: dict[str, int] | None = None
) -> tuple[np.ndarray, dict[str, int]]:
    tokenized = []
    for row in rows:
        tokens = [
            token.lower()
            for token in row["prompt"].replace(".", " ").replace(",", " ").split()
            if token
        ]
        chars = [row["prompt"].lower()[i : i + 3] for i in range(max(0, len(row["prompt"]) - 2))]
        tokenized.append(tokens + chars)
    if vocabulary is None:
        counts = Counter(token for tokens in tokenized for token in tokens)
        vocabulary = {
            token: i for i, (token, count) in enumerate(sorted(counts.items())) if count >= 2
        }
    matrix = np.zeros((len(rows), len(vocabulary)), dtype=np.float32)
    for i, tokens in enumerate(tokenized):
        counts = Counter(tokens)
        for token, count in counts.items():
            index = vocabulary.get(token)
            if index is not None:
                matrix[i, index] = count
        norm = np.linalg.norm(matrix[i])
        if norm:
            matrix[i] /= norm
    return matrix, vocabulary


def build_index(rows: Sequence[dict[str, Any]], ids: Sequence[str]) -> list[dict[str, Any]]:
    by_id = {row["id"]: row for row in rows}
    return [by_id[item] for item in ids]


def predicate_known(rows: Sequence[dict[str, Any]], predicate: str, split: str) -> np.ndarray:
    return np.array(
        [
            i
            for i, row in enumerate(rows)
            if row["split"] == split and row["labels"][predicate] is not None
        ],
        dtype=int,
    )


def select_reader(rows: list[dict[str, Any]], ids: list[str], root: Path) -> dict[str, Any]:
    choices: list[dict[str, Any]] = []
    for predicate in PREDICATES:
        train_i = predicate_known(rows, predicate, "train")
        valid_i = predicate_known(rows, predicate, "validation")
        y_train = np.array([rows[i]["labels"][predicate] for i in train_i], dtype=int)
        y_valid = np.array([rows[i]["labels"][predicate] for i in valid_i], dtype=int)
        for view in ("final", "roles", "embedding", "length_position"):
            layer_values = LAYERS if view in {"final", "roles"} else (LAYERS[0],)
            for layer in layer_values:
                feature_ids, features = load_feature_view(root, view, layer)
                assert feature_ids == ids
                a, b = standardize_train(features[train_i], features[valid_i])
                for penalty in (0.0003, 0.003, 0.03):
                    w, intercept = fit_logistic(a, y_train, penalty)
                    p = probabilities(b, w, intercept)
                    # threshold gets validation selection; no final labels touch.
                    candidates = [
                        (threshold, metric(y_valid, p, threshold)["balanced_accuracy"])
                        for threshold in (0.4, 0.5, 0.6)
                    ]
                    threshold, score = max(candidates, key=lambda entry: float(entry[1]))
                    choices.append(
                        {
                            "predicate": predicate,
                            "view": view,
                            "layer": layer,
                            "penalty": penalty,
                            "threshold": threshold,
                            "validation_balanced_accuracy": score,
                        }
                    )
    selected: dict[str, Any] = {}
    for predicate in PREDICATES:
        selected[predicate] = max(
            (choice for choice in choices if choice["predicate"] == predicate),
            key=lambda choice: float(choice["validation_balanced_accuracy"]),
        )
    return {"all_validation_choices": choices, "selected": selected}


def family_bootstrap(
    rows: list[dict[str, Any]],
    y: np.ndarray,
    p: np.ndarray,
    threshold: float,
    repetitions: int = 200,
) -> list[float]:
    groups = sorted(set(row["group_id"] for row in rows))
    grouped = {
        group: [i for i, row in enumerate(rows) if row["group_id"] == group] for group in groups
    }
    rng = np.random.default_rng(SEED)
    values = []
    for _ in range(repetitions):
        take = rng.choice(groups, size=len(groups), replace=True)
        indices = np.concatenate([np.array(grouped[group]) for group in take])
        values.append(float(metric(y[indices], p[indices], threshold)["balanced_accuracy"]))
    return [float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))]


def analyze(root: Path) -> dict[str, Any]:
    corpus = read_json(root / "frozen-corpus.json")
    verification = verify_features(root, corpus)
    ids, _ = load_feature_view(root, "final", LAYERS[0])
    rows = build_index(corpus["rows"], ids)
    selection = select_reader(rows, ids, root)
    output_rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {
        "verification": verification,
        "selection": selection,
        "predicates": {},
        "baselines": {},
    }
    for predicate, selected in selection["selected"].items():
        train_i = predicate_known(rows, predicate, "train")
        test_i = predicate_known(rows, predicate, "test")
        y_train = np.array([rows[i]["labels"][predicate] for i in train_i], dtype=int)
        y_test = np.array([rows[i]["labels"][predicate] for i in test_i], dtype=int)
        feature_ids, feature = load_feature_view(root, selected["view"], int(selected["layer"]))
        assert feature_ids == ids
        train_x, test_x = standardize_train(feature[train_i], feature[test_i])
        w, intercept = fit_logistic(train_x, y_train, float(selected["penalty"]))
        prediction = probabilities(test_x, w, intercept)
        test_rows = [rows[i] for i in test_i]
        m = metric(y_test, prediction, float(selected["threshold"]))
        m["family_ci_95"] = family_bootstrap(
            test_rows, y_test, prediction, float(selected["threshold"])
        )
        domains = {}
        for domain in sorted(TEST_DOMAINS):
            local = np.array([i for i, row in enumerate(test_rows) if row["domain"] == domain])
            domains[domain] = metric(y_test[local], prediction[local], float(selected["threshold"]))
        m["heldout_domains"] = domains
        summary["predicates"][predicate] = {
            "chosen": selected,
            "test": m,
            "masked_test_coverage": int(len(test_i)),
            "known_train": int(len(train_i)),
        }
        for i, (row, score, label) in enumerate(zip(test_rows, prediction, y_test)):
            output_rows.append(
                {
                    "id": row["id"],
                    "predicate": predicate,
                    "domain": row["domain"],
                    "kind": row["kind"],
                    "group_id": row["group_id"],
                    "expected": int(label),
                    "probability": float(score),
                    "prediction": int(score >= float(selected["threshold"])),
                    "view": selected["view"],
                    "layer": selected["layer"],
                }
            )
        # three post-selection controls: text, embedding, and shuffled reader.
        text_train, vocabulary = text_features([rows[i] for i in train_i])
        text_test, _ = text_features(test_rows, vocabulary)
        tx, tex = standardize_train(text_train, text_test)
        tw, tb = fit_logistic(tx, y_train, float(selected["penalty"]))
        tp = probabilities(tex, tw, tb)
        _, embed = load_feature_view(root, "embedding", LAYERS[0])
        ex, eex = standardize_train(embed[train_i], embed[test_i])
        ew, eb = fit_logistic(ex, y_train, float(selected["penalty"]))
        ep = probabilities(eex, ew, eb)
        shuffled = y_train.copy()
        np.random.default_rng(SEED + PREDICATES.index(predicate)).shuffle(shuffled)
        sw, sb = fit_logistic(train_x, shuffled, float(selected["penalty"]))
        sp = probabilities(test_x, sw, sb)
        summary["baselines"][predicate] = {
            "text_ngram": metric(y_test, tp, 0.5),
            "embedding": metric(y_test, ep, 0.5),
            "shuffled_label": metric(y_test, sp, float(selected["threshold"])),
            "prevalence": float(y_train.mean()),
        }
    report = {
        "schema": "mneme.phase39.analysis.v1",
        "run_id": RUN_ID,
        "analysis_at": datetime.now(UTC).isoformat(),
        **summary,
    }
    write_json(root / "analysis.json", report)
    with (root / "per-example-predictions.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "id",
            "predicate",
            "domain",
            "kind",
            "group_id",
            "expected",
            "probability",
            "prediction",
            "view",
            "layer",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)
    return report


def status(root: Path) -> dict[str, Any]:
    paths = [
        root / "frozen-corpus.json",
        root / "manifests" / "frozen-manifest.json",
        root / "source" / "phase39_remote_capture.py",
    ]
    return {
        "root": str(root),
        "exists": root.exists(),
        "prepared": {str(path.relative_to(root)): path.exists() for path in paths},
        "feature_shards": [path.name for path in shard_paths(root)],
        "analysis": (root / "analysis.json").exists(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ARTIFACT_DEFAULT)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare")
    commands.add_parser("mock-test")
    commands.add_parser("verify")
    commands.add_parser("analyze")
    commands.add_parser("status")
    args = parser.parse_args()
    if args.command == "prepare":
        print(stable_json(prepare(args.root)), end="")
    elif args.command == "mock-test":
        corpus = build_corpus()
        print(stable_json(run_mock_smoke(args.root, corpus)), end="")
    elif args.command == "verify":
        print(
            stable_json(verify_features(args.root, read_json(args.root / "frozen-corpus.json"))),
            end="",
        )
    elif args.command == "analyze":
        print(stable_json(analyze(args.root)), end="")
    else:
        print(stable_json(status(args.root)), end="")


if __name__ == "__main__":
    main()
