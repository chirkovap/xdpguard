"""Command-line interface for XDPGuard"""

import click
import requests
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from python.config import Config
from python.xdpmanager import XDPManager
from python.stats import StatsCollector


@click.group()
def cli():
    """XDPGuard CLI - DDoS Protection System"""
    pass


@cli.command()
@click.option('--config', default='/etc/xdpguard/config.yaml', help='Config file path')
def start(config):
    """Start XDPGuard protection"""
    click.echo("Starting XDPGuard...")
    
    cfg = Config(config)
    xdp = XDPManager(cfg)
    
    if xdp.load_program():
        click.echo("✓ XDP program loaded successfully")
        click.echo(f"✓ Protection enabled on {cfg.get('network.interface')}")
    else:
        click.echo("✗ Failed to load XDP program", err=True)
        sys.exit(1)


@cli.command()
def stop():
    """Stop XDPGuard protection"""
    click.echo("Stopping XDPGuard...")
    
    cfg = Config()
    xdp = XDPManager(cfg)
    xdp.unload_program()
    
    click.echo("✓ Protection disabled")


@cli.command()
@click.argument('ip')
def block(ip):
    """Block an IP address"""
    cfg = Config()
    xdp = XDPManager(cfg)
    stats = StatsCollector()
    
    # Load program if not loaded
    xdp.load_program()
    
    if xdp.block_ip(ip):
        stats.log_blocked_ip(ip, reason="cli_manual")
        click.echo(f"✓ Blocked: {ip}")
    else:
        click.echo(f"✗ Failed to block: {ip}", err=True)


@cli.command()
@click.argument('ip')
def unblock(ip):
    """Unblock an IP address"""
    cfg = Config()
    xdp = XDPManager(cfg)
    stats = StatsCollector()
    
    # Load program if not loaded
    xdp.load_program()
    
    if xdp.unblock_ip(ip):
        stats.log_unblocked_ip(ip)
        click.echo(f"✓ Unblocked: {ip}")
    else:
        click.echo(f"✗ Failed to unblock: {ip}", err=True)


@cli.command()
def status():
    """Show current status"""
    cfg = Config()
    xdp = XDPManager(cfg)
    
    # Load program to get stats
    if not xdp.load_program():
        click.echo("✗ XDP program not loaded", err=True)
        return
    
    stats = xdp.get_statistics()
    blocked = xdp.get_blocked_ips()
    
    click.echo("\n=== XDPGuard Status ===")
    click.echo(f"Interface: {cfg.get('network.interface')}")
    click.echo(f"Protection: ENABLED")
    click.echo(f"\nPacket Statistics:")
    click.echo(f"  Total:   {stats['packets_total']:,}")
    click.echo(f"  Dropped: {stats['packets_dropped']:,}")
    click.echo(f"  Passed:  {stats['packets_passed']:,}")
    click.echo(f"\nBlocked IPs: {len(blocked)}")
    
    if blocked:
        click.echo("\nRecently blocked (max 10):")
        for ip in blocked[:10]:
            click.echo(f"  - {ip}")


@cli.command()
@click.option('--limit', default=50, help='Number of IPs to show')
def list_blocked(limit):
    """List all blocked IPs"""
    cfg = Config()
    xdp = XDPManager(cfg)
    
    # Load program
    if not xdp.load_program():
        click.echo("✗ XDP program not loaded", err=True)
        return
    
    blocked = xdp.get_blocked_ips()
    
    if not blocked:
        click.echo("No IPs currently blocked")
        return
    
    click.echo(f"\nBlocked IPs ({len(blocked)} total):\n")
    for i, ip in enumerate(blocked[:limit], 1):
        click.echo(f"{i:3d}. {ip}")
    
    if len(blocked) > limit:
        click.echo(f"\n... and {len(blocked) - limit} more")


@cli.command()
def clear_stats():
    """Clear all statistics"""
    cfg = Config()
    xdp = XDPManager(cfg)
    
    if not xdp.load_program():
        click.echo("✗ XDP program not loaded", err=True)
        return
    
    xdp.clear_statistics()
    click.echo("✓ Statistics cleared")


if __name__ == '__main__':
    cli()
