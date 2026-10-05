#!/usr/bin/env bash
# Phase 3.9 foreground-only lifecycle helper. It never stores a Vast credential.
set -Eeuo pipefail
ROOT="${PHASE39_ROOT:-/home/nyx/mneme_artifacts/phase39-relational-readout-20261004-r1}"
RUN_ID="phase39-relational-readout-20261004-r1"
STATE="$ROOT/manifests/lifecycle-state.json"
LOG="$ROOT/logs/supervisor.log"
mkdir -p "$ROOT/manifests" "$ROOT/logs" "$ROOT/incoming" "$ROOT/features"
log() { printf '%s %s\n' "$(date --iso-8601=seconds)" "$*" | tee -a "$LOG"; }
owned_id() { test -s "$STATE" && python3 - "$STATE" <<'PY'
import json,sys
try:
 print(json.load(open(sys.argv[1])).get("instance_id", ""))
except Exception:
 pass
PY
}
record_state() { python3 - "$STATE" "$1" "$2" <<'PY'
import json,sys,time
p,phase,instance=sys.argv[1:]
old={}
try: old=json.load(open(p))
except Exception: pass
old.update({"run_id":"phase39-relational-readout-20261004-r1","phase":phase,"instance_id":instance or old.get("instance_id"),"updated_at":time.time()})
tmp=p+'.tmp'; open(tmp,'w').write(json.dumps(old,sort_keys=True,indent=2)+'\n'); __import__('os').replace(tmp,p)
PY
}
destroy_owned() {
  local id; id="$(owned_id)"
  if [[ -z "$id" ]]; then log "cleanup: no owned instance recorded"; return 0; fi
  log "cleanup: requesting destroy for owned instance $id"
  for attempt in 1 2 3; do
    vastai destroy instance "$id" -y --raw >"$ROOT/manifests/destroy-${attempt}.json" 2>>"$LOG" || true
    vastai show instances --raw >"$ROOT/manifests/post-destroy-${attempt}.json" 2>>"$LOG" || true
    if python3 - "$ROOT/manifests/post-destroy-${attempt}.json" "$id" <<'PY'
import json,sys
try: data=json.load(open(sys.argv[1]))
except Exception: raise SystemExit(1)
text=json.dumps(data)
raise SystemExit(0 if sys.argv[2] not in text else 1)
PY
    then record_state "DESTROYED_VERIFIED" "$id"; log "cleanup: instance $id absent"; return 0; fi
    sleep 5
  done
  record_state "DESTROY_UNCONFIRMED" "$id"; log "EMERGENCY: destruction unconfirmed for $id"; return 1
}
trap 'status=$?; if [[ "${PHASE39_KEEP_INSTANCE:-0}" != "1" ]]; then destroy_owned || true; fi; exit $status' EXIT INT TERM
case "${1:-}" in
  preflight)
    test -f "$ROOT/manifests/frozen-manifest.json"
    test -f "$ROOT/frozen-corpus.json"
    test -f "$ROOT/source/phase39_remote_capture.py"
    test -r /home/nyx/.config/vastai/vast_api_key
    test "$(stat -c '%a' /home/nyx/.config/vastai/vast_api_key)" = 600
    vastai show instances --raw >"$ROOT/manifests/preflight-instances.json"
    vastai show ssh-keys --raw >"$ROOT/manifests/preflight-ssh-keys.json"
    log "preflight complete; no resource created"
    ;;
  destroy)
    PHASE39_KEEP_INSTANCE=1 destroy_owned
    ;;
  *) echo "usage: $0 {preflight|destroy}" >&2; exit 64;;
esac
