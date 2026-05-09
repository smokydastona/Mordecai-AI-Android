# Mode B: Rooted Device Automation and Recovery Integration

This document defines Mode B automation on the Galaxy S10e reference device, covering both rooted shell-level actions and custom recovery tree integration.

## Overview

Mode B provides two complementary layers of device automation:

1. **Rooted Shell Layer** (Magisk-based): Application-level input injection, settings modification, and event monitoring via ADB with root access.
2. **Recovery Tree Layer** (TWRP/Custom): Boot-level hooks for hardware initialization, firmware patching, and low-level device state transitions.

Both layers remain behind explicit policy enforcement and operator approval surfaces.

## Architecture: Two-Tier Automation Model

```
┌─────────────────────────────────────────────────────────┐
│  Runtime Backend (src/mordecai/)                        │
│  - Policy enforcement (android_control.py)              │
│  - Rooted shell actions                                 │
│  - Recovery/boot state queries                          │
│  - Event listeners and callbacks                        │
└────────────────┬────────────────────────────────────────┘
                 │ ADB + Policy
     ┌───────────┴────────────────────────────────────────┐
     │                                                     │
┌────▼──────────────────────────┐  ┌────────────────────┐ │
│  Rooted Magisk Shell Layer    │  │  Device Tree Layer │ │
│  - Input injection (tap/swipe)│  │  (TWRP/Custom)    │ │
│  - Settings module config     │  │  - Boot hooks      │ │
│  - Property commands          │  │  - Recovery init   │ │
│  - Package dumping            │  │  - Partition info  │ │
│  - Gesture simulation         │  │                    │ │
└──────────────────────────────┘  └────────────────────┘ │
                                                          │
              Root Access (ADB over TCP/USB)
              Bootloader Unlocked
              Knox Tripped (Expected)
```

## Tier 1: Rooted Shell Automation (Magisk)

### Prerequisites

- **Device:** Galaxy S10e (beyond0lte) with bootloader unlocked
- **Rooting Method:** Magisk via patched AP firmware + Odin (see `RobThePCGuy/Rooting-Samsung-Devices`)
- **Access:** ADB with root shell (`adb shell` as root or via Magisk module)
- **Knox Status:** Tripped (cannot be recovered; banking apps may fail SafetyNet without Zygisk deny list)

### Capability Matrix

#### Input Injection

| Action | Command | Policy | Use Case |
|--------|---------|--------|----------|
| Tap | `input tap X Y` | Allowlisted coordinates only | UI navigation, button presses |
| Swipe | `input swipe X1 Y1 X2 Y2 [DURATION]` | Duration capped at 5s | Gesture scrolling, pattern unlock |
| Type | `input text "STRING"` | No special chars without escape | Text input, search boxes |
| Key event | `input keyevent KEYCODE` | Allowlisted keycodes only | Back, Home, Volume, Power (restricted) |

#### Settings Module Actions (via Magisk)

| Action | Command | Policy | Use Case |
|--------|---------|--------|----------|
| Get property | `getprop PROPERTY` | Any readable property | Query device state, ROM version |
| Set property | `setprop PROPERTY VALUE` | Protected properties denied | Configure runtime behavior |
| Get setting | `settings get NAMESPACE KEY` | Any readable setting | Query display, sound, developer options |
| Put setting | `settings put NAMESPACE KEY VALUE` | Protected settings denied | Brightness, timeout (if permitted) |

#### Device State Queries

| Query | Command | Use |
|-------|---------|-----|
| Battery status | `dumpsys battery` | Power monitoring |
| Display state | `dumpsys display` \| grep "Display Power" | Screen lock detection |
| Running processes | `ps \| grep PACKAGE` | App state verification |
| Accessibility enabled | `settings get secure enabled_accessibility_services` | Verify own service status |

#### Gesture Simulation (API 24+)

| Action | Command | Policy |
|--------|---------|--------|
| Swipe gesture | `/system/bin/input swipe` with timing | Duration-capped |
| Multi-finger tap | Via accessibility event injection | Permission-gated |
| Long press | Swipe with 500ms+ duration | Confirmed action only |

### Protected Command Patterns

The following are **always blocked** by policy, regardless of settings:

- `pm uninstall` (package removal)
- `cmd package disable` (system package disablement)
- `reboot` (hard reset without confirmation)
- `setprop ro.*` (immutable properties)
- `settings put global` with high-risk keys (OEM unlock, bootloader state)
- Any command touching `/system/`, `/vendor/`, `/boot/`, or `/recovery/`
- Device administration commands (Device Policy Manager)

## Tier 2: Recovery Tree Integration (Custom TWRP)

### Device Tree Baseline

Use **ExtremeXT/android_device_samsung_exynos9820** as the base:

