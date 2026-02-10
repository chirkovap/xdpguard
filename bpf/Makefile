# Makefile for XDPGuard eBPF programs

LLC ?= llc
CLANG ?= clang
CC := gcc

KERN_SOURCES = xdp_filter.c
KERN_OBJECTS = $(KERN_SOURCES:.c=.o)

LINUX_HEADERS = /usr/include
BPF_CFLAGS = -O2 -Wall -target bpf

# Include paths
INCLUDES = -I$(LINUX_HEADERS)

.PHONY: all clean install

all: $(KERN_OBJECTS)

%.o: %.c
	@echo "  CC      $@"
	$(CLANG) $(BPF_CFLAGS) $(INCLUDES) -c $< -o $@

clean:
	@echo "  CLEAN"
	rm -f *.o
	 rm -f *.ll

install: all
	@echo "  INSTALL XDP programs"
	mkdir -p /usr/lib/xdpguard
	cp $(KERN_OBJECTS) /usr/lib/xdpguard/
	@echo "  Installation complete"

uninstall:
	@echo "  UNINSTALL XDP programs"
	rm -rf /usr/lib/xdpguard

help:
	@echo "XDPGuard eBPF Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  all       - Build all eBPF programs (default)"
	@echo "  clean     - Remove build artifacts"
	@echo "  install   - Install compiled programs to /usr/lib/xdpguard"
	@echo "  uninstall - Remove installed programs"
	@echo "  help      - Show this help message"
