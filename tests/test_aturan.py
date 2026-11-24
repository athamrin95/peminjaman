from aturan import cari_perangkat


def test_cari_perangkat_empty_string():
    """Test that passing an empty string returns the appropriate error dictionary."""
    result = cari_perangkat("")
    assert result == {"error": "Passed an empty string as the argument!"}


def test_cari_perangkat_by_code_exact():
    """Test matching an exact item code (case-sensitive)."""
    result = cari_perangkat("LP-01")
    assert "success" in result
    assert "LP-01" in result["success"]


def test_cari_perangkat_by_code_case_insensitive():
    """Test matching a code using different casing."""
    result = cari_perangkat("lp-02")
    assert "success" in result
    assert "LP-02" in result["success"]


def test_cari_perangkat_by_name_multiple():
    """Test matching a name that returns multiple items from PSEUDO_DB."""
    result = cari_perangkat("Laptop 14 inch")
    assert "success" in result
    assert "LP-01" in result["success"]
    assert "LP-02" in result["success"]


def test_cari_perangkat_by_type():
    """Test matching an item type."""
    result = cari_perangkat("projector")
    assert "success" in result
    assert "PR-01" in result["success"]


def test_cari_perangkat_no_match():
    """Test that a non-existent query returns a no match error dictionary."""
    result = cari_perangkat("NonExistentItem")
    assert result == {"error": "No match found in the database!"}