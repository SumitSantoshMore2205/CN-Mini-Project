"""Pure IPv4 subnetting logic used by the Tkinter application.

The calculations use integer addresses so boundary conditions (including /31
and /32) are handled explicitly and without floating point rounding.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Subnet:
    """One child network and its address details."""

    index: int
    network: ipaddress.IPv4Network
    first_usable: ipaddress.IPv4Address | None
    last_usable: ipaddress.IPv4Address | None
    broadcast: ipaddress.IPv4Address
    usable_hosts: int


@dataclass(frozen=True)
class SubnetPlan:
    """All information needed by the UI to present a subnetting result."""

    original_ip: ipaddress.IPv4Address
    original_network: ipaddress.IPv4Network
    original_mask: ipaddress.IPv4Address
    subnets: tuple[Subnet, ...]
    new_prefix: int
    mode: str
    requested: int

    @property
    def new_mask(self) -> ipaddress.IPv4Address:
        return ipaddress.IPv4Address(int(self.subnets[0].network.netmask))

    @property
    def subnet_count(self) -> int:
        return len(self.subnets)


def parse_network(address: str, cidr_or_mask: str) -> tuple[ipaddress.IPv4Address, ipaddress.IPv4Network]:
    """Parse an IPv4 address and CIDR prefix or dotted-decimal mask."""
    try:
        ip = ipaddress.IPv4Address(address.strip())
    except ipaddress.AddressValueError as exc:
        raise ValueError("Enter a valid IPv4 address, for example 192.168.10.0.") from exc

    value = cidr_or_mask.strip()
    if value.startswith("/"):
        value = value[1:]
    try:
        if "." in value:
            mask = ipaddress.IPv4Address(value)
            # IPv4Network validates that a dotted mask is contiguous.
            network = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
        else:
            prefix = int(value)
            if not 0 <= prefix <= 32:
                raise ValueError
            network = ipaddress.IPv4Network(f"{ip}/{prefix}", strict=False)
    except (ipaddress.AddressValueError, ipaddress.NetmaskValueError, ValueError) as exc:
        raise ValueError("Enter a CIDR prefix from /0 to /32 or a contiguous dotted-decimal subnet mask.") from exc
    return ip, network


def _usable_host_count(network: ipaddress.IPv4Network) -> int:
    # RFC 3021 allows both addresses in a /31 point-to-point link. A /32 is a
    # single host route. All larger networks reserve network and broadcast.
    if network.prefixlen == 32:
        return 1
    if network.prefixlen == 31:
        return 2
    return max(0, network.num_addresses - 2)


def calculate_subnets(address: str, cidr_or_mask: str, mode: str, requested: int,
                      max_subnets: int = 65536) -> SubnetPlan:
    """Create an equal-size subnet plan.

    ``mode`` is either ``"subnets"`` (requested number of subnets, rounded
    up to the next power of two) or ``"hosts"`` (minimum usable hosts each).
    The original IP may be any address in the entered network; the network
    boundary is calculated before splitting.
    """
    ip, original = parse_network(address, cidr_or_mask)
    if mode not in {"subnets", "hosts"}:
        raise ValueError("Choose either the required-subnets or hosts-per-subnet mode.")
    if isinstance(requested, bool) or requested < 1:
        raise ValueError("Enter a whole number greater than zero.")

    if mode == "subnets":
        added_bits = (requested - 1).bit_length()
        new_prefix = original.prefixlen + added_bits
        if new_prefix > 32:
            raise ValueError(f"This network cannot be divided into {requested} subnets.")
    else:
        # Find the smallest address block whose usable capacity meets request.
        new_prefix = 32
        while new_prefix >= original.prefixlen:
            candidate = ipaddress.IPv4Network(f"0.0.0.0/{new_prefix}")
            if _usable_host_count(candidate) >= requested:
                break
            new_prefix -= 1
        if new_prefix < original.prefixlen:
            available = _usable_host_count(original)
            raise ValueError(f"The parent network provides at most {available} usable hosts per subnet.")

    block_count = 1 << (new_prefix - original.prefixlen)
    if block_count > max_subnets:
        raise ValueError(f"This request creates {block_count:,} subnets, which is too many to display at once (limit {max_subnets:,}). Use a smaller request.")

    step = 1 << (32 - new_prefix)
    base = int(original.network_address)
    rows: list[Subnet] = []
    for index in range(block_count):
        child = ipaddress.IPv4Network((base + index * step, new_prefix))
        count = _usable_host_count(child)
        if child.prefixlen == 32:
            first = last = child.network_address
        elif child.prefixlen == 31:
            first, last = child.network_address, child.broadcast_address
        else:
            first = ipaddress.IPv4Address(int(child.network_address) + 1)
            last = ipaddress.IPv4Address(int(child.broadcast_address) - 1)
        rows.append(Subnet(index + 1, child, first, last, child.broadcast_address, count))

    return SubnetPlan(ip, original, original.netmask, tuple(rows), new_prefix, mode, requested)


def ip_binary(value: ipaddress.IPv4Address) -> str:
    """Return four 8-bit groups for an address."""
    return ".".join(f"{octet:08b}" for octet in value.packed)

