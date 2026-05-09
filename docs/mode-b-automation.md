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

## Ecosystem Resources: Complete GitHub Index

This section catalogs the complete ecosystem of tools, device trees, kernels, and recovery systems relevant to Mode B rooting and automation on Samsung Exynos 9820 devices (S10e reference).

### 🔹 Device Trees & Platform Support

**Critical (Direct S10e Support)**
- **TeamWin/android_device_samsung_beyond0lte** (https://github.com/TeamWin/android_device_samsung_beyond0lte)
  - TWRP device tree for S10e (beyond0lte) — reference for custom recovery builds
  - Branch: android-9.0 (older) or consider updating to 12.1+ via ExtremeXT fork

- **ExtremeXT/android_device_samsung_exynos9820** (https://github.com/ExtremeXT/android_device_samsung_exynos9820)
  - **Recommended base for Mode B custom tree**
  - Exynos 9820/9825 unified device tree covering S10/S10+/S10e/Note10 variants
  - Branch: android-12.1 (latest tested, actively maintained)
  - Built against minimal-manifest-twrp; full build instructions provided

**Alternative Implementations**
- **exynos9820-dev/android_device_samsung_beyond0lte** (https://github.com/exynos9820-dev/android_device_samsung_beyond0lte)
  - Community-maintained alternative S10e device tree
  - May have different init hooks or partition layouts; verify against ExtremeXT

### 🔹 Kernel & Vendor Platform

**Core Platform (Required for Custom Device Trees)**
- **exynos9820-dev/android_kernel_samsung_exynos9820** (https://github.com/exynos9820-dev/android_kernel_samsung_exynos9820)
  - Kernel source for Exynos 9820 (S10 family)
  - Required if building custom device tree with kernel modifications
  - Mode B integration points: boot arguments, ramdisk hooks, partition discovery

- **exynos9820-dev/android_vendor_samsung_exynos9820** (https://github.com/exynos9820-dev/android_vendor_samsung_exynos9820)
  - Vendor blobs and HAL implementations for Exynos 9820
  - Required for full TWRP recovery build with hardware-specific drivers

### 🔹 Recovery Builders & Boot Systems

**TWRP (Recommended for Mode B)**
- **TeamWin/android_bootable_recovery** (https://github.com/TeamWin/android_bootable_recovery)
  - TWRP recovery source (base binary and lifecycle)
  - Used in conjunction with device tree to build recovery.img
  - **Preferred for Mode B:** Mature, well-documented, stable init.rc ecosystem

- **TeamWin/android_device_samsung_exynos9820** (https://github.com/TeamWin/android_device_samsung_exynos9820)
  - TWRP device tree for Exynos 9820 family (same as base ExtremeXT)

**Alternative Recovery Systems**
- **SHRP/SHRP-device-tree-samsung_beyond0lte** (https://github.com/SHRP/SHRP-device-tree-samsung_beyond0lte)
  - SHRP (Skyhawk Recovery Project) — lightweight alternative to TWRP
  - Smaller image footprint; suitable if recovery partition is space-constrained
  - Less mature ecosystem; TWRP is recommended for Mode B stability

### 🔹 Root Frameworks & Magisk

**Primary (Magisk - Recommended for Mode B)**
- **topjohnwu/Magisk** (https://github.com/topjohnwu/Magisk)
  - **Industry-standard rooting framework**
  - System-as-root compatible (required for S10e)
  - Zygisk hooks for app-specific root access control
  - SafetyNet/Play Integrity bypass modules available
  - **Mode B uses this:** Magisk + patched firmware = rooted shell access

- **topjohnwu/libsu** (https://github.com/topjohnwu/libsu)
  - Magisk library for native apps to request root via Magisk's IPC
  - Optional: Use if building native utilities that require root context
  - Not required for basic Mode B ADB shell access

**Alternative: Kernel-Level Root**
- **tiann/KernelSU** (https://github.com/tiann/KernelSU)
  - Kernel-level root alternative (newer, less mature)
  - **Pros:** No bootloader unlock required (on supported kernels), kernel-integrated permission model
  - **Cons:** Not compatible with Magisk; requires custom kernel build
  - **Not recommended for Mode B Phase 1:** Stick with Magisk + standard firmware

### 🔹 Flashing Tools & Firmware Utilities

**Primary (Samsung Odin - Proprietary)**
- Samsung Odin v3.14.1 (patched) — download from XDA forums via rooting guide
  - **Required for initial root installation** (flashing patched AP firmware)
  - No open-source equivalent; closed-source Samsung tool

**Open-Source Alternatives**
- **Benjamin-Dobell/Heimdall** (https://github.com/Benjamin-Dobell/Heimdall)
  - **Open-source alternative to Odin**
  - Supports Samsung Exynos devices; cross-platform (Windows/Linux/Mac)
  - Compatible with S10e; can replace Odin for firmware flashing
  - **Advantage:** Transparent, scriptable, GPL-licensed
  - **Caution:** Less tested than Odin on Samsung; use at own risk

**Firmware Downloader**
- **zxz0O0/SamFirm_Reborn** (https://github.com/zxz0O0/SamFirm_Reborn)
  - Modern Samsung firmware downloader (replaces deprecated Samloader)
  - Fetches official firmware from Samsung servers without requiring device-specific serial
  - Used in rooting workflow as **Step 2** (download official firmware)

### 🔹 Security & Exploit Research (Context & Reference)

These repos provide educational context on Samsung bootloader, TrustZone, and exploit research — useful for understanding attack surfaces but not required for Mode B operator workflows.

- **alephsecurity/samsung-mobicore** (https://github.com/alephsecurity/samsung-mobicore)
  - TrustZone (Secure Monitor Call) research for Samsung devices
  - Reference: Bootloader security model and Knox architecture

- **Comsecuris/qsee_research** (https://github.com/Comsecuris/qsee_research)
  - Qualcomm Secure Execution Environment (QSEE) research
  - Not directly applicable to Exynos 9820 (Qualcomm variant), but educational for understanding ARM TrustZone patterns

### 🔹 Minimal TWRP Manifest (Build System)

- **minimal-manifest-twrp/platform_manifest_twrp_aosp** (https://github.com/minimal-manifest-twrp/platform_manifest_twrp_aosp)
  - **Required for building custom TWRP recovery**
  - Repo manifest that fetches TWRP sources, device tree, and build system
  - ExtremeXT device tree is tested against this manifest (branch: android-12.1)

### Recommended Implementation Path for Mode B Custom Recovery

1. **Base:** Clone minimal-manifest-twrp (android-12.1 branch)
2. **Device Tree:** Clone ExtremeXT/android_device_samsung_exynos9820 (android-12.1 branch)
3. **Kernel (Optional):** exynos9820-dev/android_kernel_samsung_exynos9820 if custom boot hooks needed
4. **Vendor:** exynos9820-dev/android_vendor_samsung_exynos9820 (optional, for full HAL)
5. **Build:** Follow ExtremeXT README for build environment setup and mka recoveryimage
6. **Flash:** Use Odin (proprietary) or Heimdall (open-source) to flash the recovery.img

### Known Ecosystem Gaps & Caveats

- **Odin is proprietary:** No full open-source replacement for Samsung Odin exists; Heimdall is the best alternative but has less testing coverage
- **S10e specific:** beyond0lte is one of several Exynos 9820 variants; device tree unification (ExtremeXT) helps but vendor-specific blobs may differ
- **Knox is permanent:** Once tripped by Magisk/rooting, Knox cannot be restored; system-level security features degrade
- **QSEE vs Knox:** S10e uses ARM TrustZone + Samsung Knox (not Qualcomm QSEE); research repos for QSEE are educational but not directly applicable

## Future Directions

- HID/gamepad event injection for controller-class input
- Settings persistence hooks via recovery `init.rc` persistence layer
- Automated Mode B health checks via recovery state snapshots
- Conditional automation based on recovery-layer device health (battery %, thermal state)
