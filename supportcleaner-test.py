# Install pytest for testing `pip install pytest`

from supportcleaner import add_unit_prefix, remove_unit_prefix


def test_list_files_in_dir():
    pass


def test_add_unit_prefix():
    assert add_unit_prefix(2048) == '2.0KiB'
    assert add_unit_prefix(2376582746591) == '2.2TiB'


def test_remove_unit_prefix():
    assert remove_unit_prefix('4.0KiB') == 4096
    assert remove_unit_prefix('2.3GiB') == 2469606195.2
