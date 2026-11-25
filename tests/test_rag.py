"""The RAG scale: ordering, parsing, and the signed relations reconciliation depends on."""

from __future__ import annotations

import pytest

from status_audit.rag import Rag, is_optimistic, parse_rag, severity_gap


def test_green_is_less_severe_than_amber_which_is_less_severe_than_red():
    assert Rag.GREEN < Rag.AMBER < Rag.RED


def test_the_integer_value_is_the_severity():
    assert int(Rag.GREEN) == 0
    assert int(Rag.AMBER) == 1
    assert int(Rag.RED) == 2


def test_the_letter_property_is_the_first_capital_of_the_name():
    assert Rag.GREEN.letter == "G"
    assert Rag.AMBER.letter == "A"
    assert Rag.RED.letter == "R"


def test_str_renders_the_colour_in_title_case():
    assert str(Rag.RED) == "Red"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Green", Rag.GREEN), ("green ", Rag.GREEN), ("G", Rag.GREEN),
        ("Amber", Rag.AMBER), ("A", Rag.AMBER), ("yellow", Rag.AMBER), ("Y", Rag.AMBER),
        ("Red", Rag.RED), ("r", Rag.RED), ("RED", Rag.RED),
    ],
)
def test_parse_rag_accepts_the_spellings_a_real_export_contains(text, expected):
    assert parse_rag(text) == expected


def test_parse_rag_returns_a_rag_unchanged():
    assert parse_rag(Rag.AMBER) is Rag.AMBER


def test_parse_rag_rejects_an_unknown_token_rather_than_bucketing_it():
    with pytest.raises(ValueError, match="not a recognisable RAG"):
        parse_rag("maroon")


def test_parse_rag_rejects_an_empty_cell():
    with pytest.raises(ValueError):
        parse_rag("")


def test_is_optimistic_is_true_only_when_the_report_is_greener_than_computed():
    assert is_optimistic(Rag.GREEN, Rag.RED) is True
    assert is_optimistic(Rag.AMBER, Rag.RED) is True
    assert is_optimistic(Rag.RED, Rag.RED) is False
    assert is_optimistic(Rag.RED, Rag.GREEN) is False


def test_severity_gap_is_the_absolute_distance_on_the_scale():
    assert severity_gap(Rag.GREEN, Rag.RED) == 2
    assert severity_gap(Rag.RED, Rag.GREEN) == 2
    assert severity_gap(Rag.AMBER, Rag.AMBER) == 0
