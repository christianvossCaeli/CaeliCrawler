"""URL validation utilities to prevent SSRF attacks.

Server-Side Request Forgery (SSRF) protection by validating URLs
before crawling to ensure they don't point to internal resources.
"""

import ipaddress
import socket
from typing import Optional, Tuple
from urllib.parse import urlparse

import structlog

logger = structlog.get_logger()

# Blocked IP ranges (internal/private networks)
BLOCKED_IP_RANGES = [
    ipaddress.ip_network("0.0.0.0/8"),        # "This" network
    ipaddress.ip_network("10.0.0.0/8"),       # Private class A
    ipaddress.ip_network("100.64.0.0/10"),    # Carrier-grade NAT
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("169.254.0.0/16"),   # Link-local
    ipaddress.ip_network("172.16.0.0/12"),    # Private class B
    ipaddress.ip_network("192.0.0.0/24"),     # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),     # TEST-NET-1
    ipaddress.ip_network("192.168.0.0/16"),   # Private class C
    ipaddress.ip_network("198.18.0.0/15"),    # Benchmarking
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),   # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),      # Multicast
    ipaddress.ip_network("240.0.0.0/4"),      # Reserved
    ipaddress.ip_network("255.255.255.255/32"),  # Broadcast
    # IPv6 private ranges
    ipaddress.ip_network("::1/128"),          # Loopback
    ipaddress.ip_network("fc00::/7"),         # Unique local
    ipaddress.ip_network("fe80::/10"),        # Link-local
]

# Blocked hostnames
BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "local",
    "broadcasthost",
    "ip6-localhost",
    "ip6-loopback",
}

# Allowed schemes
ALLOWED_SCHEMES = {"http", "https"}


def is_ip_blocked(ip_str: str) -> bool:
    """Check if an IP address is in a blocked range."""
    try:
        ip = ipaddress.ip_address(ip_str)
        for network in BLOCKED_IP_RANGES:
            if ip in network:
                return True
        return False
    except ValueError:
        return False


def resolve_hostname(hostname: str) -> Optional[str]:
    """Resolve hostname to IP address.

    Returns None if resolution fails.
    """
    try:
        # Get all IP addresses for the hostname
        addr_info = socket.getaddrinfo(hostname, None)
        if addr_info:
            # Return the first IP address
            return addr_info[0][4][0]
        return None
    except socket.gaierror:
        return None


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """Validate a URL for crawling.

    Checks:
    1. URL is well-formed
    2. Scheme is http or https
    3. Hostname is not in blocked list
    4. Resolved IP is not in blocked ranges

    Args:
        url: The URL to validate

    Returns:
        Tuple of (is_valid, error_message)
        If valid: (True, None)
        If invalid: (False, "reason")
    """
    if not url:
        return False, "URL is empty"

    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Invalid URL format: {e}"

    # Check scheme
    if not parsed.scheme:
        return False, "URL has no scheme (http/https required)"

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return False, f"Scheme '{parsed.scheme}' not allowed. Use http or https."

    # Check hostname exists
    hostname = parsed.hostname
    if not hostname:
        return False, "URL has no hostname"

    # Check for blocked hostnames
    hostname_lower = hostname.lower()
    if hostname_lower in BLOCKED_HOSTNAMES:
        return False, f"Hostname '{hostname}' is blocked"

    # Check if hostname ends with blocked domain
    if hostname_lower.endswith(".local") or hostname_lower.endswith(".internal"):
        return False, f"Domain '{hostname}' is blocked (internal domain)"

    # Check if hostname is an IP address
    try:
        ip = ipaddress.ip_address(hostname)
        if is_ip_blocked(str(ip)):
            return False, f"IP address {ip} is in a blocked range"
    except ValueError:
        # It's a hostname, not an IP - resolve it
        resolved_ip = resolve_hostname(hostname)
        if resolved_ip and is_ip_blocked(resolved_ip):
            logger.warning(
                "URL resolves to blocked IP",
                url=url,
                hostname=hostname,
                resolved_ip=resolved_ip,
            )
            return False, f"Hostname resolves to blocked IP ({resolved_ip})"

    # Check for suspicious port
    if parsed.port:
        # Block common internal service ports
        blocked_ports = {22, 23, 25, 445, 3306, 5432, 6379, 27017}
        if parsed.port in blocked_ports:
            return False, f"Port {parsed.port} is blocked (internal service port)"

    return True, None


def validate_url_strict(url: str, allowed_domains: Optional[list] = None) -> Tuple[bool, Optional[str]]:
    """Strict URL validation with optional domain whitelist.

    In addition to basic validation, can restrict to specific domains.

    Args:
        url: The URL to validate
        allowed_domains: Optional list of allowed domains (e.g., ["example.com", "gov.de"])

    Returns:
        Tuple of (is_valid, error_message)
    """
    # First do basic validation
    is_valid, error = validate_url(url)
    if not is_valid:
        return is_valid, error

    # If domain whitelist is provided, check it
    if allowed_domains:
        parsed = urlparse(url)
        hostname = parsed.hostname.lower()

        # Check if hostname matches or is subdomain of allowed domain
        is_allowed = False
        for domain in allowed_domains:
            domain = domain.lower()
            if hostname == domain or hostname.endswith(f".{domain}"):
                is_allowed = True
                break

        if not is_allowed:
            return False, f"Domain '{hostname}' not in allowed list"

    return True, None
