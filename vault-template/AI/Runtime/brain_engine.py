#!/usr/bin/env python3
"""Living Brain v0.1 — runtime engine (Phase 1-5 mechanics).

Stdlib-only. Not wired to any hook — running it does not change session behavior.
Store: ~/.brain-runtime (override with the BRAIN_RUNTIME env var; the self-test
uses an isolated temp dir).

Scope:
  Phase 1  append_event / working memory delta / session resume
  Phase 2  activation() + progressive_retrieve() (activation formula + thresholds)
  Phase 3  open_decision() / close_decision() + prediction_error
  Phase 4  synaptic weight update + eligibility + independence
  Phase 5  suppression + pruning
  +        salience()

The concrete weights/thresholds below mirror the cognitive-layer policy files
(AI/Cognition/*, AI/Memory/*). Change them in one place if you retune.
"""
import json
import math
import os
import sqlite3

RUNTIME = os.environ.get("BRAIN_RUNTIME", os.path.expanduser("~/.brain-runtime"))

# ---- activation weights (see AI/Memory/synaptic-policy.md) ----
ACTIVATION_W = {
    "base_activation": 0.04, "semantic_similarity": 0.25, "tag_match": 0.10,
    "description_match": 0.10, "explicit_link_signal": 0.13, "project_context_signal": 0.15,
    "recency_signal": 0.05, "coactivation_signal": 0.06, "reliability_signal": 0.08,
    "novelty_signal": 0.04,
    "contradiction_inhibition": 0.40, "project_mismatch": 0.35, "deprecated_penalty": 0.60,
    "token_cost_penalty": 0.15, "refractory_penalty": 0.40,
}
POSITIVE = {"base_activation", "semantic_similarity", "tag_match", "description_match",
            "explicit_link_signal", "project_context_signal", "recency_signal",
            "coactivation_signal", "reliability_signal", "novelty_signal"}

# ---- progressive retrieval thresholds ----
THRESHOLDS = {"ignore_below": 0.35, "frontmatter": 0.50, "matching_section": 0.65,
              "adjacent_sections": 0.78, "full_concept": 0.88}

# ---- plasticity ----
PLASTICITY = {"positive_lr": 0.10, "negative_lr": 0.14, "coactivation_lr": 0.03,
              "decay_daily": 0.002, "deprecated_penalty": 0.60}

# ---- eligibility ----
ELIGIBILITY = {"direct_used_in_action": 1.00, "influenced_decision": 0.80,
               "used_in_verification": 0.65, "background_context_only": 0.15, "not_used": 0.00}

# ---- salience weights (see AI/Cognition/attention-and-salience.md) ----
SALIENCE_W = {"goal_relevance": 0.25, "novelty": 0.10, "prediction_error": 0.20,
              "threat": 0.15, "user_emphasis": 0.15, "unresolved_conflict": 0.10,
              "expected_information_gain": 0.05, "repetition": -0.10, "low_impact": -0.10}

WEIGHT_MAX = 0.95


def _p(name):
    return os.path.join(RUNTIME, name)


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


