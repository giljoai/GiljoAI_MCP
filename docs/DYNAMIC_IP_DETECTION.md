# Dynamic Network Adapter IP Detection and CORS Update System

## Overview

The dynamic IP detection system automatically detects network adapter IP changes at API startup and updates CORS origins accordingly. This enables seamless operation when switching networks, DHCP renewals, VPN connections, or mobile hotspot changes.

## Architecture

### Components

1. **AdapterIPDetector** (src/giljo_mcp/network_detector.py)
   - Cross-platform network adapter detection (Windows, Linux, macOS)
   - IP change detection by comparing current vs stored IP
   - Graceful fallback to localhost if adapter disconnected
   - Recommended adapter selection

2. **API Integration** (api/app.py)
   - Called before CORS middleware setup in create_app()
   - Updates CORS origins dynamically if IP changed
   - Logs serving address with adapter name
   - Handles errors gracefully without disrupting startup

3. **Configuration** (config.yaml)
   - Stores selected adapter and initial IP in security.network section

## Configuration Format

security:
  network:
    selected_adapter: "Ethernet"  # Adapter name/interface ID
    initial_ip: "10.1.0.164"      # IP at configuration time
    adapter_selection_method: "manual"  # or "automatic"

## Startup Flow

1. API Starts → create_app() called
2. Load CORS Config → Read static origins from config.yaml
3. Detect IP → Call AdapterIPDetector.detect_ip_change(config)
4. Compare IPs → Check current IP vs security.network.initial_ip
5. Update CORS → If changed, add new origins to CORS list
6. Log Result → Show adapter name and serving address
7. Continue Startup → CORS middleware configured with updated origins

## IP Change Scenarios

### Scenario 1: IP Unchanged
INFO - Network adapter IP unchanged: Ethernet @ 10.1.0.164

### Scenario 2: IP Changed
INFO - IP changed for 'Ethernet': 10.1.0.164 -> 10.1.0.200
INFO - Added CORS origin: http://10.1.0.200:7274

### Scenario 3: Adapter Disconnected
WARNING - Adapter 'Ethernet' disconnected - using localhost fallback

## Cross-Platform Support

- Windows: "Ethernet", "Wi-Fi", "Local Area Connection"
- Linux: "eth0", "wlan0", "enp0s3"
- macOS: "en0", "en1", "en2"

## Security

- No wildcard CORS origins
- Explicit origins only
- Graceful localhost fallback
- Validates adapter names

## Implementation Status: COMPLETE

All core functionality implemented and tested:
- [x] AdapterIPDetector class created
- [x] Cross-platform adapter detection
- [x] IP change detection
- [x] Adapter disconnection fallback
- [x] Integration with api/app.py
- [x] Dynamic CORS origin updates
- [x] Serving address logging
- [x] Comprehensive testing
