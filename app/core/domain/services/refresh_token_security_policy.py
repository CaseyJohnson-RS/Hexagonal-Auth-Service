from ipaddress import ip_address, IPv4Address


class RefreshTokenSecurityPolicy:
    """
    Stateless policy for assessing refresh token misuse risk based on
    client metadata changes.

    The returned risk score is an integer where higher values indicate
    higher suspicion.
    """

    # Risk weights
    AGENT_MISMATCH_RISK = 2
    LOCATION_MISMATCH_RISK = 2
    IP_RANGE_MISMATCH_RISK = 1

    @staticmethod
    def assess_risk(
        *,
        token_ip: str | None,
        token_agent: str | None,
        token_location: str | None,
        current_ip: str | None,
        current_agent: str | None,
        current_location: str | None,
    ) -> int:
        """
        Assess risk level for refresh token usage by comparing stored
        token metadata with current request metadata.

        Returns:
            int: Risk score (0 = no risk, higher = more suspicious).
        """
        risk = 0

        if token_agent and current_agent and token_agent != current_agent:
            risk += RefreshTokenSecurityPolicy.AGENT_MISMATCH_RISK

        if token_location and current_location and token_location != current_location:
            risk += RefreshTokenSecurityPolicy.LOCATION_MISMATCH_RISK

        if not RefreshTokenSecurityPolicy._same_ip_range(token_ip, current_ip):
            risk += RefreshTokenSecurityPolicy.IP_RANGE_MISMATCH_RISK

        return risk

    @staticmethod
    def _same_ip_range(ip1: str | None, ip2: str | None) -> bool:
        """
        Check whether two IP addresses belong to the same /24 IPv4 subnet.

        If either IP is missing or invalid, treat as different.
        """
        try:
            addr1 = ip_address(ip1)  # type: ignore[arg-type]
            addr2 = ip_address(ip2)  # type: ignore[arg-type]
        except Exception:
            return False

        if not isinstance(addr1, IPv4Address) or not isinstance(addr2, IPv4Address):
            return False

        return addr1.packed[:3] == addr2.packed[:3]