- **S10e Model:** `beyond0lte` (SM-G970F)
- **SoC:** Exynos 9820/9825
- **Repository:** https://github.com/ExtremeXT/android_device_samsung_exynos9820
- **Branch:** `android-12.1` (latest tested)
- **Build System:** Make-based (BoardConfig.mk, device.mk, recovery.fstab)

### Integration Points for Mode B

#### 1. Custom Recovery Init Script

Path: `recovery/root/init.recovery.custom.rc`

Purpose: Boot-time hooks for Mordecai state capture and safety checks before OS load.

Responsibilities:
- Query partition layout and record to `/metadata/mordecai/recovery-state.json`
- Verify bootloader unlock status via `getprop ro.boot.verifiedbootstate`
- Check for Magisk ramdisk integration completeness
- Log device tree version for update tracking

Example:
```makefile
# In twrp_beyond0lte.mk
BOARD_RECOVERY_MK_ADDITIONS := custom_recovery_init.mk

# custom_recovery_init.mk adds to init.recovery.rc
on early-init
    mkdir /metadata/mordecai 0700 root root
    exec /system/bin/bash -c "getprop ro.boot.verifiedbootstate > /metadata/mordecai/bootstate.txt"
    exec /system/bin/bash -c "test -f /magisk_patched -o -f /magisk.img && echo 1 > /metadata/mordecai/magisk-detected.txt || echo 0 > /metadata/mordecai/magisk-detected.txt"
```

#### 2. Partition Metadata and State Capture

Path: `recovery/root/sbin/capture_mode_b_state.sh`

Purpose: Record boot-time device state that the runtime backend can query post-boot.

Captures:
- `ro.bootloader` (firmware version)
- `ro.build.fingerprint` (ROM build ID)
- `ro.secure` (root allowance flag)
- Partition table (via `blockdev --getsz`)
- Magisk module list (if available)

#### 3. Bootloader State Verification

Path: `BoardConfig.mk` additions

Check that the device tree validates:
- OEM unlock status is irreversible after rooting
- Recovery partition is writable (required for Magisk)
- System-as-root detected (Samsung Galaxy S10e uses this)

#### 4. Firmware Integrity Hooks

Optional: Add hooks to `recovery/root/init.recovery.rc` to verify that the device tree version matches the backend's expected tree version, preventing silently inconsistent automation between shell and recovery layers.

### Building a Custom Mode B Device Tree

```bash
# Clone minimal-manifest-twrp as per ExtremeXT docs
git clone https://github.com/minimal-manifest-twrp/platform_manifest_twrp_aosp.git \
    -b android-12.1 twrp-android-12.1

cd twrp-android-12.1

# Clone the exynos9820 base device tree
git clone https://github.com/ExtremeXT/android_device_samsung_exynos9820.git \
    -b android-12.1 device/samsung/exynos9820

# Create Mode B fork or branch
mkdir -p device/samsung/beyond0lte-mordecai
cp -r device/samsung/exynos9820/beyond0lte/* device/samsung/beyond0lte-mordecai/

# Add Mordecai-specific init and state capture
cat > device/samsung/beyond0lte-mordecai/recovery/root/sbin/mordecai_init.sh << 'EOF'
#!/sbin/bash
# Mordecai Mode B recovery initialization hook

# Capture bootloader state
mkdir -p /metadata/mordecai
getprop ro.bootloader > /metadata/mordecai/bootloader.txt 2>/dev/null
getprop ro.secure > /metadata/mordecai/ro_secure.txt 2>/dev/null
getprop ro.build.fingerprint > /metadata/mordecai/build_fingerprint.txt 2>/dev/null

# Verify system-as-root (should be true for S10e)
if grep -q "system-as-root" /proc/cmdline 2>/dev/null; then
  echo "1" > /metadata/mordecai/system_as_root.txt
else
  echo "0" > /metadata/mordecai/system_as_root.txt
fi

# Detect Magisk if present
if [ -f /magisk.img ] || [ -f /magisk_patched ]; then
  echo "1" > /metadata/mordecai/magisk_detected.txt
else
  echo "0" > /metadata/mordecai/magisk_detected.txt
fi

exit 0
EOF

chmod 755 device/samsung/beyond0lte-mordecai/recovery/root/sbin/mordecai_init.sh

# Update BoardConfig.mk to call the init hook
echo "BOARD_RECOVERY_MK_ADDITIONS := device/samsung/beyond0lte-mordecai/custom_init.mk" \
    >> device/samsung/beyond0lte-mordecai/BoardConfig.mk

# Build the custom recovery
. build/envsetup.sh
lunch twrp_beyond0lte-eng
ALLOW_MISSING_DEPENDENCIES=true mka recoveryimage -j128
```

### State Query API

Post-boot, the runtime can query recovery-captured state:

