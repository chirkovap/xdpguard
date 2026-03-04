// XDPGuard - XDP/eBPF DDoS Filter Program
// High-performance packet filtering at NIC driver level with DYNAMIC configuration

#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/in.h>
#include <linux/tcp.h>
#include <linux/udp.h>
#include <linux/icmp.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

#define MAX_BLACKLIST_ENTRIES 10000
#define MAX_WHITELIST_ENTRIES 1000
#define MAX_RATELIMIT_ENTRIES 65536

// Configuration keys for config_map
#define CFG_SYN_RATE 0
#define CFG_UDP_RATE 1
#define CFG_ICMP_RATE 2
#define CFG_ENABLED 3

// BPF Maps

// Configuration map - stores rate limits (updated by Python from config.yaml)
struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __type(key, __u32);
    __type(value, __u64);
    __uint(max_entries, 10);
} config_map SEC(".maps");

// IP Blacklist map
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __type(key, __u32);      // IP address
    __type(value, __u8);     // 1 = blocked
    __uint(max_entries, MAX_BLACKLIST_ENTRIES);
} blacklist SEC(".maps");

// IP Whitelist map (these IPs are never blocked)
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __type(key, __u32);      // IP address
    __type(value, __u8);     // 1 = whitelisted
    __uint(max_entries, MAX_WHITELIST_ENTRIES);
} whitelist SEC(".maps");

// Rate limiting map with timestamps
struct rate_info {
    __u64 pkt_count;
    __u64 last_reset;
};

struct {
    __uint(type, BPF_MAP_TYPE_LRU_HASH);
    __type(key, __u32);              // IP address
    __type(value, struct rate_info); // packet count + timestamp
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

// Helper: Get configuration value
static __always_inline __u64 get_config(__u32 key, __u64 default_val) {
    __u64 *val = bpf_map_lookup_elem(&config_map, &key);
    return val ? *val : default_val;
}

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

// Check rate limit with time-based window (1 second)
static __always_inline int check_rate_limit(__u32 src_ip, __u8 protocol) {
    struct rate_info *rate = bpf_map_lookup_elem(&rate_limit, &src_ip);
    __u64 now = bpf_ktime_get_ns();
    __u64 one_sec_ns = 1000000000ULL; // 1 second in nanoseconds
    
    // Get rate limit from config based on protocol
    __u64 rate_limit_pps;
    if (protocol == IPPROTO_TCP) {
        rate_limit_pps = get_config(CFG_SYN_RATE, 1000); // Default 1000 pps
    } else if (protocol == IPPROTO_UDP) {
        rate_limit_pps = get_config(CFG_UDP_RATE, 500);  // Default 500 pps
    } else if (protocol == IPPROTO_ICMP) {
        rate_limit_pps = get_config(CFG_ICMP_RATE, 100); // Default 100 pps
    } else {
        return 0; // Pass other protocols
    }
    
    if (rate) {
        // Check if window expired (1 second passed)
        if (now - rate->last_reset > one_sec_ns) {
            // Reset counter for new window
            rate->pkt_count = 1;
            rate->last_reset = now;
        } else {
            // Increment counter
            rate->pkt_count++;
            
            // Check if rate limit exceeded
            if (rate->pkt_count > rate_limit_pps) {
                return 1; // Rate limit exceeded - drop
            }
        }
    } else {
        // First packet from this IP - initialize
        struct rate_info new_rate = {
            .pkt_count = 1,
            .last_reset = now
        };
        bpf_map_update_elem(&rate_limit, &src_ip, &new_rate, BPF_ANY);
    }
    
    return 0; // Rate limit OK
}

SEC("xdp")
int xdp_filter_func(struct xdp_md *ctx) {
    struct ethhdr *eth;
    struct iphdr *ip;
    __u32 src_ip;
    __u8 *whitelisted;
    __u8 *blocked;
    __u32 action = XDP_PASS;
    __u64 bytes = (__u64)(ctx->data_end - ctx->data);

    // Parse packet headers
    if (parse_packet(ctx, &eth, &ip) < 0) {
        // Not IPv4 or malformed packet - pass through
        return XDP_PASS;
    }

    src_ip = ip->saddr;

    // Check if protection is enabled
    __u64 enabled = get_config(CFG_ENABLED, 1);
    if (!enabled) {
        update_stats(XDP_PASS, bytes);
        return XDP_PASS;
    }

    // Check whitelist first - whitelisted IPs bypass all checks
    whitelisted = bpf_map_lookup_elem(&whitelist, &src_ip);
    if (whitelisted && *whitelisted) {
        update_stats(XDP_PASS, bytes);
        return XDP_PASS;
    }

    // Check IP blacklist
    blocked = bpf_map_lookup_elem(&blacklist, &src_ip);
    if (blocked && *blocked) {
        action = XDP_DROP;
        update_stats(action, bytes);
        return XDP_DROP;
    }

    // Rate limiting check (protocol-specific)
    if (check_rate_limit(src_ip, ip->protocol)) {
        action = XDP_DROP;
        update_stats(action, bytes);
        return XDP_DROP;
    }

    // Packet passes all checks
    update_stats(action, bytes);
    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";
