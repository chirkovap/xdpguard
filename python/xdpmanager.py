#!/usr/bin/env python3
"""
XDPGuard XDP Manager

Manages XDP/eBPF programs for DDoS protection.
Handles loading, attaching, and controlling XDP programs via BCC.
"""

import logging
import socket
import struct
from typing import List, Dict, Optional
from bcc import BPF

logger = logging.getLogger(__name__)


class XDPManager:
    """Manages XDP programs for packet filtering"""

    def __init__(self, config: Dict):
        self.config = config
        self.bpf = None
        self.device = config.get('network', {}).get('interface', 'eth0')
        self.program_loaded = False

    def load_program(self, program_path: str = "/usr/lib/xdpguard/xdp_filter.o") -> bool:
        """Load and attach XDP program to network interface"""
        try:
            logger.info(f"Loading XDP program from {program_path}...")
            
            # For production, load compiled .o file
            # For development with BCC, inline the program
            bpf_code = self._get_inline_bpf_code()
            
            self.bpf = BPF(text=bpf_code)
            fn = self.bpf.load_func("xdp_filter_func", BPF.XDP)
            
            # Attach to network interface
            self.bpf.attach_xdp(self.device, fn, 0)
            
            logger.info(f"XDP program attached to {self.device}")
            self.program_loaded = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to load XDP program: {e}")
            return False

    def unload_program(self) -> bool:
        """Detach XDP program from network interface"""
        try:
            if self.bpf and self.program_loaded:
                self.bpf.remove_xdp(self.device, 0)
                logger.info(f"XDP program detached from {self.device}")
                self.program_loaded = False
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to unload XDP program: {e}")
            return False

    def block_ip(self, ip: str) -> bool:
        """Add IP address to blacklist"""
        try:
            if not self.bpf:
                logger.error("BPF program not loaded")
                return False

            blacklist = self.bpf.get_table("blacklist")
            ip_int = self._ip_to_int(ip)
            blacklist[blacklist.Key(ip_int)] = blacklist.Leaf(1)
            
            logger.info(f"Blocked IP: {ip}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to block IP {ip}: {e}")
            return False

    def unblock_ip(self, ip: str) -> bool:
        """Remove IP address from blacklist"""
        try:
            if not self.bpf:
                logger.error("BPF program not loaded")
                return False

            blacklist = self.bpf.get_table("blacklist")
            ip_int = self._ip_to_int(ip)
            
            try:
                del blacklist[blacklist.Key(ip_int)]
                logger.info(f"Unblocked IP: {ip}")
                return True
            except KeyError:
                logger.warning(f"IP {ip} was not in blacklist")
                return False
                
        except Exception as e:
            logger.error(f"Failed to unblock IP {ip}: {e}")
            return False

    def get_blocked_ips(self) -> List[str]:
        """Get list of currently blocked IPs"""
        blocked = []
        try:
            if not self.bpf:
                return blocked

            blacklist = self.bpf.get_table("blacklist")
            for key, value in blacklist.items():
                ip = self._int_to_ip(key.value)
                blocked.append(ip)
                
        except Exception as e:
            logger.error(f"Failed to get blocked IPs: {e}")
            
        return blocked

    def get_statistics(self) -> Dict:
        """Get packet statistics from XDP program"""
        stats = {
            'packets_total': 0,
            'packets_dropped': 0,
            'packets_passed': 0,
            'bytes_total': 0,
            'bytes_dropped': 0
        }
        
        try:
            if not self.bpf:
                return stats

            stats_map = self.bpf.get_table("stats_map")
            key = stats_map.Key(0)
            
            if key in stats_map:
                stat = stats_map[key]
                stats['packets_total'] = stat.packets_total
                stats['packets_dropped'] = stat.packets_dropped
                stats['packets_passed'] = stat.packets_passed
                stats['bytes_total'] = stat.bytes_total
                stats['bytes_dropped'] = stat.bytes_dropped
                
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            
        return stats

    def clear_rate_limits(self) -> bool:
        """Clear rate limiting counters"""
        try:
            if not self.bpf:
                return False

            rate_limit = self.bpf.get_table("rate_limit")
            rate_limit.clear()
            
            logger.info("Rate limit counters cleared")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear rate limits: {e}")
            return False

    @staticmethod
    def _ip_to_int(ip_str: str) -> int:
        """Convert IP address string to integer"""
        return struct.unpack("I", socket.inet_aton(ip_str))[0]

    @staticmethod
    def _int_to_ip(ip_int: int) -> str:
        """Convert integer to IP address string"""
        return socket.inet_ntoa(struct.pack("I", ip_int))

    def _get_inline_bpf_code(self) -> str:
        """Get inline BPF code for BCC (development mode)"""
        return """
#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/in.h>

BPF_HASH(blacklist, u32, u8, 10000);
BPF_HASH(rate_limit, u32, u64, 65536);

struct stats {
    u64 packets_total;
    u64 packets_dropped;
    u64 packets_passed;
    u64 bytes_total;
    u64 bytes_dropped;
};

BPF_PERCPU_ARRAY(stats_map, struct stats, 1);

int xdp_filter_func(struct xdp_md *ctx) {
    void *data = (void *)(long)ctx->data;
    void *data_end = (void *)(long)ctx->data_end;
    
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return XDP_PASS;
    
    if (eth->h_proto != htons(ETH_P_IP))
        return XDP_PASS;
    
    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end)
        return XDP_PASS;
    
    u32 src_ip = ip->saddr;
    u64 bytes = (u64)(data_end - data);
    
    // Update stats
    u32 key = 0;
    struct stats *stat = stats_map.lookup(&key);
    if (stat) {
        lock_xadd(&stat->packets_total, 1);
        lock_xadd(&stat->bytes_total, bytes);
    }
    
    // Check blacklist
    u8 *blocked = blacklist.lookup(&src_ip);
    if (blocked && *blocked) {
        if (stat) {
            lock_xadd(&stat->packets_dropped, 1);
            lock_xadd(&stat->bytes_dropped, bytes);
        }
        return XDP_DROP;
    }
    
    // Rate limiting
    u64 *pkt_count = rate_limit.lookup(&src_ip);
    if (pkt_count) {
        lock_xadd(pkt_count, 1);
        if (*pkt_count > 1000) {
            if (stat) {
                lock_xadd(&stat->packets_dropped, 1);
                lock_xadd(&stat->bytes_dropped, bytes);
            }
            return XDP_DROP;
        }
    } else {
        u64 init = 1;
        rate_limit.update(&src_ip, &init);
    }
    
    if (stat) {
        lock_xadd(&stat->packets_passed, 1);
    }
    
    return XDP_PASS;
}
"""
