"""
Tests for canonical_map.py false-positive prevention.
Covers review finding #4: startswith matching was removed.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.fields.canonical_map import resolve_canonical_key


class TestCanonicalMapFalsePositives:
    """Verify that short-key substring matches no longer produce false positives."""

    def test_status_does_not_match_status_kesehatan(self):
        """'Status Kesehatan' should NOT map to marital_status."""
        result = resolve_canonical_key("Status Kesehatan")
        # Should be None (no match) since this is health status, not marital status
        assert result is None or result != "marital_status"

    def test_kota_does_not_match_kota_kelahiran_ayah(self):
        """'Kota Kelahiran Ayah' should NOT map to user's city."""
        result = resolve_canonical_key("Kota Kelahiran Ayah")
        assert result is None or result != "city"

    def test_alamat_does_not_match_alamat_kantor_cabang(self):
        """'Alamat Kantor Cabang' should NOT map to user's home address."""
        result = resolve_canonical_key("Alamat Kantor Cabang")
        assert result is None or result != "address"

    def test_exact_match_still_works(self):
        """Exact static matches should still resolve correctly."""
        assert resolve_canonical_key("Nama Lengkap") == "full_name"
        assert resolve_canonical_key("email") == "email"
        assert resolve_canonical_key("alamat") == "address"
        assert resolve_canonical_key("status") == "marital_status"
        assert resolve_canonical_key("kota") == "city"

    def test_fuzzy_close_match_works(self):
        """Labels very close to a canonical key should still match via fuzzy."""
        result = resolve_canonical_key("Nama Lengkap Full Name")
        assert result == "full_name"
