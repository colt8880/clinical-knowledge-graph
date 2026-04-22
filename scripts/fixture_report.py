"""Generate HTML fixture inspection reports from Braintrust experiment data.

Usage:
    cd evals

    # Single fixture
    uv run python ../scripts/fixture_report.py --run v2-phase1 --fixture cross-domain/case-08

    # All fixtures
    uv run python ../scripts/fixture_report.py --run v2-phase1 --all

    # Only specific arms
    uv run python ../scripts/fixture_report.py --run v2-phase1 --all --arms b,c

    # Multiple runs side by side
    uv run python ../scripts/fixture_report.py --run v2-phase1 --run v1-thesis --all
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

EVALS_ROOT = Path(__file__).resolve().parent.parent / "evals"
FIXTURES_ROOT = EVALS_ROOT / "fixtures"
ALL_ARM_IDS = ["a", "b", "c"]
ARM_LABELS = {"a": "Arm A — Vanilla LLM", "b": "Arm B — Flat RAG", "c": "Arm C — Graph Context"}
ARM_COLORS = {"a": "#6b7280", "b": "#2563eb", "c": "#059669"}

DIMENSIONS = ["completeness", "clinical_appropriateness", "prioritization", "integration"]

DIMENSION_DEFS = {
    "completeness": "Are all expected actions present?\n5 — All present\n4 — One minor action missing\n3 — One clinically relevant action missing\n2 — Multiple expected actions missing\n1 — Most missing or incoherent",
    "clinical_appropriateness": "Are recommendations safe and correct?\n5 — All appropriate, no contraindications\n4 — All appropriate, minor imprecision\n3 — One questionable but not harmful\n2 — One contraindicated or wrong\n1 — Multiple dangerous recommendations",
    "prioritization": "Is sequencing reasonable?\n5 — Ordered by clinical impact\n4 — Reasonable, one minor issue\n3 — Partially correct, key action misordered\n2 — Largely incorrect ordering\n1 — No coherent ordering",
    "integration": "Cross-guideline interactions handled?\n5 — Correctly identified and resolved\n4 — Mostly correct, one minor gap\n3 — Some missed, no harmful conflicts\n2 — Significant conflicts unresolved\n1 — Interactions ignored entirely",
}


def _denormalize(val: float) -> float:
    return (val * 4) + 1


# ---------------------------------------------------------------------------
# Braintrust data fetching
# ---------------------------------------------------------------------------

def _fetch_experiment_spans(run_name: str, arm_id: str) -> dict:
    """Fetch all spans for one experiment, indexed by fixture_id.

    Returns {fixture_id: {"output": ..., "scores": ..., "input": ..., "expected": ..., "scorer_meta": ...}}
    """
    import httpx

    api_key = os.environ.get("BRAINTRUST_API_KEY")
    if not api_key:
        print("BRAINTRUST_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    base = "https://api.braintrust.dev/v1"
    headers = {"Authorization": f"Bearer {api_key}"}

    experiment_name = f"{run_name}-arm-{arm_id}"
    r = httpx.get(
        f"{base}/experiment",
        headers=headers,
        params={"project_name": "clinical-knowledge-graph", "experiment_name": experiment_name},
    )
    exps = r.json().get("objects", [])
    if not exps:
        print(f"Warning: experiment '{experiment_name}' not found", file=sys.stderr)
        return {}
    exp_id = exps[0]["id"]

    r2 = httpx.post(
        f"{base}/experiment/{exp_id}/fetch",
        headers=headers,
        json={"limit": 500},
    )
    events = r2.json().get("events", [])

    eval_spans = {}
    task_spans = {}
    scorer_spans = {}
    for ev in events:
        sa = ev.get("span_attributes", {})
        rid = ev.get("root_span_id", "")
        if sa.get("type") == "eval" and ev.get("is_root"):
            eval_spans[rid] = ev
        elif sa.get("type") == "task":
            task_spans[rid] = ev
        elif sa.get("purpose") == "scorer":
            scorer_spans[rid] = ev

    results = {}
    for rid, eval_span in eval_spans.items():
        meta = eval_span.get("metadata") or {}
        fid = meta.get("fixture_id", "")
        if not fid:
            continue

        task_span = task_spans.get(rid, {})
        task_output = task_span.get("output", {})

        scorer_span = scorer_spans.get(rid, {})
        scores_raw = scorer_span.get("scores") or {}
        scorer_meta = scorer_span.get("metadata") or {}

        dim_scores = {}
        for dim in DIMENSIONS:
            raw = scores_raw.get(dim, 0)
            dim_scores[dim] = round(_denormalize(raw), 1)
        composite_raw = scores_raw.get("composite", 0)
        dim_scores["composite"] = round(_denormalize(composite_raw), 2)

        results[fid] = {
            "input": eval_span.get("input", {}),
            "output": task_output,
            "expected": eval_span.get("expected", {}),
            "scores": dim_scores,
            "scorer_meta": scorer_meta,
        }

    return results


def fetch_all_data(run_name: str, arm_ids: list[str]) -> dict:
    """Fetch all experiment data for a run.

    Returns {fixture_id: {arm_id: {output, scores, ...}}}
    """
    all_data: dict[str, dict] = {}

    for arm_id in arm_ids:
        print(f"  Fetching {run_name} arm {arm_id.upper()}...", file=sys.stderr)
        arm_data = _fetch_experiment_spans(run_name, arm_id)
        for fid, data in arm_data.items():
            if fid not in all_data:
                all_data[fid] = {}
            all_data[fid][arm_id] = data

    return all_data


def fetch_fixture_data(run_name: str, fixture_id: str, arm_ids: list[str]) -> dict:
    """Fetch data for one fixture across specified arms."""
    arms = {}
    for arm_id in arm_ids:
        arm_data = _fetch_experiment_spans(run_name, arm_id)
        if fixture_id in arm_data:
            arms[arm_id] = arm_data[fixture_id]
    return arms


# ---------------------------------------------------------------------------
# Fixture loading
# ---------------------------------------------------------------------------

def discover_fixtures() -> list[str]:
    """Discover all fixture IDs on disk."""
    fixtures = []
    for guideline_dir in sorted(FIXTURES_ROOT.iterdir()):
        if not guideline_dir.is_dir() or guideline_dir.name.startswith(".") or guideline_dir.name == "archive":
            continue
        for case_dir in sorted(guideline_dir.iterdir()):
            if not case_dir.is_dir():
                continue
            has_patient = any((case_dir / n).exists() for n in ("patient.json", "patient-context.json"))
            if has_patient and (case_dir / "expected-actions.json").exists():
                fixtures.append(f"{guideline_dir.name}/{case_dir.name}")
    return fixtures


def load_fixture_files(fixture_id: str) -> tuple[dict, dict]:
    """Load patient context and expected actions from disk."""
    fixture_dir = FIXTURES_ROOT / fixture_id
    for name in ("patient.json", "patient-context.json"):
        p = fixture_dir / name
        if p.exists():
            patient = json.loads(p.read_text())
            break
    else:
        raise FileNotFoundError(f"No patient file in {fixture_dir}")
    expected = json.loads((fixture_dir / "expected-actions.json").read_text())
    return patient, expected


def classify_fixture(fid: str) -> str:
    return "multi-guideline" if fid.startswith("cross-domain/") else "single-guideline"


# ---------------------------------------------------------------------------
# HTML rendering helpers
# ---------------------------------------------------------------------------

def _json_block(data: object) -> str:
    text = json.dumps(data, indent=2, default=str)
    escaped = html.escape(text)
    return f'<pre class="json-block"><code>{escaped}</code></pre>'


def _score_bar(score: float, max_score: float = 5.0) -> str:
    pct = (score / max_score) * 100
    color = "#059669" if score >= 4 else "#d97706" if score >= 3 else "#dc2626"
    return (
        f'<div class="score-bar-container">'
        f'<div class="score-bar" style="width:{pct}%;background:{color}"></div>'
        f'<span class="score-label">{score:.1f}</span>'
        f'</div>'
    )


def _extract_actions(output: dict) -> list[dict]:
    if not output:
        return []
    parsed = output.get("parsed", output)
    if isinstance(parsed, dict):
        for key in ("actions", "recommendations", "recommended_actions"):
            if key in parsed:
                val = parsed[key]
                if isinstance(val, list):
                    return val
        return [parsed]
    if isinstance(parsed, list):
        return parsed
    return []


def _render_rag_chunks(chunks: list) -> str:
    if not chunks:
        return '<p class="muted">No chunks retrieved.</p>'
    lines = [f'<div class="context-detail"><p class="muted">{len(chunks)} retrieved sections</p>']
    for i, chunk in enumerate(chunks):
        if isinstance(chunk, dict):
            source = chunk.get("source", chunk.get("guideline", ""))
            section = chunk.get("section", chunk.get("title", ""))
            text = chunk.get("text", chunk.get("content", json.dumps(chunk, default=str)))
            header = f"{source}: {section}" if source and section else source or section or f"Chunk {i+1}"
            lines.append(
                f'<details{"" if i > 0 else " open"}>'
                f'<summary class="chunk-header">{html.escape(str(header))}</summary>'
                f'<div class="chunk-text">{html.escape(str(text)[:1000])}</div>'
                f'</details>'
            )
        else:
            lines.append(f'<details><summary>Chunk {i+1}</summary><div class="chunk-text">{html.escape(str(chunk)[:1000])}</div></details>')
    lines.append('</div>')
    return "\n".join(lines)


def _render_graph_context(gc: dict) -> str:
    lines = ['<div class="context-detail">']

    conv = gc.get("convergence_summary", {})
    conv_prose = conv.get("convergence_prose", "")
    if conv_prose:
        lines.append('<div class="context-block"><h5>Convergence</h5>')
        for para in conv_prose.split("\n"):
            if para.strip():
                lines.append(f'<p>{html.escape(para.strip())}</p>')
        lines.append('</div>')

    grouped = conv.get("grouped_convergence", [])
    for group in grouped:
        tc = group.get("therapeutic_class", "Unknown class")
        members = group.get("members", [])
        recommended_by = group.get("recommended_by", [])
        lines.append(f'<div class="convergence-group"><h5>{html.escape(str(tc))}</h5>')
        if recommended_by:
            lines.append('<div class="rec-sources">')
            for rb in recommended_by:
                gl = rb.get("guideline", "?")
                grade = rb.get("evidence_grade", "?")
                lines.append(f'<span class="source-badge">{html.escape(str(gl))} ({html.escape(str(grade))})</span>')
            lines.append('</div>')
        intensity = group.get("intensity_details", [])
        if intensity:
            lines.append('<div class="intensity-details">')
            for det in intensity:
                lines.append(f'<div class="intensity-row"><span class="muted">{html.escape(str(det.get("guideline","?")))}:</span> {html.escape(str(det.get("strategy_name","?")))}</div>')
            lines.append('</div>')
        if members:
            lines.append(f'<div class="muted" style="margin-top:0.25rem">Medications: {html.escape(", ".join(str(m) for m in members))}</div>')
        lines.append('</div>')

    ts = gc.get("trace_summary", {})
    if ts:
        matched = ts.get("matched_recs", [])
        if matched:
            lines.append(f'<div class="context-block"><h5>Matched Recommendations ({len(matched)})</h5>')
            for rec in matched:
                if isinstance(rec, dict):
                    rec_id = rec.get("recommendation_id", rec.get("rec_id", rec.get("label", rec.get("id", "?"))))
                    display_name = rec_id.replace("rec:", "").replace("-", " ").replace("_", " ").title()
                    gl = rec.get("guideline_id", rec.get("guideline", "")).replace("guideline:", "").replace("-", " ").replace("_", " ").title()
                    grade = rec.get("evidence_grade", "")
                    status = rec.get("status", "")
                    reason = rec.get("reason", "")
                    status_badge = f' <span class="status-badge status-{status}">{status}</span>' if status else ""
                    tag = f' <span class="source-badge">{html.escape(str(gl))} ({html.escape(str(grade))})</span>' if gl else ""
                    lines.append(f'<div class="matched-rec"><div>{html.escape(display_name)}{status_badge}{tag}</div>')
                    if reason:
                        lines.append(f'<div class="action-rationale">{html.escape(str(reason))}</div>')
                    lines.append('</div>')
                else:
                    lines.append(f'<div class="matched-rec">{html.escape(str(rec))}</div>')
            lines.append('</div>')

        preemption = ts.get("preemption_prose", "")
        if preemption:
            lines.append(f'<div class="preemption-block"><h5>&#x26D4; Preemption</h5><p>{html.escape(str(preemption))}</p></div>')
        modifier = ts.get("modifier_prose", "")
        if modifier:
            lines.append(f'<div class="modifier-block"><h5>&#x26A0; Modifier</h5><p>{html.escape(str(modifier))}</p></div>')

    subgraph = gc.get("subgraph", {})
    rendered = subgraph.get("rendered_prose", "")
    if rendered:
        lines.append(f'<details><summary>Full evaluation prose</summary><div class="chunk-text">{html.escape(str(rendered))}</div></details>')

    lines.append(f'<details><summary>Raw graph context JSON</summary>{_json_block(gc)}</details>')
    lines.append('</div>')
    return "\n".join(lines)


def _render_arm_actions(arm_actions: list[dict]) -> str:
    if not arm_actions:
        return '<p class="muted">No actions in output.</p>'
    lines = []
    for i, a in enumerate(arm_actions):
        label = a.get("label", a.get("id", f"Action {i+1}"))
        rationale = a.get("rationale", "")
        priority = a.get("priority", "")
        source = a.get("source", a.get("source_rec_id", ""))
        priority_badge = f'<span class="priority-badge">P{priority}</span> ' if priority else ""
        source_tag = f'<div class="action-source">{html.escape(str(source))}</div>' if source else ""
        lines.append(
            f'<div class="action-item">'
            f'<div class="action-header">{priority_badge}<strong>{html.escape(str(label))}</strong></div>'
            f'<p class="action-rationale">{html.escape(str(rationale)[:300])}</p>'
            f'{source_tag}</div>'
        )
    return "\n".join(lines)


def _patient_age(patient: dict) -> str:
    dob = patient.get("patient", {}).get("date_of_birth", "")
    if not dob:
        return "?"
    try:
        from datetime import date
        birth = date.fromisoformat(dob)
        eval_time = patient.get("evaluation_time", "")
        eval_date = date.fromisoformat(eval_time[:10]) if eval_time else date.today()
        return str(eval_date.year - birth.year - ((eval_date.month, eval_date.day) < (birth.month, birth.day)))
    except Exception:
        return "?"


def _patient_conditions(patient: dict) -> str:
    return ", ".join(c["codes"][0].get("display", "?") for c in patient.get("conditions", []) if c.get("codes")) or "None"


def _patient_labs(patient: dict) -> str:
    labs = []
    for o in patient.get("observations", []):
        codes = o.get("codes", [])
        display = codes[0].get("display", "") if codes else ""
        vq = (o.get("value") or {}).get("value_quantity", {})
        if vq:
            short = display.split("[")[0].split("/")[0].strip()[:20]
            labs.append(f"{short}: {vq.get('value', '')} {vq.get('unit', '')}")
    return "; ".join(labs[:4]) or "None"


def _patient_meds(patient: dict) -> str:
    return ", ".join(m["codes"][0].get("display", "?") for m in patient.get("medications", []) if m.get("codes")) or "None"


def _patient_risk(patient: dict) -> str:
    rs = patient.get("risk_scores", {}).get("ascvd_10yr", {})
    return f"{rs.get('value', '?')}%" if rs else "N/A"


# ---------------------------------------------------------------------------
# Single-fixture HTML
# ---------------------------------------------------------------------------

def _render_fixture_section(
    fixture_id: str,
    patient: dict,
    expected: dict,
    arms: dict,
    arm_ids: list[str],
    collapsed: bool = False,
) -> str:
    """Render one fixture as an HTML section (used both standalone and in multi-fixture reports)."""
    description = expected.get("description", "")
    expected_actions = expected.get("actions", [])
    contraindications = expected.get("contraindications", [])
    subset = classify_fixture(fixture_id)

    # Build arm cards
    arm_cards = []
    for arm_id in arm_ids:
        if arm_id not in arms:
            continue
        arm = arms[arm_id]
        label = ARM_LABELS[arm_id]
        color = ARM_COLORS[arm_id]
        scores = arm.get("scores", {})
        output = arm.get("output", {})

        score_html = ""
        for dim in DIMENSIONS:
            dim_label = dim.replace("_", " ").title()
            tooltip = html.escape(DIMENSION_DEFS.get(dim, ""), quote=True)
            score_html += (
                f'<div class="score-row">'
                f'<span class="score-dim">{dim_label}<span class="dim-help" title="{tooltip}">?</span></span>'
                f'{_score_bar(scores.get(dim, 0))}'
                f'</div>'
            )
        score_html += f'<div class="score-row composite"><span class="score-dim">Composite</span>{_score_bar(scores.get("composite", 0))}</div>'

        raw_output = output.get("raw_output", "")
        arm_actions = _extract_actions(output)

        # Judge rationale
        scorer_meta = arm.get("scorer_meta", {})
        rationale_parts = []
        for dim in DIMENSIONS:
            dim_meta = scorer_meta.get(dim, {})
            rat = dim_meta.get("rationale", "")
            if rat:
                dim_label = dim.replace("_", " ").title()
                rationale_parts.append(f'<div class="rationale-item"><strong>{dim_label}:</strong> {html.escape(str(rat))}</div>')

        rationale_html = "\n".join(rationale_parts) if rationale_parts else '<p class="muted">No rationale stored.</p>'

        context_html = ""
        if arm_id == "a":
            context_html = '<p class="context-note">Patient context only (no guideline material)</p>'
        elif arm_id == "b":
            chunks_used = output.get("chunks_used", None)
            chunks_list = output.get("chunks", output.get("retrieved_chunks", []))
            if isinstance(chunks_list, list) and chunks_list:
                context_html = _render_rag_chunks(chunks_list)
            elif chunks_used:
                context_html = f'<p class="context-note">Patient context + {chunks_used} retrieved RAG sections (section-level chunking + multi-query retrieval). Chunk content not stored in experiment output.</p>'
            else:
                context_html = '<p class="context-note">Patient context + flat RAG chunks (chunk content not stored)</p>'
        elif arm_id == "c":
            gc = output.get("graph_context", {})
            if gc:
                context_html = _render_graph_context(gc)
            else:
                context_html = '<p class="context-note">Graph context (not captured in output)</p>'

        actions_html = _render_arm_actions(arm_actions)

        arm_cards.append(f"""
        <div class="arm-card" style="border-top: 4px solid {color}">
            <h3 style="color:{color}">{label}</h3>
            <div class="scores-section">
                <h4>Scores</h4>
                {score_html}
            </div>
            <div class="section">
                <h4>Judge Rationale</h4>
                <div class="rationale-box">{rationale_html}</div>
            </div>
            <div class="section">
                <h4>Recommended Actions ({len(arm_actions)})</h4>
                {actions_html}
            </div>
            <div class="section">
                <h4>Context Provided</h4>
                <div class="context-box">{context_html}</div>
            </div>
            <div class="section">
                <h4>Raw LLM Output</h4>
                <details><summary>Show raw output</summary><pre class="output-block">{html.escape(raw_output[:5000])}</pre></details>
            </div>
        </div>
        """)

    # Composite scores summary line
    score_summary_parts = []
    for arm_id in arm_ids:
        if arm_id in arms:
            comp = arms[arm_id].get("scores", {}).get("composite", 0)
            color = ARM_COLORS[arm_id]
            score_summary_parts.append(f'<span style="color:{color};font-weight:600">{arm_id.upper()}: {comp:.1f}</span>')
    score_summary = " &nbsp;|&nbsp; ".join(score_summary_parts)

    subset_badge = f'<span class="subset-badge subset-{subset.replace("-", "_")}">{subset}</span>'

    open_attr = "" if collapsed else " open"

    return f"""
    <details class="fixture-section"{open_attr} id="fixture-{fixture_id.replace('/', '-')}">
        <summary class="fixture-header">
            <span class="fixture-title">{fixture_id}</span>
            {subset_badge}
            <span class="fixture-scores">{score_summary}</span>
        </summary>
        <div class="fixture-body">
            <div class="description">{html.escape(description)}</div>

            <div class="two-col">
                <div>
                    <h4>Patient Summary</h4>
                    <div class="patient-summary">
                        <div class="patient-grid">
                            <div class="patient-item"><div class="label">Age / Sex</div><div class="value">{_patient_age(patient)} / {patient.get('patient', {}).get('administrative_sex', '?').upper()}</div></div>
                            <div class="patient-item"><div class="label">Conditions</div><div class="value">{_patient_conditions(patient)}</div></div>
                            <div class="patient-item"><div class="label">Key Labs</div><div class="value">{_patient_labs(patient)}</div></div>
                            <div class="patient-item"><div class="label">Medications</div><div class="value">{_patient_meds(patient)}</div></div>
                            <div class="patient-item"><div class="label">ASCVD 10yr</div><div class="value">{_patient_risk(patient)}</div></div>
                        </div>
                        <details style="margin-top:0.5rem"><summary>Full patient context JSON</summary>{_json_block(patient)}</details>
                    </div>
                </div>
                <div>
                    <h4>Expected Actions</h4>
                    <div class="expected-section">
                        {''.join(f'<div style="margin-bottom:0.5rem"><strong>{i+1}. {html.escape(a.get("label",""))}</strong><br><span class="muted">{html.escape(a.get("rationale","")[:150])}</span></div>' for i, a in enumerate(expected_actions))}
                        {('<h4 style="margin-top:0.75rem">Contraindications</h4>' + ''.join(f'<div style="margin-bottom:0.4rem"><strong>&#x26D4; {html.escape(c.get("label",""))}</strong><br><span class="muted">{html.escape(c.get("rationale","")[:150])}</span></div>' for c in contraindications)) if contraindications else ''}
                    </div>
                </div>
            </div>

            <div class="arms-grid arms-grid-{len(arm_ids)}">
                {''.join(arm_cards)}
            </div>
        </div>
    </details>
    """


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

def _render_summary_table(all_fixtures: list[str], all_arms_data: dict, arm_ids: list[str]) -> str:
    """Render an aggregate summary table: mean scores per arm, broken out by subset."""
    # Collect scores by (arm, subset)
    from collections import defaultdict
    arm_subset_scores: dict[tuple[str, str], list[dict]] = defaultdict(list)
    arm_all_scores: dict[str, list[dict]] = defaultdict(list)

    for fid in all_fixtures:
        arms = all_arms_data.get(fid, {})
        subset = classify_fixture(fid)
        for arm_id in arm_ids:
            if arm_id in arms:
                scores = arms[arm_id].get("scores", {})
                arm_subset_scores[(arm_id, subset)].append(scores)
                arm_all_scores[arm_id].append(scores)

    def _mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0

    def _score_cell(score: float) -> str:
        color = "#059669" if score >= 4 else "#d97706" if score >= 3 else "#dc2626"
        return f'<strong style="color:{color}">{score:.2f}</strong>'

    # Build rows: one per arm, columns = composite (all), composite (multi), composite (single), then per-dimension (all)
    rows = []
    for arm_id in arm_ids:
        all_composites = [s.get("composite", 0) for s in arm_all_scores[arm_id]]
        multi_composites = [s.get("composite", 0) for s in arm_subset_scores[(arm_id, "multi-guideline")]]
        single_composites = [s.get("composite", 0) for s in arm_subset_scores[(arm_id, "single-guideline")]]

        dim_means = {d: _mean([s.get(d, 0) for s in arm_all_scores[arm_id]]) for d in DIMENSIONS}

        n_all = len(all_composites)
        n_multi = len(multi_composites)
        n_single = len(single_composites)

        cells = [
            f'<td style="color:{ARM_COLORS[arm_id]};font-weight:700">{ARM_LABELS[arm_id]}</td>',
            f'<td style="text-align:center">{_score_cell(_mean(all_composites))}<br><span class="muted">n={n_all}</span></td>',
            f'<td style="text-align:center">{_score_cell(_mean(multi_composites))}<br><span class="muted">n={n_multi}</span></td>',
            f'<td style="text-align:center">{_score_cell(_mean(single_composites))}<br><span class="muted">n={n_single}</span></td>',
        ]
        for d in DIMENSIONS:
            cells.append(f'<td style="text-align:center">{_score_cell(dim_means[d])}</td>')

        rows.append(f'<tr>{"".join(cells)}</tr>')

    # C - B gap row if both present
    if "b" in arm_ids and "c" in arm_ids:
        b_all = _mean([s.get("composite", 0) for s in arm_all_scores["b"]])
        c_all = _mean([s.get("composite", 0) for s in arm_all_scores["c"]])
        b_multi = _mean([s.get("composite", 0) for s in arm_subset_scores[("b", "multi-guideline")]])
        c_multi = _mean([s.get("composite", 0) for s in arm_subset_scores[("c", "multi-guideline")]])
        b_single = _mean([s.get("composite", 0) for s in arm_subset_scores[("b", "single-guideline")]])
        c_single = _mean([s.get("composite", 0) for s in arm_subset_scores[("c", "single-guideline")]])

        def _gap_cell(gap: float) -> str:
            color = "#059669" if gap >= 0.5 else "#d97706" if gap > 0 else "#dc2626"
            return f'<strong style="color:{color}">{gap:+.2f}</strong>'

        gap_cells = [
            '<td style="font-weight:700;color:var(--muted)">C - B Gap</td>',
            f'<td style="text-align:center">{_gap_cell(c_all - b_all)}</td>',
            f'<td style="text-align:center">{_gap_cell(c_multi - b_multi)}</td>',
            f'<td style="text-align:center">{_gap_cell(c_single - b_single)}</td>',
        ]
        for d in DIMENSIONS:
            b_dim = _mean([s.get(d, 0) for s in arm_all_scores["b"]])
            c_dim = _mean([s.get(d, 0) for s in arm_all_scores["c"]])
            gap_cells.append(f'<td style="text-align:center">{_gap_cell(c_dim - b_dim)}</td>')
        rows.append(f'<tr style="border-top:2px solid var(--border)">{"".join(gap_cells)}</tr>')

    dim_headers = "".join(f'<th style="text-align:center">{d.replace("_"," ").title()[:12]}</th>' for d in DIMENSIONS)

    return f"""
    <table class="summary-table">
        <thead><tr>
            <th>Arm</th>
            <th style="text-align:center">Composite<br><span class="muted">(all)</span></th>
            <th style="text-align:center">Composite<br><span class="muted">(multi-gl)</span></th>
            <th style="text-align:center">Composite<br><span class="muted">(single-gl)</span></th>
            {dim_headers}
        </tr></thead>
        <tbody>{''.join(rows)}</tbody>
    </table>
    """


# ---------------------------------------------------------------------------
# Full page HTML
# ---------------------------------------------------------------------------

CSS = """
  :root {
    --bg: #f8fafc; --card: #ffffff; --border: #e2e8f0;
    --text: #1e293b; --muted: #64748b;
    --font: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    --mono: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: var(--font); background: var(--bg); color: var(--text); line-height: 1.6; padding: 1.5rem; }
  .container { max-width: 1500px; margin: 0 auto; }
  h1 { font-size: 1.5rem; margin-bottom: 0.25rem; }
  h2 { font-size: 1.15rem; margin: 1.5rem 0 0.75rem; color: var(--muted); }
  h3 { font-size: 1.05rem; margin-bottom: 0.6rem; }
  h4 { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); margin-bottom: 0.4rem; }
  .page-meta { color: var(--muted); font-size: 0.85rem; margin-bottom: 1.5rem; }

  /* Summary table */
  .summary-table { width: 100%; border-collapse: collapse; margin-bottom: 2rem; background: var(--card); border-radius: 8px; overflow: hidden; border: 1px solid var(--border); }
  .summary-table th, .summary-table td { padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--border); font-size: 0.85rem; }
  .summary-table th { background: #f1f5f9; text-align: left; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.04em; }
  .summary-table a { color: var(--text); text-decoration: none; }
  .summary-table a:hover { text-decoration: underline; }

  /* Fixture sections */
  .fixture-section { margin-bottom: 0.75rem; border: 1px solid var(--border); border-radius: 8px; background: var(--card); }
  .fixture-header { padding: 0.75rem 1rem; cursor: pointer; display: flex; align-items: center; gap: 0.75rem; font-size: 0.95rem; }
  .fixture-header:hover { background: #f8fafc; }
  .fixture-title { font-weight: 700; }
  .fixture-scores { margin-left: auto; font-size: 0.85rem; }
  .fixture-body { padding: 0 1.25rem 1.25rem; }

  .subset-badge { font-size: 0.7rem; padding: 0.1rem 0.5rem; border-radius: 3px; font-weight: 600; }
  .subset-multi_guideline { background: #dbeafe; color: #1e40af; }
  .subset-single_guideline { background: #f3f4f6; color: #6b7280; }

  .description { color: var(--muted); font-size: 0.9rem; margin-bottom: 1rem; padding: 0.75rem; background: #fffbeb; border-radius: 6px; border: 1px solid #fde68a; }
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; }
  @media (max-width: 900px) { .two-col { grid-template-columns: 1fr; } }

  .patient-summary { background: var(--card); border: 1px solid var(--border); border-radius: 6px; padding: 0.75rem; }
  .patient-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0.5rem; }
  .patient-item { font-size: 0.85rem; }
  .patient-item .label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); }
  .patient-item .value { font-weight: 600; }

  .expected-section { background: var(--card); border: 1px solid var(--border); border-radius: 6px; padding: 0.75rem; }

  .arms-grid { display: grid; gap: 1rem; margin-bottom: 1rem; }
  .arms-grid-1 { grid-template-columns: 1fr; }
  .arms-grid-2 { grid-template-columns: repeat(2, 1fr); }
  .arms-grid-3 { grid-template-columns: repeat(3, 1fr); }
  @media (max-width: 1200px) { .arms-grid { grid-template-columns: 1fr !important; } }

  .arm-card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; }
  .section { margin-top: 0.75rem; }

  .scores-section { background: #f1f5f9; border-radius: 6px; padding: 0.6rem; }
  .score-row { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem; }
  .score-row.composite { border-top: 1px solid var(--border); padding-top: 0.35rem; margin-top: 0.25rem; }
  .score-dim { font-size: 0.75rem; width: 145px; flex-shrink: 0; display: flex; align-items: center; gap: 0.25rem; }
  .dim-help { display: inline-flex; align-items: center; justify-content: center; width: 14px; height: 14px; border-radius: 50%; background: var(--border); color: var(--muted); font-size: 0.6rem; font-weight: 700; cursor: help; flex-shrink: 0; position: relative; }
  .dim-help:hover { background: #94a3b8; color: white; }
  .dim-help:hover::after { content: attr(title); position: absolute; left: 120%; top: -0.5rem; background: #1e293b; color: #e2e8f0; padding: 0.5rem 0.75rem; border-radius: 6px; font-size: 0.72rem; font-weight: 400; white-space: pre-line; width: 240px; z-index: 100; line-height: 1.4; pointer-events: none; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
  .dim-help:hover::before { content: ''; position: absolute; left: 100%; top: 0.25rem; border: 5px solid transparent; border-right-color: #1e293b; z-index: 100; }
  .score-bar-container { flex: 1; display: flex; align-items: center; gap: 0.5rem; }
  .score-bar { height: 14px; border-radius: 3px; }
  .score-label { font-size: 0.8rem; font-weight: 600; min-width: 2rem; }

  .rationale-box { background: #f8fafc; border: 1px solid var(--border); border-radius: 6px; padding: 0.6rem; }
  .rationale-item { font-size: 0.8rem; margin-bottom: 0.3rem; }
  .rationale-item strong { color: var(--muted); }

  .json-block, .output-block { font-family: var(--mono); font-size: 0.75rem; background: #1e293b; color: #e2e8f0; padding: 0.75rem; border-radius: 6px; overflow-x: auto; max-height: 350px; overflow-y: auto; white-space: pre-wrap; word-break: break-word; }
  details { margin-top: 0.4rem; }
  summary { cursor: pointer; font-size: 0.8rem; color: var(--muted); padding: 0.2rem 0; }
  summary:hover { color: var(--text); }
  .context-note { font-size: 0.8rem; color: var(--muted); font-style: italic; }

  .action-item { padding: 0.4rem; border-radius: 5px; margin-bottom: 0.4rem; background: #f8fafc; border: 1px solid var(--border); }
  .action-header { font-size: 0.85rem; }
  .action-rationale { font-size: 0.75rem; color: var(--muted); margin-top: 0.2rem; }
  .action-source { font-size: 0.7rem; color: var(--muted); margin-top: 0.15rem; font-family: var(--mono); }
  .priority-badge { background: #dbeafe; color: #1e40af; font-size: 0.65rem; padding: 0.1rem 0.35rem; border-radius: 3px; font-weight: 600; }

  .context-box { background: #fafbfd; border: 1px solid var(--border); border-radius: 8px; padding: 0.75rem; margin-top: 0.4rem; }
  .context-detail { margin-top: 0.4rem; }
  .context-block { margin-bottom: 0.6rem; }
  .context-block h5 { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); margin-bottom: 0.25rem; border-bottom: 1px solid var(--border); padding-bottom: 0.15rem; }
  .context-block p { font-size: 0.8rem; margin-top: 0.15rem; }
  .convergence-group { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 0.6rem; margin-bottom: 0.4rem; }
  .convergence-group h5 { font-size: 0.85rem; color: var(--text); margin-bottom: 0.25rem; border: none; }
  .rec-sources { display: flex; flex-wrap: wrap; gap: 0.25rem; margin-bottom: 0.25rem; }
  .source-badge { background: #e0e7ff; color: #3730a3; font-size: 0.7rem; padding: 0.1rem 0.4rem; border-radius: 3px; }
  .status-badge { font-size: 0.65rem; padding: 0.1rem 0.35rem; border-radius: 3px; font-weight: 600; margin-left: 0.25rem; }
  .status-due { background: #fef3c7; color: #92400e; }
  .status-satisfied, .status-up_to_date { background: #d1fae5; color: #065f46; }
  .status-not_applicable { background: #f3f4f6; color: #6b7280; }
  .intensity-details { margin-top: 0.25rem; }
  .intensity-row { font-size: 0.75rem; }
  .matched-rec { font-size: 0.8rem; padding: 0.35rem 0.5rem; background: white; border: 1px solid var(--border); border-radius: 4px; margin-bottom: 0.25rem; }
  .modifier-block { background: #fef3c7; border: 1px solid #fde68a; border-radius: 6px; padding: 0.6rem; margin-bottom: 0.4rem; }
  .modifier-block h5 { color: #92400e; border: none; }
  .preemption-block { background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; padding: 0.6rem; margin-bottom: 0.4rem; }
  .preemption-block h5 { color: #991b1b; border: none; }
  .chunk-header { font-weight: 600; }
  .chunk-text { font-size: 0.75rem; padding: 0.6rem; background: #f1f5f9; border-radius: 4px; white-space: pre-wrap; word-break: break-word; max-height: 250px; overflow-y: auto; }
  .muted { color: var(--muted); font-size: 0.8rem; }

  /* Filter controls */
  .controls { display: flex; gap: 1rem; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; }
  .controls label { font-size: 0.85rem; font-weight: 600; }
  .controls select, .controls input { font-size: 0.85rem; padding: 0.3rem 0.5rem; border: 1px solid var(--border); border-radius: 4px; }
  .btn { font-size: 0.8rem; padding: 0.3rem 0.75rem; border: 1px solid var(--border); border-radius: 4px; background: var(--card); cursor: pointer; }
  .btn:hover { background: #f1f5f9; }
"""

JS = """
function filterFixtures() {
  const subset = document.getElementById('subset-filter').value;
  document.querySelectorAll('.fixture-section').forEach(el => {
    const isMulti = el.querySelector('.subset-multi_guideline') !== null;
    if (subset === 'all') el.style.display = '';
    else if (subset === 'multi' && isMulti) el.style.display = '';
    else if (subset === 'single' && !isMulti) el.style.display = '';
    else el.style.display = 'none';
  });
}
function expandAll() { document.querySelectorAll('.fixture-section').forEach(el => el.open = true); }
function collapseAll() { document.querySelectorAll('.fixture-section').forEach(el => el.open = false); }
"""


def generate_page(
    title: str,
    run_names: list[str],
    arm_ids: list[str],
    fixture_ids: list[str],
    all_data: dict,
) -> str:
    """Generate the full HTML page."""

    fixture_sections = []
    for i, fid in enumerate(fixture_ids):
        try:
            patient, expected = load_fixture_files(fid)
        except FileNotFoundError:
            continue
        arms = all_data.get(fid, {})
        if not arms:
            continue
        fixture_sections.append(_render_fixture_section(
            fid, patient, expected, arms, arm_ids, collapsed=(i > 0),
        ))

    summary_table = _render_summary_table(fixture_ids, all_data, arm_ids)

    arms_desc = ", ".join(f"{ARM_LABELS[a]}" for a in arm_ids)
    runs_desc = ", ".join(run_names)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
    <h1>{title}</h1>
    <div class="page-meta">
        Run: {html.escape(runs_desc)} &nbsp;|&nbsp; Arms: {html.escape(arms_desc)} &nbsp;|&nbsp; Fixtures: {len(fixture_ids)}
    </div>

    <div class="controls">
        <label>Filter:</label>
        <select id="subset-filter" onchange="filterFixtures()">
            <option value="all">All fixtures</option>
            <option value="multi">Multi-guideline only</option>
            <option value="single">Single-guideline only</option>
        </select>
        <button class="btn" onclick="expandAll()">Expand all</button>
        <button class="btn" onclick="collapseAll()">Collapse all</button>
    </div>

    <h2>Score Summary</h2>
    {summary_table}

    <h2>Fixture Detail</h2>
    {''.join(fixture_sections)}
</div>
<script>{JS}</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    load_dotenv(EVALS_ROOT / ".env")

    parser = argparse.ArgumentParser(
        description="Generate fixture inspection report from Braintrust experiments",
        prog="fixture_report.py",
    )
    parser.add_argument("--run", type=str, action="append", required=True,
                        help="Run name (e.g. v2-phase1). Can specify multiple times.")
    parser.add_argument("--fixture", type=str, default=None,
                        help="Single fixture ID (e.g. cross-domain/case-08)")
    parser.add_argument("--all", action="store_true",
                        help="Generate report for all fixtures")
    parser.add_argument("--arms", type=str, default="a,b,c",
                        help="Comma-separated arm IDs to include (default: a,b,c)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output HTML path (default: fixture-report.html)")
    args = parser.parse_args()

    if not args.all and not args.fixture:
        parser.error("Specify --fixture <id> or --all")

    arm_ids = [a.strip() for a in args.arms.split(",") if a.strip() in ALL_ARM_IDS]
    if not arm_ids:
        parser.error(f"No valid arm IDs in --arms. Choose from: {', '.join(ALL_ARM_IDS)}")

    run_names = args.run

    # Determine fixture list
    if args.all:
        fixture_ids = discover_fixtures()
    else:
        fixture_ids = [args.fixture]

    print(f"Fixtures: {len(fixture_ids)}, Arms: {', '.join(a.upper() for a in arm_ids)}, Runs: {', '.join(run_names)}", file=sys.stderr)

    # Fetch data
    # For multiple runs, we merge data (last run wins per fixture/arm)
    all_data: dict[str, dict] = {}
    for run_name in run_names:
        print(f"Fetching run '{run_name}'...", file=sys.stderr)
        run_data = fetch_all_data(run_name, arm_ids)
        for fid, arms in run_data.items():
            if fid not in all_data:
                all_data[fid] = {}
            all_data[fid].update(arms)

    found = sum(1 for fid in fixture_ids if fid in all_data)
    print(f"Found data for {found}/{len(fixture_ids)} fixtures", file=sys.stderr)

    title = f"Fixture Report — {', '.join(run_names)}"
    html_content = generate_page(title, run_names, arm_ids, fixture_ids, all_data)

    out_path = Path(args.output) if args.output else Path("fixture-report.html")
    out_path.write_text(html_content)
    print(f"Report written to {out_path.resolve()}", file=sys.stderr)


if __name__ == "__main__":
    main()
