#!/usr/bin/env python3
"""
Packet Logger for XDPGuard

Stores detailed information about every packet passing through the system.
"""

import time
import json
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging
import socket
import struct

logger = logging.getLogger(__name__)


class PacketLogger:
    """
    Stores and manages detailed packet logs with filtering capabilities.
    Similar to event_logger but specialized for packet-level data.
    """
    
    def __init__(self, max_packets=10000):
        """
        Initialize packet logger.
        
        Args:
            max_packets: Maximum number of packets to store in memory
        """
        self.packets = deque(maxlen=max_packets)
        self.max_packets = max_packets
        logger.info(f"PacketLogger initialized with max_packets={max_packets}")
    
    def log_packet(self, src_ip, dst_ip, protocol, src_port=None, dst_port=None, 
                   size=0, action="PASS", reason=None):
        """
        Log a single packet.
        
        Args:
            src_ip: Source IP address (string)
            dst_ip: Destination IP address (string)
            protocol: Protocol name (TCP/UDP/ICMP/OTHER)
            src_port: Source port (optional)
            dst_port: Destination port (optional)
            size: Packet size in bytes
            action: Action taken (PASS/DROP)
            reason: Reason for action (optional)
        """
        packet = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'src_ip': src_ip,
            'dst_ip': dst_ip,
            'protocol': protocol,
            'src_port': src_port,
            'dst_port': dst_port,
            'size': size,
            'action': action,
            'reason': reason
        }
        
        self.packets.append(packet)
    
    def get_packets(self, limit=100, action=None, protocol=None):
        """
        Get packet logs with optional filtering.
        
        Args:
            limit: Maximum number of packets to return
            action: Filter by action (PASS/DROP)
            protocol: Filter by protocol (TCP/UDP/ICMP)
        
        Returns:
            List of packet dictionaries
        """
        packets = list(self.packets)
        
        # Apply filters
        if action:
            packets = [p for p in packets if p['action'] == action]
        
        if protocol:
            packets = [p for p in packets if p['protocol'] == protocol]
        
        # Return most recent first, limited
        return list(reversed(packets))[:limit]
    
    def get_stats(self):
        """
        Get packet logging statistics.
        
        Returns:
            Dictionary with statistics
        """
        packets = list(self.packets)
        
        stats = {
            'total': len(packets),
            'by_action': defaultdict(int),
            'by_protocol': defaultdict(int),
            'recent_count': {
                'last_minute': 0,
                'last_hour': 0
            }
        }
        
        now = datetime.utcnow()
        one_minute_ago = now - timedelta(minutes=1)
        one_hour_ago = now - timedelta(hours=1)
        
        for packet in packets:
            # Count by action
            stats['by_action'][packet['action']] += 1
            
            # Count by protocol
            stats['by_protocol'][packet['protocol']] += 1
            
            # Count recent packets
            try:
                packet_time = datetime.fromisoformat(packet['timestamp'].replace('Z', '+00:00'))
                if packet_time >= one_minute_ago:
                    stats['recent_count']['last_minute'] += 1
                if packet_time >= one_hour_ago:
                    stats['recent_count']['last_hour'] += 1
            except:
                pass
        
        # Convert defaultdict to regular dict
        stats['by_action'] = dict(stats['by_action'])
        stats['by_protocol'] = dict(stats['by_protocol'])
        
        return stats
    
    def clear(self):
        """
        Clear all packet logs.
        
        Returns:
            Number of packets cleared
        """
        count = len(self.packets)
        self.packets.clear()
        logger.info(f"Cleared {count} packet logs")
        return count
    
    def process_bpf_event(self, cpu, data, size):
        """
        Process packet event from BPF perf buffer.
        
        This is a callback function that will be called by BCC when
        a packet event is received from the eBPF program.
        
        Args:
            cpu: CPU number
            data: Raw packet data from BPF
            size: Size of data
        """
        try:
            # Parse the packet event structure
            # This structure should match the one defined in the eBPF program
            # Example structure (adjust based on your eBPF code):
            # struct packet_event {
            #     __u32 src_ip;
            #     __u32 dst_ip;
            #     __u16 src_port;
            #     __u16 dst_port;
            #     __u8 protocol;
            #     __u8 action;
            #     __u32 size;
            # };
            
            # Unpack data (adjust format string based on your structure)
            src_ip_int, dst_ip_int, src_port, dst_port, protocol_num, action_num, pkt_size = \
                struct.unpack('IIHHHBI', data[:20])
            
            # Convert IP addresses to string format
            src_ip = socket.inet_ntoa(struct.pack('I', src_ip_int))
            dst_ip = socket.inet_ntoa(struct.pack('I', dst_ip_int))
            
            # Map protocol number to name
            protocol_map = {
                6: 'TCP',
                17: 'UDP',
                1: 'ICMP'
            }
            protocol = protocol_map.get(protocol_num, 'OTHER')
            
            # Map action number to name
            action = 'PASS' if action_num == 0 else 'DROP'
            
            # Log the packet
            self.log_packet(
                src_ip=src_ip,
                dst_ip=dst_ip,
                protocol=protocol,
                src_port=src_port if src_port > 0 else None,
                dst_port=dst_port if dst_port > 0 else None,
                size=pkt_size,
                action=action
            )
            
        except Exception as e:
            logger.error(f"Failed to process BPF packet event: {e}")
