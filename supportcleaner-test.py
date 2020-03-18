# Install pytest for testing `pip install pytest`

from supportcleaner import add_unit_prefix, remove_unit_prefix


def test_add_unit_prefix():
    assert add_unit_prefix(2048) == '2.0KiB'
    assert add_unit_prefix(2376582746591, 'V') == '2.2TiV'


def test_remove_unit_prefix():
    assert remove_unit_prefix('4.0KiB') == (4096, 'B')
    assert remove_unit_prefix('2.3GiV') == (2469606195.2, 'V')
