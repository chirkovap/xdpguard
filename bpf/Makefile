# XDPGuard BPF Makefile
# Compiles XDP programs with proper BTF support

CLANG ?= clang
LLC ?= llc
ARCH := $(shell uname -m | sed 's/x86_64/x86/' | sed 's/aarch64/arm64/')

# BPF compilation flags with BTF support
BPF_CFLAGS := -g -O2 -Wall \
	-target bpf \
	-D__TARGET_ARCH_$(ARCH) \
	-I/usr/include \
	-I/usr/include/$(shell uname -m)-linux-gnu

# Targets
TARGET := xdp_filter.o
SOURCE := xdp_filter.c
INSTALL_DIR := /usr/lib/xdpguard

.PHONY: all clean install

all: $(TARGET)
	@echo "✓ XDP program compiled successfully"
	@echo "  Output: $(TARGET)"
	@echo "  Size: $$(stat -c%s $(TARGET)) bytes"

$(TARGET): $(SOURCE)
	@echo "Compiling XDP program..."
	$(CLANG) $(BPF_CFLAGS) -c $< -o $@
	@echo "✓ Compilation complete"

install: $(TARGET)
	@echo "Installing XDP program..."
	mkdir -p $(INSTALL_DIR)
	cp $(TARGET) $(INSTALL_DIR)/
	chmod 644 $(INSTALL_DIR)/$(TARGET)
	@echo "✓ XDP program installed to $(INSTALL_DIR)/$(TARGET)"

clean:
	@echo "Cleaning build artifacts..."
	rm -f *.o *.ll
	@echo "✓ Clean complete"

uninstall:
	@echo "Uninstalling XDP program..."
	rm -f $(INSTALL_DIR)/$(TARGET)
	@echo "✓ Uninstall complete"

# Helper targets
check:
	@echo "Checking dependencies..."
	@which $(CLANG) > /dev/null || (echo "ERROR: clang not found" && exit 1)
	@echo "✓ clang found: $$($(CLANG) --version | head -n1)"
	@test -f $(SOURCE) || (echo "ERROR: $(SOURCE) not found" && exit 1)
	@echo "✓ Source file: $(SOURCE)"

info:
	@echo "XDPGuard BPF Makefile"
	@echo "  Compiler: $(CLANG)"
	@echo "  Architecture: $(ARCH)"
	@echo "  Target: $(TARGET)"
	@echo "  Source: $(SOURCE)"
	@echo "  Install dir: $(INSTALL_DIR)"
