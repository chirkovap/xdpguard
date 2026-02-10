#!/usr/bin/env python3
"""
XDPGuard CLI Tool

Command-line interface for managing XDP DDoS protection.
"""

import click
import requests
import json
import sys
from pathlib import Path

# API endpoint
API_BASE = "http://localhost:8080/api"


@click.group()
def cli():
    """XDPGuard CLI - DDoS Protection Management Tool"""
    pass


@cli.command()
def status():
    """Show current system status and statistics"""
    try:
        response = requests.get(f"{API_BASE}/status")
        data = response.json()
        
        click.echo("="*50)
        click.echo("XDPGuard Status")
        click.echo("="*50)
        click.echo(f"Protection: {'ENABLED' if data['protection_enabled'] else 'DISABLED'}")
        click.echo(f"Status: {data['status'].upper()}")
        click.echo("")
        
        stats = data['stats']
        click.echo("Statistics:")
        click.echo(f"  Total Packets:   {stats['packets_total']:,}")
        click.echo(f"  Dropped:         {stats['packets_dropped']:,}")
        click.echo(f"  Passed:          {stats['packets_passed']:,}")
        click.echo(f"  Total Bytes:     {stats['bytes_total']:,}")
        click.echo(f"  Dropped Bytes:   {stats['bytes_dropped']:,}")
        click.echo("")
        
        click.echo(f"Blocked IPs: {data['blocked_count']}")
        if data['blocked_ips']:
            click.echo("  Recent blocks:")
            for ip in data['blocked_ips'][:10]:
                click.echo(f"    - {ip}")
        
    except requests.exceptions.ConnectionError:
        click.echo("ERROR: Cannot connect to XDPGuard service", err=True)
        click.echo("Make sure the service is running: systemctl status xdpguard", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('ip')
def block(ip):
    """Block an IP address"""
    try:
        response = requests.post(
            f"{API_BASE}/block",
            json={'ip': ip},
            headers={'Content-Type': 'application/json'}
        )
        data = response.json()
        
        if data['success']:
            click.echo(f"✓ IP {ip} blocked successfully")
        else:
            click.echo(f"✗ Failed to block IP {ip}: {data.get('error', 'Unknown error')}", err=True)
            sys.exit(1)
            
    except requests.exceptions.ConnectionError:
        click.echo("ERROR: Cannot connect to XDPGuard service", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('ip')
def unblock(ip):
    """Unblock an IP address"""
    try:
        response = requests.post(
            f"{API_BASE}/unblock",
            json={'ip': ip},
            headers={'Content-Type': 'application/json'}
        )
        data = response.json()
        
        if data['success']:
            click.echo(f"✓ IP {ip} unblocked successfully")
        else:
            click.echo(f"✗ Failed to unblock IP {ip}: {data.get('error', 'Unknown error')}", err=True)
            sys.exit(1)
            
    except requests.exceptions.ConnectionError:
        click.echo("ERROR: Cannot connect to XDPGuard service", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)


@cli.command(name='list-blocked')
def list_blocked():
    """List all blocked IP addresses"""
    try:
        response = requests.get(f"{API_BASE}/blocked")
        data = response.json()
        
        if not data['blocked_ips']:
            click.echo("No IPs currently blocked")
            return
        
        click.echo(f"Total blocked IPs: {data['count']}")
        click.echo("")
        
        for idx, ip in enumerate(data['blocked_ips'], 1):
            click.echo(f"{idx:3d}. {ip}")
            
    except requests.exceptions.ConnectionError:
        click.echo("ERROR: Cannot connect to XDPGuard service", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)


@cli.command(name='clear-rate-limits')
def clear_rate_limits():
    """Clear rate limiting counters"""
    try:
        response = requests.post(
            f"{API_BASE}/clear-rate-limits",
            headers={'Content-Type': 'application/json'}
        )
        data = response.json()
        
        if data['success']:
            click.echo("✓ Rate limit counters cleared")
        else:
            click.echo("✗ Failed to clear rate limits", err=True)
            sys.exit(1)
            
    except requests.exceptions.ConnectionError:
        click.echo("ERROR: Cannot connect to XDPGuard service", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--output', '-o', type=click.Path(), help='Output file path')
def export(output):
    """Export statistics to JSON file"""
    try:
        response = requests.get(f"{API_BASE}/status")
        data = response.json()
        
        if output:
            output_path = Path(output)
        else:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = Path(f'xdpguard_stats_{timestamp}.json')
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        click.echo(f"✓ Statistics exported to {output_path}")
        
    except requests.exceptions.ConnectionError:
        click.echo("ERROR: Cannot connect to XDPGuard service", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"ERROR: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