```python
# In src/mordecai/android_control.py

def get_mode_b_state(self) -> dict[str, Any]:
    """Query Mode B recovery-layer initialization state."""
    result = {}
    state_dir = "/metadata/mordecai"
    
    for key in ["bootloader", "ro_secure", "build_fingerprint", "system_as_root", "magisk_detected"]:
        try:
            state_file = f"{state_dir}/{key}.txt"
            output = subprocess.run(["adb", "shell", f"cat {state_file}"], 
                                  capture_output=True, text=True, check=True)
            result[key] = output.stdout.strip()
        except subprocess.CalledProcessError:
            result[key] = None
    
    return result
```

## Policy Boundaries

### Rooted Shell Layer Enforcement

```python
# In src/mordecai/policy.py, within CommandValidator

ROOTED_SHELL_ALLOWLIST = {
    # Input injection
    r"^adb shell input tap \d+ \d+$",  # tap X Y
    r"^adb shell input swipe \d+ \d+ \d+ \d+ [0-9]{3,4}$",  # swipe with duration
    
    # Settings queries (read-only)
    r"^adb shell settings get \w+ [\w_]+$",  # get NAMESPACE KEY
    r"^adb shell getprop ro\.\w+",  # get ro.* properties
    
    # State queries
    r"^adb shell dumpsys battery$",
    r"^adb shell dumpsys display$",
    r"^adb shell ps$",
}

ROOTED_SHELL_BLOCKED = {
    # No modifications to system partitions
    r"touch /system/.*",
    r"setprop ro\.(boot|secure|build).*",
    
    # No destructive package operations
    r"pm uninstall",
    r"cmd package disable-user",
    
    # No hard reboots
    r"reboot",
    r"poweroff",
}
```

### Recovery Layer Enforcement

Custom device tree builds are **out-of-band** and do not require policy changes; they run at boot before the runtime is active. However, the runtime validates:

1. Recovery partition is **not writable** by default (bootloader protection)
2. Any attempt to reflash recovery requires explicit operator approval
3. Queries to recovery state (`/metadata/mordecai/`) are read-only

## Operational Safety

### Critical Safeguards

1. **Bootloader Lock:** OEM unlock is one-way; once tripped, it cannot be re-locked without a factory reset (expected for Mode B).
2. **Knox Flag:** Permanently tripped after Magisk installation; banking apps and Samsung security features may be unavailable.
3. **Accessibility Service:** Required for lock-screen overlay; must remain enabled throughout the Mode B session.
4. **ADB Daemon:** Runs as root only if Magisk install succeeded; verify via `adb shell id`.
5. **Recovery State:** Persistent across reboots; if invalid, recovery init logs will explain why Mode B hooks failed.

### Operator Approval Checklist

Before enabling Mode B automation, operators must:

- [ ] Install Magisk via the full firmware + Odin process (see rooting guide)
- [ ] Run `adb shell id` and verify `uid=0(root)` output
- [ ] Enable ADB over TCP via `adb tcpip 5555`
- [ ] Custom recovery tree (if used) is built from an audited fork
- [ ] Test recovery state capture: `adb shell cat /metadata/mordecai/bootstate.txt`
- [ ] Acknowledge that Knox is permanently tripped and banking apps may fail
- [ ] Read and accept the rooting guide disclaimer regarding warranty and data loss

## Validation and Testing

### Unit Tests

- `test_android_control.py`: Rooted command allowlist enforcement
- `test_mode_b_state_capture.py`: Recovery layer state query parsing
- `test_policy_protection.py`: Verify protected commands are blocked

### Integration Tests (On-Device)

1. **Shell Layer:**
   - Run `adb shell input tap 100 100` and verify touch registers on-screen
   - Run `adb shell settings get system screen_brightness` and verify read succeeds
   - Run `adb shell setprop ro.boot.test 1` and verify policy rejection

2. **Recovery Layer:**
   - Boot into recovery (Vol Up + Power)
   - Verify `/metadata/mordecai/bootstate.txt` exists and contains valid output
   - Verify Magisk detection logic works (if installed)

3. **End-to-End:**
   - Enable Mode B in config
   - Call `/api/android/mode-b-tap?x=100&y=200` via dashboard
   - Observe on-device touch event
   - Verify API returns success and execution ID

## References

- **Rooting Guide:** https://github.com/RobThePCGuy/Rooting-Samsung-Devices
- **Device Tree (ExtremeXT):** https://github.com/ExtremeXT/android_device_samsung_exynos9820 (branch: android-12.1)
- **TWRP Build Guide:** https://github.com/minimal-manifest-twrp/platform_manifest_twrp_aosp
- **TeamWin S10e Tree:** https://github.com/TeamWin/android_device_samsung_beyond0lte (reference for comparison)

## Future Directions

- HID/gamepad event injection for controller-class input
- Settings persistence hooks via recovery `init.rc` persistence layer
- Automated Mode B health checks via recovery state snapshots
- Conditional automation based on recovery-layer device health (battery %, thermal state)
