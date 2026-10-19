import pytest
from offline_toolbox.ui.pdf.rotate_dialog import parse_page_ranges


def test_parse_page_ranges():
    # Standard single pages and ranges
    res = parse_page_ranges("1-3, 5, 7-8", max_pages=10)
    assert res == [0, 1, 2, 4, 6, 7]

    # Out of bound pages
    assert parse_page_ranges("1-15", max_pages=10) is None
    assert parse_page_ranges("0", max_pages=10) is None
    assert parse_page_ranges("abc", max_pages=10) is None

    # Inverted range
    assert parse_page_ranges("5-2", max_pages=10) is None
