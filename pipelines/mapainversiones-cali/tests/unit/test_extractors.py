import pandas as pd

from mapainversiones_cali.extract.csv_extractor import CsvExtractor
from mapainversiones_cali.extract.xlsx_extractor import XlsxExtractor


def test_xlsx_extracts_sheet_and_period(tmp_path):
    source = tmp_path / 'input.xlsx'
    pd.DataFrame({'Código': ['A1'], 'Valor': ['23']}).to_excel(source, sheet_name='Datos', index=False)
    rows = XlsxExtractor().extract({'base_dir': str(tmp_path), 'path': 'input.xlsx', 'xlsx_sheet': 'Datos', 'periodo': '202512'})
    assert rows == [{'codigo': 'A1', 'valor': '23', 'periodo': '202512'}]


def test_csv_extracts_columns(tmp_path):
    (tmp_path / 'input.csv').write_text('Codigo,Valor\nA1,23\n', encoding='utf-8')
    rows = CsvExtractor().extract({'base_dir': str(tmp_path), 'path': 'input.csv'})
    assert rows == [{'codigo': 'A1', 'valor': '23'}]
