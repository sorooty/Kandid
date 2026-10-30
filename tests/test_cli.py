import json

from typer.testing import CliRunner

from kandid_tools.cli import app

from conftest import CAMILLE

runner = CliRunner()
PROFILE = str(CAMILLE / "profile.yaml")
DATAVIA = str(CAMILLE / "specs" / "datavia.yaml")


def test_validate_ok():
    result = runner.invoke(app, ["validate", PROFILE, DATAVIA])
    assert result.exit_code == 0
    assert result.stdout.strip() == "OK"


def test_validate_reports_unknown_items(tmp_path):
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        "offer: {company: Acme, role: Dev}\ncontract: Alternance\nexperiences: [ghost]\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["validate", PROFILE, str(spec)])
    assert result.exit_code == 1
    assert "expérience inconnue : 'ghost'" in result.stderr


def test_invalid_yaml_schema_is_reported(tmp_path):
    spec = tmp_path / "spec.yaml"
    spec.write_text("offer: {company: Acme}\n", encoding="utf-8")
    result = runner.invoke(app, ["validate", PROFILE, str(spec)])
    assert result.exit_code == 1
    assert "fichier invalide" in result.stderr


def test_name_and_folder():
    result = runner.invoke(app, ["name", PROFILE, DATAVIA, "--doc", "LM", "--date", "2027-09-01"])
    assert result.exit_code == 0
    assert result.stdout.strip() == (
        "LETTRES_MOTIVATION/ALTERNANCE/LM_Camille_Martin_Datavia_Alternance_Data-Analyst_FR_2027-09"
    )


def test_render_tex_only(tmp_path):
    result = runner.invoke(
        app, ["render", "cv", PROFILE, DATAVIA, "--out", str(tmp_path), "--tex-only", "--json"]
    )
    assert result.exit_code == 0, result.output
    paths = json.loads(result.stdout)
    assert paths["pdf"] is None
    assert "Lumio Énergie" in (tmp_path / paths["tex"]).read_text(encoding="utf-8")


def test_status_check():
    assert runner.invoke(app, ["status", "check", "ready", "sent"]).exit_code == 0
    refused = runner.invoke(app, ["status", "check", "to_review", "sent"])
    assert refused.exit_code == 1
    assert "À voir vers Envoyée" in refused.stderr


def test_status_list_json():
    rows = json.loads(runner.invoke(app, ["status", "list", "--json"]).stdout)
    assert rows["archived"] == {"label": "Archivée", "next": []}


def test_malformed_yaml_gives_a_message_not_a_traceback(tmp_path):
    spec = tmp_path / "spec.yaml"
    spec.write_text("offer: [unclosed\n", encoding="utf-8")
    result = runner.invoke(app, ["validate", PROFILE, str(spec)])
    assert result.exit_code == 1
    assert "YAML illisible ligne" in result.stderr
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_validation_errors_do_not_echo_file_content(tmp_path):
    profile = tmp_path / "profile.yaml"
    content = (CAMILLE / "profile.yaml").read_text(encoding="utf-8")
    profile.write_text(content.replace("city: Lyon", "city: [SENTINEL-123]"), encoding="utf-8")
    result = runner.invoke(app, ["validate", str(profile), DATAVIA])
    assert result.exit_code == 1
    assert "identity.city" in result.stderr
    assert "SENTINEL" not in result.output + result.stderr


def test_render_refuses_a_claim_the_profile_does_not_back(tmp_path):
    spec = tmp_path / "spec.yaml"
    content = (CAMILLE / "specs" / "datavia.yaml").read_text(encoding="utf-8")
    spec.write_text(content + "summary: Experte Kubernetes.\n", encoding="utf-8")
    result = runner.invoke(
        app, ["render", "cv", PROFILE, str(spec), "--out", str(tmp_path / "out"), "--tex-only"]
    )
    assert result.exit_code == 1
    assert "Kubernetes" in result.stdout
    assert not (tmp_path / "out").exists()


def test_render_failure_keeps_the_json_shape(tmp_path):
    spec = tmp_path / "spec.yaml"
    content = (CAMILLE / "specs" / "datavia.yaml").read_text(encoding="utf-8")
    spec.write_text(content + "summary: Experte Kubernetes.\n", encoding="utf-8")
    result = runner.invoke(
        app, ["render", "cv", PROFILE, str(spec), "--out", str(tmp_path), "--tex-only", "--json"]
    )
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["tex"] is None
    assert payload["honesty"]["ok"] is False


def test_render_refuses_the_master_folder(tmp_path):
    master = tmp_path / "00_MASTER"
    master.mkdir()
    config = tmp_path / "config.yaml"
    config.write_text(f"paths:\n  master: '{master}'\n", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "render",
            "cv",
            PROFILE,
            DATAVIA,
            "--out",
            str(master / "sub"),
            "--tex-only",
            "--config",
            str(config),
        ],
    )
    assert result.exit_code == 1
    assert "lecture seule" in result.stderr
    assert not any(master.iterdir())
