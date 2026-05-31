import pytest

from app.core.domain.services.refresh_token_security_policy import (
    RefreshTokenSecurityPolicy,
)

assess = RefreshTokenSecurityPolicy.assess_risk


# ── zero risk ─────────────────────────────────────────────────────────────────

class TestZeroRisk:
    def test_identical_metadata_is_zero(self):
        assert assess(
            token_ip="10.0.0.1", token_agent="Browser/1", token_location="Berlin",
            current_ip="10.0.0.1", current_agent="Browser/1", current_location="Berlin",
        ) == 0

    def test_same_subnet_different_host_is_zero(self):
        """IPs in the same /24 subnet are treated as same range."""
        assert assess(
            token_ip="192.168.1.1", token_agent="UA/1", token_location=None,
            current_ip="192.168.1.254", current_agent="UA/1", current_location=None,
        ) == 0

    def test_no_metadata_at_all_adds_ip_risk_only(self):
        """All Nones: agent/location guards short-circuit; IP None → +1."""
        risk = assess(
            token_ip=None, token_agent=None, token_location=None,
            current_ip=None, current_agent=None, current_location=None,
        )
        assert risk == RefreshTokenSecurityPolicy.IP_RANGE_MISMATCH_RISK


# ── individual risk components ────────────────────────────────────────────────

class TestIndividualRiskWeights:
    def test_different_user_agent_adds_agent_weight(self):
        risk = assess(
            token_ip="10.0.0.1", token_agent="Chrome/1", token_location=None,
            current_ip="10.0.0.1", current_agent="Firefox/2", current_location=None,
        )
        assert risk == RefreshTokenSecurityPolicy.AGENT_MISMATCH_RISK

    def test_different_location_adds_location_weight(self):
        risk = assess(
            token_ip="10.0.0.1", token_agent="UA/1", token_location="Moscow",
            current_ip="10.0.0.1", current_agent="UA/1", current_location="Berlin",
        )
        assert risk == RefreshTokenSecurityPolicy.LOCATION_MISMATCH_RISK

    def test_different_subnet_adds_ip_weight(self):
        risk = assess(
            token_ip="10.0.0.1", token_agent="UA/1", token_location=None,
            current_ip="192.168.1.1", current_agent="UA/1", current_location=None,
        )
        assert risk == RefreshTokenSecurityPolicy.IP_RANGE_MISMATCH_RISK

    def test_all_mismatches_accumulate(self):
        expected = (
            RefreshTokenSecurityPolicy.AGENT_MISMATCH_RISK
            + RefreshTokenSecurityPolicy.LOCATION_MISMATCH_RISK
            + RefreshTokenSecurityPolicy.IP_RANGE_MISMATCH_RISK
        )
        risk = assess(
            token_ip="10.0.0.1", token_agent="Chrome/1", token_location="Moscow",
            current_ip="99.99.99.1", current_agent="Firefox/2", current_location="Berlin",
        )
        assert risk == expected


# ── None metadata short-circuit ───────────────────────────────────────────────

class TestNoneMetadata:
    def test_none_token_agent_no_agent_risk(self):
        """token_agent=None → condition 'token_agent and ...' is False → no risk."""
        risk = assess(
            token_ip="10.0.0.1", token_agent=None, token_location=None,
            current_ip="10.0.0.1", current_agent="Chrome/1", current_location=None,
        )
        assert risk == 0

    def test_none_current_agent_no_agent_risk(self):
        risk = assess(
            token_ip="10.0.0.1", token_agent="Chrome/1", token_location=None,
            current_ip="10.0.0.1", current_agent=None, current_location=None,
        )
        assert risk == 0

    def test_none_token_location_no_location_risk(self):
        risk = assess(
            token_ip="10.0.0.1", token_agent="UA/1", token_location=None,
            current_ip="10.0.0.1", current_agent="UA/1", current_location="Berlin",
        )
        assert risk == 0

    def test_none_current_location_no_location_risk(self):
        risk = assess(
            token_ip="10.0.0.1", token_agent="UA/1", token_location="Moscow",
            current_ip="10.0.0.1", current_agent="UA/1", current_location=None,
        )
        assert risk == 0

    def test_none_token_ip_adds_ip_risk(self):
        """token_ip=None → ip_address(None) raises → _same_ip_range returns False → +1."""
        risk = assess(
            token_ip=None, token_agent="UA/1", token_location=None,
            current_ip="10.0.0.1", current_agent="UA/1", current_location=None,
        )
        assert risk == RefreshTokenSecurityPolicy.IP_RANGE_MISMATCH_RISK

    def test_none_current_ip_adds_ip_risk(self):
        risk = assess(
            token_ip="10.0.0.1", token_agent="UA/1", token_location=None,
            current_ip=None, current_agent="UA/1", current_location=None,
        )
        assert risk == RefreshTokenSecurityPolicy.IP_RANGE_MISMATCH_RISK


# ── edge cases for IP comparison ──────────────────────────────────────────────

class TestIpRangeComparison:
    def test_invalid_ip_string_adds_ip_risk(self):
        risk = assess(
            token_ip="not.an.ip", token_agent="UA/1", token_location=None,
            current_ip="10.0.0.1", current_agent="UA/1", current_location=None,
        )
        assert risk == RefreshTokenSecurityPolicy.IP_RANGE_MISMATCH_RISK

    def test_ipv6_addresses_add_ip_risk(self):
        """IPv6 is not IPv4Address → _same_ip_range returns False → +1 risk."""
        risk = assess(
            token_ip="::1", token_agent="UA/1", token_location=None,
            current_ip="::1", current_agent="UA/1", current_location=None,
        )
        assert risk == RefreshTokenSecurityPolicy.IP_RANGE_MISMATCH_RISK

    def test_subnet_boundary_same_24(self):
        """10.0.0.0 and 10.0.0.255 are in the same /24."""
        risk = assess(
            token_ip="10.0.0.0", token_agent="UA/1", token_location=None,
            current_ip="10.0.0.255", current_agent="UA/1", current_location=None,
        )
        assert risk == 0

    def test_subnet_boundary_crossing_24(self):
        """10.0.0.255 and 10.0.1.0 cross a /24 boundary."""
        risk = assess(
            token_ip="10.0.0.255", token_agent="UA/1", token_location=None,
            current_ip="10.0.1.0", current_agent="UA/1", current_location=None,
        )
        assert risk == RefreshTokenSecurityPolicy.IP_RANGE_MISMATCH_RISK


# ── truthiness as used by RevokeTokenCase ────────────────────────────────────

class TestRiskTruthiness:
    def test_zero_risk_is_falsy(self):
        risk = assess(
            token_ip="10.0.0.1", token_agent="UA/1", token_location=None,
            current_ip="10.0.0.1", current_agent="UA/1", current_location=None,
        )
        assert not risk

    def test_any_mismatch_is_truthy(self):
        risk = assess(
            token_ip="10.0.0.1", token_agent="Chrome/1", token_location=None,
            current_ip="10.0.0.1", current_agent="Firefox/2", current_location=None,
        )
        assert risk
