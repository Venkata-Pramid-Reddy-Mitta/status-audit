"""Rendering: JSON round-trips, text leads with the verdict, HTML is valid and legible."""

from __future__ import annotations

import json
import re

from status_audit.report import build_report_dict, render_html, render_json, render_text

# Every CSS class that appears in render_html's markup. The test below asserts each has a rule
# in the stylesheet, which is the collision that once rendered a verdict green on green.
MARKUP_CLASSES = {
    "badge", "badge-fail", "badge-pass", "headline", "big", "subtitle", "note", "cell-rag",
}


def test_the_json_record_round_trips_through_json_loads(audit_result):
    data = json.loads(render_json(audit_result))
    assert data["summary"]["green_over_trouble_program_weeks"] == 26


def test_the_json_summary_counts_match_the_result_object(audit_result):
    data = build_report_dict(audit_result)
    assert data["summary"]["total_reports"] == audit_result.total_reports
    assert len(data["program_audits"]) == len(audit_result.program_audits)
    assert len(data["rollup_audits"]) == len(audit_result.rollup_audits)


def test_the_json_contains_no_numpy_types(audit_result):
    # json.dumps would already raise on a numpy scalar; this asserts the coercion explicitly.
    text = render_json(audit_result)
    assert "numpy" not in text


def test_the_text_report_leads_with_the_verdict(audit_result):
    text = render_text(audit_result)
    assert text.splitlines()[0].startswith("status-audit verdict: FAIL")


def test_the_text_report_names_the_never_confessed_program(audit_result):
    assert "NEVER CONFESSED" in render_text(audit_result)


def test_the_html_report_carries_a_fail_badge_on_the_committed_data(audit_result):
    html = render_html(audit_result)
    assert 'class="badge badge-fail"' in html
    assert ">FAIL<" in html


def test_every_css_class_used_in_the_markup_has_a_stylesheet_rule(audit_result):
    html = render_html(audit_result)
    used = set(re.findall(r'class="([^"]+)"', html))
    flat = {cls for group in used for cls in group.split()}
    for cls in flat:
        assert f".{cls}" in html, f"class {cls} used in markup has no CSS rule"


def test_the_markup_class_inventory_is_a_subset_of_the_known_classes(audit_result):
    # The pass badge only renders on passing data, so a single render is a subset of the
    # full inventory; the stylesheet still carries a rule for every known class.
    html = render_html(audit_result)
    used = set(re.findall(r'class="([^"]+)"', html))
    flat = {cls for group in used for cls in group.split()}
    assert flat <= MARKUP_CLASSES
    for cls in MARKUP_CLASSES:
        assert f".{cls}" in html, f"class {cls} has no CSS rule"


def test_the_html_states_the_boundary_in_its_own_section(audit_result):
    html = render_html(audit_result)
    assert "What this cannot establish" in html
    assert "ground truth" in html
    assert "disagreement" in html
