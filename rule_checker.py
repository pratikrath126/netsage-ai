import re
import csv
import json
import sys


def check_duplicate_ips(show_output: str) -> list:
    """Find IP addresses that appear on multiple interfaces."""
    results = []
    # Match lines from 'show ip interface brief' format:
    # Interface  IP-Address  OK? Method Status Protocol
    ip_pattern = re.compile(
        r'(\S+)\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+YES'
    )
    ips = {}
    for line in show_output.splitlines():
        match = ip_pattern.search(line)
        if match:
            interface, ip = match.groups()
            if ip != "unassigned" and not ip.startswith("127."):
                if ip in ips:
                    results.append({
                        'check': 'duplicate_ips',
                        'finding': f'IP {ip} is duplicated on {ips[ip]} and {interface}',
                        'severity': 'High'
                    })
                else:
                    ips[ip] = interface
    return results


def check_wrong_subnet_mask(show_output: str) -> list:
    """Detect interfaces with mismatched subnet masks in the same network."""
    results = []
    # Look for IP and mask pairs from show ip interface brief or show run
    # Pattern: ip address X.X.X.X Y.Y.Y.Y
    ip_mask_pattern = re.compile(
        r'ip\s+address\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    )
    # Also check for default-router vs network mask mismatch in DHCP
    dhcp_network = re.compile(
        r'network\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    )
    dhcp_router = re.compile(
        r'default-router\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    )

    interfaces = {}
    for match in ip_mask_pattern.finditer(show_output):
        ip, mask = match.groups()
        # Compute network address (simplified: just compare first 3 octets for /24)
        network = '.'.join(ip.split('.')[:3]) + '.0'
        if network in interfaces:
            old_ip, old_mask = interfaces[network]
            if old_mask != mask:
                results.append({
                    'check': 'wrong_subnet_mask',
                    'finding': f'Subnet mask mismatch in network {network}: {old_ip} uses {old_mask} but {ip} uses {mask}',
                    'severity': 'High'
                })
        else:
            interfaces[network] = (ip, mask)

    # Check DHCP pool network vs default-router
    networks = dhcp_network.findall(show_output)
    routers = dhcp_router.findall(show_output)
    for net_ip, net_mask in networks:
        net_prefix = '.'.join(net_ip.split('.')[:3])
        for router_ip in routers:
            router_prefix = '.'.join(router_ip.split('.')[:3])
            if net_prefix != router_prefix:
                results.append({
                    'check': 'wrong_subnet_mask',
                    'finding': f'DHCP pool network {net_ip}/{net_mask} does not match default-router {router_ip}',
                    'severity': 'High'
                })

    return results


def check_gateway_mismatch(show_output: str) -> list:
    """Check if default gateway doesn't match any router interface IP."""
    results = []
    # Look for default-gateway or default-router statements
    gw_pattern = re.compile(
        r'(?:default-gateway|default-router|ip\s+default-gateway)\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    )
    # Collect all interface IPs
    ip_pattern = re.compile(
        r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+YES'
    )

    gateways = gw_pattern.findall(show_output)
    interface_ips = ip_pattern.findall(show_output)

    for gw in gateways:
        if gw not in interface_ips and interface_ips:
            results.append({
                'check': 'gateway_mismatch',
                'finding': f'Default gateway {gw} does not match any router interface IP',
                'severity': 'High'
            })

    return results


def check_interface_down(show_output: str) -> list:
    """Find interfaces in down/down or administratively down state."""
    results = []
    # Pattern 1: show ip interface brief format
    # Interface  IP-Address  OK? Method Status  Protocol
    brief_pattern = re.compile(
        r'(\S+(?:Ethernet|Serial|Vlan|Loopback|Tunnel)\S*)\s+\S+\s+\S+\s+\S+\s+(administratively\s+down|down)\s+(down)',
        re.IGNORECASE
    )
    # Pattern 2: show interfaces format - "FastEthernet0/1 is down, line protocol is down"
    detail_pattern = re.compile(
        r'(\S+)\s+is\s+(administratively\s+down|down),\s+line\s+protocol\s+is\s+(down)',
        re.IGNORECASE
    )

    found = set()
    for line in show_output.splitlines():
        match = brief_pattern.search(line)
        if match:
            iface = match.group(1)
            status = match.group(2).strip()
            if iface not in found:
                found.add(iface)
                results.append({
                    'check': 'interface_down',
                    'finding': f'{iface} is {status}/down',
                    'severity': 'High'
                })
        else:
            match = detail_pattern.search(line)
            if match:
                iface = match.group(1)
                status = match.group(2).strip()
                if iface not in found:
                    found.add(iface)
                    results.append({
                        'check': 'interface_down',
                        'finding': f'{iface} is {status}/down',
                        'severity': 'High'
                    })

    return results


def check_missing_vlan(show_output: str) -> list:
    """Find VLANs referenced in config but not in show vlan brief."""
    results = []

    # Extract VLANs from show vlan brief (VLAN ID at start of line)
    vlan_brief_pattern = re.compile(r'^(\d+)\s+\S+\s+(?:active|act/unsup|suspend)', re.MULTILINE)
    existing_vlans = set(vlan_brief_pattern.findall(show_output))
    # Always add VLAN 1 as it always exists
    existing_vlans.add('1')

    if not existing_vlans or existing_vlans == {'1'}:
        # No show vlan brief output found, skip this check
        return results

    # Find VLANs referenced in config (access vlan, trunk allowed vlan, encapsulation dot1q, etc.)
    access_vlan_pattern = re.compile(r'(?:access\s+vlan|Access\s+Mode\s+VLAN:?)\s+(\d+)', re.IGNORECASE)
    encap_pattern = re.compile(r'encapsulation\s+dot1[qQ]\s+(\d+)')
    subintf_pattern = re.compile(r'interface\s+\S+\.(\d+)')

    referenced_vlans = set()
    for pattern in [access_vlan_pattern, encap_pattern, subintf_pattern]:
        referenced_vlans.update(pattern.findall(show_output))

    for vlan_id in referenced_vlans:
        if vlan_id not in existing_vlans and vlan_id != '1':
            results.append({
                'check': 'missing_vlan',
                'finding': f'VLAN {vlan_id} is referenced in configuration but not found in show vlan brief',
                'severity': 'Medium'
            })

    return results


def check_missing_route(show_output: str) -> list:
    """Check for destination networks that have no matching route."""
    results = []

    # Check for "Gateway of last resort is not set"
    if 'Gateway of last resort is not set' in show_output:
        # Check if there are multiple networks but no default route
        route_pattern = re.compile(r'[CSORD]\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/\d+')
        routes = route_pattern.findall(show_output)
        if len(routes) >= 1:
            results.append({
                'check': 'missing_route',
                'finding': 'No default route configured (Gateway of last resort is not set)',
                'severity': 'Medium'
            })

    # Check for specific unreachable destinations mentioned in symptoms
    # Look for ping failures to specific IPs that don't have routes
    route_networks = set()
    route_line_pattern = re.compile(
        r'[CSORD]\s+(\d{1,3}\.\d{1,3}\.\d{1,3})\.\d{1,3}/(\d+)'
    )
    for match in route_line_pattern.finditer(show_output):
        route_networks.add(match.group(1))

    return results


def run_all_checks(show_output: str) -> list:
    """Run all deterministic checks and return combined results."""
    results = []
    results.extend(check_duplicate_ips(show_output))
    results.extend(check_wrong_subnet_mask(show_output))
    results.extend(check_gateway_mismatch(show_output))
    results.extend(check_interface_down(show_output))
    results.extend(check_missing_vlan(show_output))
    results.extend(check_missing_route(show_output))
    return results


if __name__ == '__main__':
    try:
        with open('cases.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            total_findings = 0
            for row in reader:
                case_id = row.get('case_id', 'Unknown')
                show_outputs = row.get('show_outputs', '')
                # Convert literal \n to actual newlines
                show_outputs = show_outputs.replace('\\n', '\n')
                findings = run_all_checks(show_outputs)
                total_findings += len(findings)
                print(f"Case {case_id}: {len(findings)} finding(s)")
                for finding in findings:
                    print(f"  - [{finding['severity']}] {finding['check']}: {finding['finding']}")
            print(f"\nTotal: {total_findings} finding(s) across all cases")
    except FileNotFoundError:
        print("Error: cases.csv not found. Make sure you're running this from the project directory.")
        sys.exit(1)
