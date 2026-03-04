#!/usr/bin/env python3
"""
XDPGuard Config Synchronization

Synchronizes config.yaml with BPF maps in runtime.
This allows changing rate limits without recompiling XDP program.
"""

import logging
import subprocess
import ipaddress
import struct

logger = logging.getLogger(__name__)

# Configuration keys for BPF config_map
CFG_SYN_RATE = 0
CFG_UDP_RATE = 1
CFG_ICMP_RATE = 2
CFG_ENABLED = 3


class ConfigSync:
    """Synchronizes Python config with XDP BPF maps"""
    
    def __init__(self):
        self.synced = False
    
    def sync_config_to_xdp(self, config):
        """
        Synchronize config.yaml values to XDP config_map.
        This updates rate limits in real-time without recompilation.
        """
        try:
            logger.info("Синхронизация конфига с XDP...")
            
            # Get values from config
            syn_rate = config.get('protection.syn_rate', 1000)
            udp_rate = config.get('protection.udp_rate', 500)
            icmp_rate = config.get('protection.icmp_rate', 100)
            enabled = 1 if config.get('protection.enabled', True) else 0
            
            # Update BPF config_map using bpftool
            updates = [
                (CFG_SYN_RATE, syn_rate, "SYN rate limit"),
                (CFG_UDP_RATE, udp_rate, "UDP rate limit"),
                (CFG_ICMP_RATE, icmp_rate, "ICMP rate limit"),
                (CFG_ENABLED, enabled, "Protection enabled")
            ]
            
            for key, value, desc in updates:
                success = self._update_config_map(key, value)
                if success:
                    logger.info(f"✓ {desc}: {value}")
                else:
                    logger.warning(f"✗ Failed to update {desc}")
            
            # Sync whitelist
            self._sync_whitelist(config)
            
            self.synced = True
            logger.info("✓ Конфигурация успешно синхронизирована с XDP")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync config to XDP: {e}")
            return False
    
    def _update_config_map(self, key, value):
        """
        Update single entry in BPF config_map.
        Uses bpftool to update the map.
        """
        try:
            # Convert key and value to hex
            key_bytes = struct.pack('I', key)  # 4 bytes (u32)
            value_bytes = struct.pack('Q', value)  # 8 bytes (u64)
            
            key_hex = ' '.join([f'{b:02x}' for b in key_bytes])
            value_hex = ' '.join([f'{b:02x}' for b in value_bytes])
            
            cmd = [
                'sudo', 'bpftool', 'map', 'update',
                'name', 'config_map',
                'key', 'hex'] + key_hex.split() + [
                'value', 'hex'] + value_hex.split()
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return result.returncode == 0
            
        except Exception as e:
            logger.debug(f"Error updating config_map[{key}]: {e}")
            return False
    
    def _sync_whitelist(self, config):
        """
        Synchronize whitelist IPs from config to XDP whitelist map.
        Whitelisted IPs bypass all filtering.
        """
        try:
            whitelist_ips = config.get('whitelist_ips', [])
            if not whitelist_ips:
                return
            
            logger.info(f"Синхронизация whitelist ({len(whitelist_ips)} записей)...")
            
            for ip_or_network in whitelist_ips:
                try:
                    # Handle both single IPs and CIDR networks
                    network = ipaddress.ip_network(ip_or_network, strict=False)
                    
                    # Add each IP in the network to whitelist
                    for ip in network:
                        if ip.version == 4:  # Only IPv4 for now
                            self._add_to_whitelist(str(ip))
                            
                except ValueError as e:
                    logger.warning(f"Invalid IP/network in whitelist: {ip_or_network}")
            
            logger.info("✓ Whitelist синхронизирован")
            
        except Exception as e:
            logger.error(f"Failed to sync whitelist: {e}")
    
    def _add_to_whitelist(self, ip_address):
        """
        Add single IP to XDP whitelist map.
        """
        try:
            ip_obj = ipaddress.ip_address(ip_address)
            ip_int = int(ip_obj)
            ip_bytes = ip_int.to_bytes(4, byteorder='little')
            key_hex = [f'{b:02x}' for b in ip_bytes]
            
            cmd = ['sudo', 'bpftool', 'map', 'update', 'name', 'whitelist',
                   'key', 'hex'] + key_hex + ['value', 'hex', '01']
            
            subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            
        except Exception as e:
            logger.debug(f"Error adding {ip_address} to whitelist: {e}")
    
    def get_current_config_from_xdp(self):
        """
        Read current configuration from XDP config_map.
        Useful for verification.
        """
        try:
            result = subprocess.run(
                ['sudo', 'bpftool', 'map', 'dump', 'name', 'config_map', '-j'],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                config_values = {}
                for entry in data:
                    key = entry.get('key', [0])[0] if isinstance(entry.get('key'), list) else entry.get('key', 0)
                    value = entry.get('value', [0])[0] if isinstance(entry.get('value'), list) else entry.get('value', 0)
                    
                    if key == CFG_SYN_RATE:
                        config_values['syn_rate'] = value
                    elif key == CFG_UDP_RATE:
                        config_values['udp_rate'] = value
                    elif key == CFG_ICMP_RATE:
                        config_values['icmp_rate'] = value
                    elif key == CFG_ENABLED:
                        config_values['enabled'] = bool(value)
                
                return config_values
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to read config from XDP: {e}")
            return {}
    
    def verify_sync(self, config):
        """
        Verify that config is properly synced with XDP.
        """
        xdp_config = self.get_current_config_from_xdp()
        
        if not xdp_config:
            logger.warning("Не удалось прочитать конфиг из XDP")
            return False
        
        # Compare values
        expected = {
            'syn_rate': config.get('protection.syn_rate', 1000),
            'udp_rate': config.get('protection.udp_rate', 500),
            'icmp_rate': config.get('protection.icmp_rate', 100),
            'enabled': config.get('protection.enabled', True)
        }
        
        mismatches = []
        for key, expected_val in expected.items():
            actual_val = xdp_config.get(key)
            if actual_val != expected_val:
                mismatches.append(f"{key}: expected {expected_val}, got {actual_val}")
        
        if mismatches:
            logger.warning(f"Несоответствия конфига: {', '.join(mismatches)}")
            return False
        
        logger.info("✓ Конфигурация XDP соответствует config.yaml")
        return True
