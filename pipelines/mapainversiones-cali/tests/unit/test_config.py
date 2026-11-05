from pathlib import Path

from mapainversiones_cali.main import load_config, build_execution_config

ROOT = Path(__file__).resolve().parents[2]

def test_configuration_model_paths_exist():
    config = load_config(str(ROOT / "config" / "config.yaml"))
    assert len(config["extract_sources"]) == 5
    for stage in ("transform_models", "load_models"):
        for model in config[stage]:
            assert (ROOT / model["script_path"]).is_file()

def test_execution_config_filters_stages():
    config = load_config(str(ROOT / "config" / "config.yaml"))
    result = build_execution_config(config, ["presupuesto"], ["extract"])
    assert {s["name"] for s in result["extract_sources"]} == {"CUIPO", "CATALOGO PRODUCTOS"}
    assert not result["load_models"]
    assert not result["transform_models"]