# ---------- Phase 1: event bus + working memory ----------
def append_event(ev):
    """Append an event to the append-only ledger. summary is clipped to 280 chars."""
    os.makedirs(RUNTIME, exist_ok=True)
    if "summary" in ev:
        ev["summary"] = ev["summary"][:280]
    with open(_p("cognitive-events.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")


def read_events(session_id=None):
    path = _p("cognitive-events.jsonl")
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            if session_id is None or e.get("session_id") == session_id:
                out.append(e)
    return out


def update_working_memory(delta):
    """Delta update — partial update instead of full rewrite."""
    path = _p("working-memory.json")
    wm = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            wm = json.load(f)
    wm.update(delta)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(wm, f, ensure_ascii=False, indent=2)
    return wm


def resume_state(session_id):
    """Phase 1 success condition: resume from ledger + working memory, no transcript."""
    wm_path = _p("working-memory.json")
    wm = {}
    if os.path.exists(wm_path):
        with open(wm_path, encoding="utf-8") as f:
            wm = json.load(f)
    events = read_events(session_id)
    return {
        "focus": wm.get("focus"),
        "next_action": wm.get("next_action"),
        "event_count": len(events),
        "last_event": events[-1]["type"] if events else None,
    }


# ---------- Phase 2: activation + progressive retrieval ----------
def activation(signals):
    """A(node) = Sum(positive) - Sum(penalties), clamped 0..1."""
    a = 0.0
    for k, w in ACTIVATION_W.items():
        v = signals.get(k, 0.0)
        a += (w * v) if k in POSITIVE else -(w * v)
    return _clamp(a)


def retrieval_level(a, dynamic_adjust=0.0):
    """Reading depth from score. dynamic_adjust: context pressure etc."""
    a = a - dynamic_adjust
    if a < THRESHOLDS["ignore_below"]:
        return "ignore"
    if a < THRESHOLDS["matching_section"]:
        return "frontmatter"
    if a < THRESHOLDS["adjacent_sections"]:
        return "matching_section"
    if a < THRESHOLDS["full_concept"]:
        return "adjacent_sections"
    return "full_concept"


def progressive_retrieve(candidates, dynamic_adjust=0.0, max_full=1):
    """Score candidates, assign a level, cap full-concept reads at max_full."""
    scored = [(c["ref"], activation(c["signals"])) for c in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    out, full_used = [], 0
    for ref, a in scored:
        lvl = retrieval_level(a, dynamic_adjust)
        if lvl == "full_concept":
            if full_used >= max_full:
                lvl = "adjacent_sections"
            else:
                full_used += 1
        if lvl != "ignore":
            out.append({"ref": ref, "activation": round(a, 3), "level": lvl})
    return out


# ---------- Phase 3: decision episode + prediction error ----------
def open_decision(dec):
    dec.setdefault("outcome", None)
    dec.setdefault("prediction_error", None)
    dec["status"] = "open"
    return dec


def close_decision(dec, outcome, observed_value):
    """prediction_error = observed - predicted."""
    predicted = dec["prediction"]["success_probability"]
    dec["outcome"] = outcome
    dec["prediction_error"] = round(observed_value - predicted, 3)
    dec["status"] = "verified"
    return dec


# ---------- salience ----------
def salience(signals):
    s = sum(w * signals.get(k, 0.0) for k, w in SALIENCE_W.items())
    return _clamp(s)


# ---------- Phase 4: synaptic store + weight update ----------
def _connect(db=None):
    conn = sqlite3.connect(db or _p("synaptic-state.sqlite"))
    conn.execute("""CREATE TABLE IF NOT EXISTS synapse(
        source TEXT, target TEXT, relation TEXT,
        weight REAL, success_count INTEGER DEFAULT 0, failure_count INTEGER DEFAULT 0,
        contradiction_conf REAL DEFAULT 0, last_use TEXT, unique_info INTEGER DEFAULT 1,
        status TEXT DEFAULT 'active',
        PRIMARY KEY(source, target, relation))""")
    return conn


def upsert_synapse(conn, source, target, relation, weight):
    conn.execute("""INSERT OR IGNORE INTO synapse(source,target,relation,weight)
                    VALUES(?,?,?,?)""", (source, target, relation, weight))
    conn.commit()


def update_weight(conn, source, target, relation, reward, eligibility,
                  confidence, independence):
    """dw = lr * reward * eligibility * confidence * independence.
    Credit only when eligibility >= 0.30. Negative reward uses negative_lr."""
    if eligibility < 0.30:
        return None
    lr = PLASTICITY["positive_lr"] if reward >= 0 else PLASTICITY["negative_lr"]
    dw = lr * reward * eligibility * confidence * independence
    row = conn.execute("SELECT weight,success_count,failure_count FROM synapse "
                       "WHERE source=? AND target=? AND relation=?",
                       (source, target, relation)).fetchone()
    if row is None:
        return None
    w_old, sc, fc = row
    w_new = _clamp(w_old + dw, 0.0, WEIGHT_MAX)
    if reward >= 0:
        sc += 1
    else:
        fc += 1
    conn.execute("UPDATE synapse SET weight=?,success_count=?,failure_count=? "
                 "WHERE source=? AND target=? AND relation=?",
                 (w_new, sc, fc, source, target, relation))
    conn.commit()
    return round(w_new, 4)


# ---------- Phase 5: consolidation (suppression + pruning) ----------
def consolidate(conn, last_use_days=None):
    """Suppression + pruning. Critical records are never deleted -> 'archived'."""
    suppressed = pruned = 0
    for row in conn.execute("SELECT source,target,relation,weight,success_count,"
                            "failure_count,contradiction_conf,unique_info FROM synapse "
                            "WHERE status='active'").fetchall():
        src, tgt, rel, w, sc, fc, cc, uniq = row
        if (fc >= 2 and sc == 0) or cc >= 0.80:
            conn.execute("UPDATE synapse SET status='suppressed' WHERE source=? AND target=? AND relation=?",
                         (src, tgt, rel))
            suppressed += 1
            continue
        old = last_use_days.get((src, tgt, rel), 0) if last_use_days else 0
        if w < 0.10 and old > 90 and sc == 0 and uniq == 0:
            conn.execute("UPDATE synapse SET status='archived' WHERE source=? AND target=? AND relation=?",
                         (src, tgt, rel))
            pruned += 1
    conn.commit()
    return {"suppressed": suppressed, "archived": pruned}


# ---------- self-test: verify each phase's success condition ----------
def selftest():
    import tempfile
    global RUNTIME
    orig = RUNTIME
    RUNTIME = tempfile.mkdtemp(prefix="brain-engine-test-")
    results = []
    try:
        # Phase 1
        sid = "test-session"
        append_event({"event_id": "e1", "type": "session.started", "session_id": sid,
                      "summary": "x" * 400, "confidence": 0.99})
        update_working_memory({"focus": "P1 test", "next_action": "try resume"})
        append_event({"event_id": "e2", "type": "action.executed", "session_id": sid, "summary": "work"})
        r = resume_state(sid)
        ev1 = read_events(sid)[0]
        ok1 = (r["event_count"] == 2 and r["focus"] == "P1 test"
               and r["next_action"] == "try resume" and len(ev1["summary"]) == 280)
        results.append(("Phase1 event+wm+resume (no transcript) + 280-clip", ok1))

        # Phase 2
        hi = activation({"semantic_similarity": 0.92, "tag_match": 0.8, "project_context_signal": 1.0,
                         "explicit_link_signal": 1.0, "reliability_signal": 0.9})
        lo = activation({"semantic_similarity": 0.1, "deprecated_penalty": 1.0, "project_mismatch": 1.0})
        ret = progressive_retrieve([
            {"ref": "hi#a", "signals": {"semantic_similarity": 1.0, "project_context_signal": 1.0,
                                        "explicit_link_signal": 1.0, "tag_match": 1.0, "reliability_signal": 1.0,
                                        "description_match": 1.0, "recency_signal": 1.0, "coactivation_signal": 1.0}},
            {"ref": "mid#b", "signals": {"semantic_similarity": 0.6, "tag_match": 0.5}},
            {"ref": "lo#c", "signals": {"semantic_similarity": 0.05, "deprecated_penalty": 1.0}},
        ], max_full=1)
        full_ct = sum(1 for x in ret if x["level"] == "full_concept")
        dropped = all(x["ref"] != "lo#c" for x in ret)
        ok2 = (hi > lo and 0.0 <= hi <= 1.0 and full_ct <= 1 and dropped)
        results.append(("Phase2 activation ranking + full-concept<=1 + low-score drop", ok2))

        # Phase 3
        dec = open_decision({"decision_id": "d1", "prediction": {"success_probability": 0.75}})
        dec = close_decision(dec, {"coverage": 0.4}, 0.40)
        ok3 = (dec["status"] == "verified" and abs(dec["prediction_error"] - (-0.35)) < 1e-9)
        results.append(("Phase3 decision episode + prediction_error=-0.35", ok3))

        # Phase 4
        conn = _connect(_p("synaptic-state.sqlite"))
        upsert_synapse(conn, "A", "B", "supports", 0.40)
        w_pos = update_weight(conn, "A", "B", "supports", reward=0.85, eligibility=1.0,
                              confidence=0.9, independence=1.0)
        upsert_synapse(conn, "C", "D", "supports", 0.40)
        w_bg = update_weight(conn, "C", "D", "supports", reward=0.85, eligibility=0.15,
                             confidence=0.9, independence=1.0)  # eligibility<0.30 -> no credit
        upsert_synapse(conn, "E", "F", "causes", 0.50)
        w_neg = update_weight(conn, "E", "F", "causes", reward=-0.8, eligibility=0.8,
                              confidence=0.9, independence=1.0)
        ok4 = (w_pos > 0.40 and w_bg is None and w_neg < 0.50 and w_pos <= WEIGHT_MAX)
        results.append(("Phase4 weight up on success, down on failure, eligibility<0.30 no-credit, clamp<=0.95", ok4))

        # Phase 5
        upsert_synapse(conn, "G", "H", "predicts", 0.30)
        conn.execute("UPDATE synapse SET failure_count=2, success_count=0 WHERE source='G'")
        conn.commit()
        cons = consolidate(conn)
        g_status = conn.execute("SELECT status FROM synapse WHERE source='G'").fetchone()[0]
        ok5 = (cons["suppressed"] >= 1 and g_status == "suppressed")
        results.append(("Phase5 suppression (failure>=2 & success=0)", ok5))
        conn.close()
    finally:
        import shutil
        shutil.rmtree(RUNTIME, ignore_errors=True)
        RUNTIME = orig

    print("Living Brain engine self-test:")
    for name, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    all_ok = all(ok for _, ok in results)
    print(f"RESULT: {'ALL PHASES PASS' if all_ok else 'FAILED'} ({sum(ok for _,ok in results)}/{len(results)})")
    return all_ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if selftest() else 1)
