// XDPGuard - XDP/eBPF DDoS Filter Program
// High-performance packet filtering at NIC driver level

#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/in.h>
#include <linux/tcp.h>
#include <linux/udp.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

#define MAX_BLACKLIST_ENTRIES 10000
#define MAX_RATELIMIT_ENTRIES 65536

// BPF Maps
// IP Blacklist map
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __type(key, __u32);      // IP address
    __type(value, __u8);     // 1 = blocked
    __uint(max_entries, MAX_BLACKLIST_ENTRIES);
} blacklist SEC(".maps");

// Rate limiting map (tracks packet counts per IP)
struct {
    __uint(type, BPF_MAP_TYPE_LRU_HASH);
    __type(key, __u32);      // IP address
    __type(value, __u64);    // packet count
    __uint(max_entries, MAX_RATELIMIT_ENTRIES);
} rate_limit SEC(".maps");

// Statistics map
struct stats {
    __u64 packets_total;
    __u64 packets_dropped;
    __u64 packets_passed;
    __u64 bytes_total;
    __u64 bytes_dropped;
};

struct {
    __uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
    __type(key, __u32);
    __type(value, struct stats);
    __uint(max_entries, 1);
} stats_map SEC(".maps");

// Helper function to parse packet headers
static __always_inline int parse_packet(struct xdp_md *ctx, 
                                        struct ethhdr **eth,
                                        struct iphdr **ip) {
    void *data = (void *)(long)ctx->data;
    void *data_end = (void *)(long)ctx->data_end;

    // Parse Ethernet header
    *eth = data;
    if ((void *)(*eth + 1) > data_end)
        return -1;

    // Check if IPv4
    if ((*eth)->h_proto != bpf_htons(ETH_P_IP))
        return -1;

    // Parse IP header
    *ip = (void *)(*eth + 1);
    if ((void *)(*ip + 1) > data_end)
        return -1;

    return 0;
}

// Update statistics
static __always_inline void update_stats(__u32 action, __u64 bytes) {
    __u32 key = 0;
    struct stats *stat = bpf_map_lookup_elem(&stats_map, &key);
    
    if (!stat)
        return;

    __sync_fetch_and_add(&stat->packets_total, 1);
    __sync_fetch_and_add(&stat->bytes_total, bytes);

    if (action == XDP_DROP) {
        __sync_fetch_and_add(&stat->packets_dropped, 1);
        __sync_fetch_and_add(&stat->bytes_dropped, bytes);
    } else if (action == XDP_PASS) {
        __sync_fetch_and_add(&stat->packets_passed, 1);
    }
}

SEC("xdp")
int xdp_filter_func(struct xdp_md *ctx) {
    struct ethhdr *eth;
    struct iphdr *ip;
    __u32 src_ip;
    __u8 *blocked;
    __u64 *pkt_count;
    __u32 action = XDP_PASS;
    __u64 bytes = (__u64)(ctx->data_end - ctx->data);

    // Parse packet headers
    if (parse_packet(ctx, &eth, &ip) < 0) {
        // Not IPv4 or malformed packet - pass through
        return XDP_PASS;
    }

    src_ip = ip->saddr;

    // Check IP blacklist
    blocked = bpf_map_lookup_elem(&blacklist, &src_ip);
    if (blocked && *blocked) {
        action = XDP_DROP;
        update_stats(action, bytes);
        return XDP_DROP;
    }

    // Rate limiting check
    pkt_count = bpf_map_lookup_elem(&rate_limit, &src_ip);
    if (pkt_count) {
        // Increment packet count
        __sync_fetch_and_add(pkt_count, 1);
        
        // Simple threshold-based rate limiting
        // In production, this should use time-based windows
        if (*pkt_count > 1000) {  // 1000 packets threshold
            action = XDP_DROP;
            update_stats(action, bytes);
            return XDP_DROP;
        }
    } else {
        // First packet from this IP - initialize counter
        __u64 init_count = 1;
        bpf_map_update_elem(&rate_limit, &src_ip, &init_count, BPF_ANY);
    }

    // Additional protocol-specific filtering can be added here
    // For example:
    // - TCP SYN flood detection
    // - UDP flood detection
    // - ICMP flood detection

    // Packet passes all checks
    update_stats(action, bytes);
    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";
