import io

import boto3
import pandas as pd
import pytest
from moto import mock_aws

from mapainversiones_cali import main
from mapainversiones_cali.extract import xlsx_extractor
from mapainversiones_cali.extract.xlsx_extractor import XlsxExtractor, resolve_location

BUCKET = "test-datalake"


def _xlsx(sheets: dict) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False)
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def aws(monkeypatch):
    for var in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        monkeypatch.setenv(var, "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("S3_BUCKET", BUCKET)
    monkeypatch.delenv("S3_RAW_PREFIX", raising=False)
    with mock_aws():
        client = boto3.client("s3")
        client.create_bucket(Bucket=BUCKET)
        yield client
    xlsx_extractor.cleanup_downloads()


def _put(client, lote, name, sheets):
    client.put_object(Bucket=BUCKET, Key=f"raw/{lote}/{name}", Body=_xlsx(sheets))


def _details(**overrides):
    base = {"path": "CUIPO.xlsx", "xlsx_sheet": "CUIPO", "lote": "202601"}
    base.update(overrides)
    return base


def test_extracts_from_lote_and_uses_lote_as_periodo(aws):
    _put(aws, "202601", "CUIPO.xlsx", {"CUIPO": pd.DataFrame({"Código": ["A1"], "Valor": ["23"]})})
    rows = XlsxExtractor().extract(_details())
    assert rows == [{"codigo": "A1", "valor": "23", "periodo": "202601"}]


def test_each_lote_is_independent_and_periodo_can_be_overridden(aws):
    _put(aws, "202601", "CUIPO.xlsx", {"CUIPO": pd.DataFrame({"Codigo": ["A1"]})})
    _put(aws, "202602", "CUIPO.xlsx", {"CUIPO": pd.DataFrame({"Codigo": ["B2"], "Nueva": ["x"]})})
    first = XlsxExtractor().extract(_details(lote="202601"))
    second = XlsxExtractor().extract(_details(lote="202602", periodo="202606"))
    assert first == [{"codigo": "A1", "periodo": "202601"}]
    assert second == [{"codigo": "B2", "nueva": "x", "periodo": "202606"}]


def test_missing_object_raises_instead_of_returning_empty(aws):
    _put(aws, "202601", "OTRO.xlsx", {"CUIPO": pd.DataFrame({"Codigo": ["A1"]})})
    with pytest.raises(FileNotFoundError, match="raw/202601/CUIPO.xlsx"):
        XlsxExtractor().extract(_details())
    with pytest.raises(FileNotFoundError):
        XlsxExtractor().validate(_details(lote="202699"))


def test_missing_sheet_lists_available_sheets(aws):
    _put(aws, "202601", "CUIPO.xlsx", {"Otra": pd.DataFrame({"Codigo": ["A1"]})})
    with pytest.raises(ValueError, match="CUIPO.*Otra"):
        XlsxExtractor().validate(_details())


def test_empty_sheet_is_an_error(aws):
    _put(aws, "202601", "CUIPO.xlsx", {"CUIPO": pd.DataFrame({"Codigo": []})})
    with pytest.raises(ValueError, match="no contiene filas"):
        XlsxExtractor().extract(_details())


def test_file_with_spaces_downloaded_once_for_shared_workbook(aws):
    _put(aws, "202601", "BASE BID.xlsx", {
        "PROCESOS": pd.DataFrame({"Id": ["1"]}),
        "CONTRATOS": pd.DataFrame({"Id": ["9"]}),
    })
    calls = []
    original = XlsxExtractor._download

    def spy(self, bucket, key):
        path = original(self, bucket, key)
        calls.append(path)
        return path

    XlsxExtractor._download = spy
    try:
        procesos = XlsxExtractor().extract(_details(path="BASE BID.xlsx", xlsx_sheet="PROCESOS"))
        contratos = XlsxExtractor().extract(_details(path="BASE BID.xlsx", xlsx_sheet="CONTRATOS"))
    finally:
        XlsxExtractor._download = original
    assert procesos == [{"id": "1", "periodo": "202601"}]
    assert contratos == [{"id": "9", "periodo": "202601"}]
    assert len(set(calls)) == 1


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"lote": ""}, "Falta el periodo/lote"),
        ({"lote": "../x"}, "Lote invalido"),
        ({"lote": "a/b"}, "Lote invalido"),
        ({"path": "sub/CUIPO.xlsx"}, "sin carpetas"),
        ({"path": "CUIPO.csv"}, ".xlsx"),
        ({"path": ""}, "details.path"),
    ],
)
def test_resolve_location_rejects_unsafe_input(overrides, message):
    with pytest.raises(ValueError, match=message):
        resolve_location(_details(**overrides))


def test_resolve_location_requires_bucket(monkeypatch):
    monkeypatch.delenv("S3_BUCKET")
    with pytest.raises(ValueError, match="bucket"):
        resolve_location(_details())


def test_resolve_location_builds_key_with_prefix_override(monkeypatch):
    monkeypatch.setenv("S3_RAW_PREFIX", "/entrada/")
    assert resolve_location(_details(path="BASE BID.xlsx")) == (BUCKET, "entrada/202601/BASE BID.xlsx")


class FakeLoader:
    def __init__(self):
        self.loaded = []

    def load_to_stage(self, data, table):
        self.loaded.append((table, len(data)))


def _config(sources, lote="202601"):
    return {"lote": lote, "extract_sources": sources}


def _source(name, path, sheet, table):
    return {
        "name": name,
        "source_type": "xlsx",
        "target_stage_table": table,
        "details": {"path": path, "xlsx_sheet": sheet},
    }


def test_preflight_blocks_all_loads_when_any_file_is_missing(aws):
    _put(aws, "202601", "CUIPO.xlsx", {"CUIPO": pd.DataFrame({"Codigo": ["A1"]})})
    loader = FakeLoader()
    config = _config([
        _source("CUIPO", "CUIPO.xlsx", "CUIPO", "dbo.stg_cuipo"),
        _source("REPORTE RPC", "REPORTE_RPC.xlsx", "REPORTE", "dbo.stg_rpc"),
    ])
    with pytest.raises(RuntimeError, match=r"REPORTE RPC.*REPORTE_RPC.xlsx"):
        main.run_extract_stage(config, loader)
    assert loader.loaded == []


def test_extract_stage_loads_every_enabled_source(aws):
    _put(aws, "202601", "CUIPO.xlsx", {"CUIPO": pd.DataFrame({"Codigo": ["A1", "A2"]})})
    _put(aws, "202601", "REPORTE_RPC.xlsx", {"REPORTE": pd.DataFrame({"Rpc": ["7"]})})
    disabled = _source("CATALOGO", "CATALOGO_DE_PRODUCTOS.xlsx", "Catalogo", "dbo.stg_cat")
    disabled["enabled"] = False
    loader = FakeLoader()
    config = _config([
        _source("CUIPO", "CUIPO.xlsx", "CUIPO", "dbo.stg_cuipo"),
        disabled,
        _source("REPORTE RPC", "REPORTE_RPC.xlsx", "REPORTE", "dbo.stg_rpc"),
    ])
    main.run_extract_stage(config, loader)
    assert loader.loaded == [("dbo.stg_cuipo", 2), ("dbo.stg_rpc", 1)]


def test_extract_stage_fails_without_lote(aws):
    config = _config([_source("CUIPO", "CUIPO.xlsx", "CUIPO", "dbo.stg_cuipo")], lote=None)
    loader = FakeLoader()
    with pytest.raises(RuntimeError, match="Falta el periodo/lote"):
        main.run_extract_stage(config, loader)
    assert loader.loaded == []
