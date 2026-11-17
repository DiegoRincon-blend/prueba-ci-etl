from mapainversiones_cali.extract.csv_extractor import CsvExtractor


def test_csv_extracts_columns(tmp_path):
    (tmp_path / 'input.csv').write_text('Codigo,Valor\nA1,23\n', encoding='utf-8')
    rows = CsvExtractor().extract({'base_dir': str(tmp_path), 'path': 'input.csv'})
    assert rows == [{'codigo': 'A1', 'valor': '23'}]
