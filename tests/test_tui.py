from linuxff12rnghelper.tui import scan_percentages_pattern


def test_find_single_percentage_one():
    vals = [1, 2, 15, 7, 9]
    pat = "15"

    results = scan_percentages_pattern(pat, vals)
    assert results == [[2]]


def test_find_single_percentage_several():
    vals = [15, 1, 2, 15, 7, 9, 15, 0, 15]
    pat = "15"

    results = scan_percentages_pattern(pat, vals)
    assert results == [[0], [3], [6], [8]]


def test_find_multitoken_one():
    vals = [20, 15, 8, 0, 2, 20]
    pat = "20 15"

    results = scan_percentages_pattern(pat, vals)
    assert results == [[0, 1]]


def test_find_multitoken_several():
    vals = [20, 15, 8, 0, 2, 20, 0, 20, 15, -1]
    pat = "20 15"

    results = scan_percentages_pattern(pat, vals)
    assert results == [[0, 1], [7, 8]]


def test_find_ranged_1():
    vals = [20, 15, 8, 0, 2, 20, 0, 20, 15, -1]
    pat = "20 50- 50- 10+"

    results = scan_percentages_pattern(pat, vals)
    assert results == [[5, 6, 7, 8]]


def test_find_ranged_2():
    vals = [14, 7, 99, 82, 95, 0, 80, 95]
    pat = "80+ 95+"

    results = scan_percentages_pattern(pat, vals)
    assert results == [[3, 4], [6, 7]]
