"""The CLI contract: the exit codes a pipeline branches on, exercised in-process.

The exit code is the product, so these tests assert it directly rather than scraping stdout.
They call main() in-process (not through a subprocess) so coverage sees the CLI module.
"""

from __future__ import annotations

import io

import pytest

from status_audit.cli import EXIT_ERROR, EXIT_FINDINGS, EXIT_OK, _build_parser, _run_audit, main


def test_audit_on_the_committed_data_exits_with_findings(repo_root):
    code = main(["audit", "--data", str(repo_root / "data"),
                 "--policy", str(repo_root / "policy.toml"), "--quiet"])
    assert code == EXIT_FINDINGS


def test_audit_prints_the_verdict_when_not_quiet(repo_root, capsys):
    main(["audit", "--data", str(repo_root / "data"),
          "--policy", str(repo_root / "policy.toml")])
    out = capsys.readouterr().out
    assert "status-audit verdict: FAIL" in out


def test_audit_writes_html_and_json_when_asked(repo_root, tmp_path):
    html = tmp_path / "r.html"
    jsonp = tmp_path / "r.json"
    main(["audit", "--data", str(repo_root / "data"),
          "--policy", str(repo_root / "policy.toml"),
          "--html", str(html), "--json", str(jsonp), "--quiet"])
    assert html.exists() and "badge" in html.read_text()
    assert jsonp.exists() and "green_over_trouble_program_weeks" in jsonp.read_text()


def test_audit_on_a_missing_data_directory_exits_error(tmp_path, repo_root):
    code = main(["audit", "--data", str(tmp_path / "nope"),
                 "--policy", str(repo_root / "policy.toml"), "--quiet"])
    assert code == EXIT_ERROR


def test_audit_on_a_missing_policy_exits_error(repo_root, tmp_path):
    code = main(["audit", "--data", str(repo_root / "data"),
                 "--policy", str(tmp_path / "nope.toml"), "--quiet"])
    assert code == EXIT_ERROR


def test_a_bad_policy_prints_to_stderr_and_exits_error(repo_root, tmp_path):
    bad = tmp_path / "bad.toml"
    bad.write_text("[schedule]\namber_below_spi = 0.5\nred_below_spi = 0.9\n")
    args = _build_parser().parse_args(
        ["audit", "--data", str(repo_root / "data"), "--policy", str(bad), "--quiet"]
    )
    err = io.StringIO()
    code = _run_audit(args, err=err)
    assert code == EXIT_ERROR
    assert "status-audit:" in err.getvalue()


def test_generate_writes_fixtures_and_exits_ok(tmp_path):
    code = main(["generate", "--data", str(tmp_path), "--seed", "7"])
    assert code == EXIT_OK
    assert (tmp_path / "workstream_status.csv").exists()


def test_generate_without_a_seed_uses_the_default(tmp_path):
    code = main(["generate", "--data", str(tmp_path)])
    assert code == EXIT_OK


def test_no_subcommand_is_an_error():
    with pytest.raises(SystemExit):
        main([])
