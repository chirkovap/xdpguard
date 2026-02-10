"""XDP Program Manager using BCC (BPF Compiler Collection)"""

import logging
from bcc import BPF
import socket
import struct
import time
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class XDPManager:
    """Manage XDP programs for DDoS protection"""
    
    # XDP program in C
    BPF_PROGRAM = """
    #include <linux/bpf.h>
    #include <linux/if_ether.h>
    #include <linux/ip.h>
    #include <linux/in.h>
    #include <linux/tcp.h>
    #include <linux/udp.h>
    
    // BPF map for IP blacklist
    BPF_HASH(blacklist, u32, u8, 10000);
    
    // BPF map for statistics
    BPF_HASH(stats, u32, u64, 10);
    
    // Statistics keys
    #define STAT_TOTAL_PACKETS 0
    #define STAT_DROPPED_PACKETS 1
    #define STAT_PASSED_PACKETS 2
    
    int xdp_filter(struct xdp_md *ctx) {
        void *data = (void *)(long)ctx->data;
        void *data_end = (void *)(long)ctx->data_end;
        
        // Parse Ethernet header
        struct ethhdr *eth = data;
        if ((void *)(eth + 1) > data_end)
            return XDP_PASS;
        
        // Only process IPv4 packets
        if (eth->h_proto != htons(ETH_P_IP))
            return XDP_PASS;
        
        // Parse IP header
        struct iphdr *ip = (void *)(eth + 1);
        if ((void *)(ip + 1) > data_end)
            return XDP_PASS;
        
        // Update total packets counter
        u32 stat_key = STAT_TOTAL_PACKETS;
        u64 *total = stats.lookup(&stat_key);
        if (total) {
            (*total)++;
        } else {
            u64 init_val = 1;
            stats.update(&stat_key, &init_val);
        }
        
        // Check if source IP is blacklisted
        u32 src_ip = ip->saddr;
        u8 *blocked = blacklist.lookup(&src_ip);
        
        if (blocked) {
            // Update dropped packets counter
            stat_key = STAT_DROPPED_PACKETS;
            u64 *dropped = stats.lookup(&stat_key);
            if (dropped) {
                (*dropped)++;
            } else {
                u64 init_val = 1;
                stats.update(&stat_key, &init_val);
            }
            return XDP_DROP;
        }
        
        // Update passed packets counter
        stat_key = STAT_PASSED_PACKETS;
        u64 *passed = stats.lookup(&stat_key);
        if (passed) {
            (*passed)++;
        } else {
            u64 init_val = 1;
            stats.update(&stat_key, &init_val);
        }
        
        return XDP_PASS;
    }
    """
    
    def __init__(self, config):
        self.config = config
        self.interface = config.get('network.interface', 'eth0')
        self.bpf = None
        self.fn = None
        self.blacklist_map = None
        self.stats_map = None
    
    def load_program(self) -> bool:
        """Load and attach XDP program to interface"""
        try:
            logger.info(f"Loading XDP program on interface {self.interface}...")
            
            # Compile BPF program
            self.bpf = BPF(text=self.BPF_PROGRAM)
            self.fn = self.bpf.load_func("xdp_filter", BPF.XDP)
            
            # Attach to interface
            self.bpf.attach_xdp(self.interface, self.fn, 0)
            
            # Get BPF maps
            self.blacklist_map = self.bpf.get_table("blacklist")
            self.stats_map = self.bpf.get_table("stats")
            
            logger.info(f"XDP program attached to {self.interface}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load XDP program: {e}")
            return False
    
    def unload_program(self):
        """Detach XDP program from interface"""
        try:
            if self.bpf:
                self.bpf.remove_xdp(self.interface, 0)
                logger.info(f"XDP program detached from {self.interface}")
        except Exception as e:
            logger.error(f"Failed to unload XDP program: {e}")
    
    def ip_to_int(self, ip_str: str) -> int:
        """Convert IP string to integer"""
        return struct.unpack("I", socket.inet_aton(ip_str))[0]
    
    def int_to_ip(self, ip_int: int) -> str:
        """Convert integer to IP string"""
        return socket.inet_ntoa(struct.pack("I", ip_int))
    
    def block_ip(self, ip: str) -> bool:
        """Add IP to blacklist"""
        try:
            ip_int = self.ip_to_int(ip)
            self.blacklist_map[self.blacklist_map.Key(ip_int)] = self.blacklist_map.Leaf(1)
            logger.info(f"Blocked IP: {ip}")
            return True
        except Exception as e:
            logger.error(f"Failed to block IP {ip}: {e}")
            return False
    
    def unblock_ip(self, ip: str) -> bool:
        """Remove IP from blacklist"""
        try:
            ip_int = self.ip_to_int(ip)
            key = self.blacklist_map.Key(ip_int)
            if key in self.blacklist_map:
                del self.blacklist_map[key]
                logger.info(f"Unblocked IP: {ip}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to unblock IP {ip}: {e}")
            return False
    
    def get_blocked_ips(self) -> List[str]:
        """Get list of all blocked IPs"""
        blocked = []
        try:
            for key, value in self.blacklist_map.items():
                ip = self.int_to_ip(key.value)
                blocked.append(ip)
        except Exception as e:
            logger.error(f"Failed to get blocked IPs: {e}")
        return blocked
    
    def get_statistics(self) -> Dict:
        """Get XDP statistics"""
        stats = {
            'packets_total': 0,
            'packets_dropped': 0,
            'packets_passed': 0,
        }
        
        try:
            # Key 0: total packets
            key = self.stats_map.Key(0)
            if key in self.stats_map:
                stats['packets_total'] = self.stats_map[key].value
            
            # Key 1: dropped packets
            key = self.stats_map.Key(1)
            if key in self.stats_map:
                stats['packets_dropped'] = self.stats_map[key].value
            
            # Key 2: passed packets
            key = self.stats_map.Key(2)
            if key in self.stats_map:
                stats['packets_passed'] = self.stats_map[key].value
                
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
        
        return stats
    
    def clear_statistics(self):
        """Clear all statistics"""
        try:
            for key in [0, 1, 2]:
                stat_key = self.stats_map.Key(key)
                if stat_key in self.stats_map:
                    self.stats_map[stat_key] = self.stats_map.Leaf(0)
            logger.info("Statistics cleared")
        except Exception as e:
            logger.error(f"Failed to clear statistics: {e}")
