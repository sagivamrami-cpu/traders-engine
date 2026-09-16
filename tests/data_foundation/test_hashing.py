from pathlib import Path

from trading_system.data_foundation.hashing import sha256_file, sha256_rows


def test_same_file_content_produces_same_hash(tmp_path: Path):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    first.write_bytes(b"a,b\n1,2\n")
    second.write_bytes(b"a,b\n1,2\n")

    assert sha256_file(first) == sha256_file(second)


def test_raw_file_hash_preserves_line_endings(tmp_path: Path):
    lf = tmp_path / "lf.csv"
    crlf = tmp_path / "crlf.csv"
    lf.write_bytes(b"a,b\n1,2\n")
    crlf.write_bytes(b"a,b\r\n1,2\r\n")

    assert sha256_file(lf) != sha256_file(crlf)


def test_row_hash_normalizes_string_line_endings():
    assert sha256_rows([{"note": "a\nb"}]) == sha256_rows([{"note": "a\r\nb"}])


def test_row_hash_is_stable_under_key_order_but_not_row_order():
    rows_a = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    rows_b = [{"b": 2, "a": 1}, {"b": 4, "a": 3}]
    rows_c = [{"a": 3, "b": 4}, {"a": 1, "b": 2}]

    assert sha256_rows(rows_a) == sha256_rows(rows_b)
    assert sha256_rows(rows_a) != sha256_rows(rows_c)
