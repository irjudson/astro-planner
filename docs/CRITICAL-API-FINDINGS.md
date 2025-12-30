# CRITICAL Seestar API Findings from APK Analysis

**Date**: 2025-12-29
**Source**: Decompiled Seestar v3.0.0 APK

## ⚠️ CRITICAL: Implementation Errors Found

### 1. **Dew Heater Control - WRONG IMPLEMENTATION**

**Current Implementation (INCORRECT)**:
```python
async def set_dew_heater(self, enabled: bool) -> bool:
    params = {"heater_enable": enabled}
    response = await self._send_command("set_setting", params)
```

**Correct Implementation** (from BaseDeviceViewModel.java:1310-1360):
```python
async def set_dew_heater(self, enabled: bool, power_level: int = 90) -> bool:
    """Control dew heater via pi_output_set2.

    Args:
        enabled: True to turn heater on, False to turn off
        power_level: Heater power level 0-100 (default: 90)

    Returns:
        True if successful
    """
    params = {
        "heater": {
            "state": enabled,
            "value": power_level  # App uses 90 as default
        }
    }
    response = await self._send_command("pi_output_set2", params)
    return response.get("result") == 0
```

**Evidence**:
- File: `/tmp/seestar_v3_decompiled/sources/com/zwoasi/kit/vm/BaseDeviceViewModel.java:1310`
- Command: `PI_OUTPUT_SET_2` (maps to "pi_output_set2")
- Params structure: `SetOutputParams` containing `HeaterParams(state, value)`
- Default power value: **90** (hardcoded in app)

**Source Code**:
```java
com.zwoasi.kit.cmd.CmdMethod r2 = com.zwoasi.kit.cmd.CmdMethod.PI_OUTPUT_SET_2
com.zwoasi.kit.cmd.SetOutputParams r3 = new com.zwoasi.kit.cmd.SetOutputParams
com.zwoasi.kit.cmd.HeaterParams r4 = new com.zwoasi.kit.cmd.HeaterParams
r5 = 90
r4.<init>(r8, r5)  // HeaterParams(state=boolean, value=90)
r3.<init>(r4)
```

---

### 2. **LP Filter - MISSING IMPLEMENTATION**

**Missing From**: `start_view()` method

**Correct Implementation** (from StartViewCmd.java:63):
```python
async def start_view(
    self,
    target_name: str,
    ra: float,
    dec: float,
    lp_filter: bool = False,  # ← MISSING PARAMETER
    is_j2000: bool = True
) -> bool:
    """Start viewing a target with optional LP (light pollution) filter.

    Args:
        target_name: Name of the target
        ra: Right ascension in hours
        dec: Declination in degrees
        lp_filter: Enable light pollution filter (default: False)
        is_j2000: Use J2000 coordinates (default: True)

    Returns:
        True if command successful
    """
    params = {
        "mode": "star",
        "target_name": target_name,
        "target_ra_dec": [ra, dec],
        "lp_filter": lp_filter,  # ← ADD THIS
        "is_j2000": is_j2000
    }
    response = await self._send_command("iscope_start_view", params)
    return response.get("result") == 0
```

**Evidence**:
- File: `/tmp/seestar_v3_decompiled/sources/com/zwo/seestar/socket/command/StartViewCmd.java:63`
- Parameter: `lp_filter` (boolean)
- Part of target params in `iscope_start_view` command

**Source Code**:
```java
jSONObject2.put("lp_filter", this.starInfo.getLpFilter());
```

---

### 3. **Arm Open/Close Commands - INVESTIGATION NEEDED**

**Status**: Command exists in app but exact implementation unclear

**Evidence Found**:
- Methods exist: `setArmOpen()` and `setArmClose()` in BaseDeviceViewModel
- Used in HomeViewDelegate when mount.close status changes
- Likely uses `scope_park` command with parameters OR checks mount state
- **NOT FOUND** in CmdMethod enum as separate command

**Action Required**:
1. Test with live telescope to determine actual command/params
2. Monitor mount state changes after parking
3. May be implicit in mount.close field rather than explicit command

**Hypothesis**:
```python
# Possibility 1: Uses scope_park with close parameter
async def open_telescope_arm(self) -> bool:
    params = {"close": False}  # Unverified
    response = await self._send_command("scope_park", params)
    return response.get("result") == 0

# Possibility 2: State change via scope_park, check mount.close field
async def get_arm_state(self) -> bool:
    """Returns True if arm is closed, False if open."""
    state = await self.get_device_state()
    mount = state.get("mount", {})
    return mount.get("close", False)
```

---

## Additional Findings

### Complete Command Parameter Structures

#### pi_output_set2 (DC Output Control)
```json
{
  "method": "pi_output_set2",
  "params": {
    "heater": {
      "state": true,    // boolean: on/off
      "value": 90       // int: power level 0-100
    }
  }
}
```

#### iscope_start_view (Enhanced)
```json
{
  "method": "iscope_start_view",
  "params": {
    "mode": "star",
    "target_name": "M31",
    "target_ra_dec": [0.712, 41.269],
    "lp_filter": false,   // ← Previously missing
    "is_j2000": true
  }
}
```

#### scope_park (Known Parameters)
```json
{
  "method": "scope_park",
  "params": {
    "equ_mode": true  // boolean: switch to equatorial mode
  }
}
```

---

## Safety Implications

### ⚠️ Heater Control Risk
- **Current implementation may not work at all** (wrong command)
- Heater is critical for preventing dew on optics in humid conditions
- Wrong implementation = users can't control heater = potential equipment damage

### ⚠️ LP Filter Risk
- LP filter improves imaging in light-polluted areas
- Missing parameter = users can't enable filter = degraded image quality
- Not a safety risk, but degrades user experience

### ⚠️ Arm Control Risk (Unknown)
- Telescope arm must be open for observations
- Arm must be closed for safe transport/storage
- **CRITICAL**: Need to verify arm control doesn't break or damage mechanism
- **DO NOT** implement until verified with live testing

---

## Action Items

1. **IMMEDIATE**: Fix heater implementation to use `pi_output_set2`
2. **IMMEDIATE**: Add `lp_filter` parameter to `start_view()`
3. **BEFORE TESTING**: Create comprehensive test suite for all commands
4. **TESTING REQUIRED**: Investigate arm open/close with live telescope
5. **VERIFY**: Test heater control doesn't cause hardware issues
6. **DOCUMENT**: Update API documentation with correct params

---

## Files Analyzed

### Key Source Files
- `/tmp/seestar_v3_decompiled/sources/com/zwoasi/kit/vm/BaseDeviceViewModel.java` - Main controller
- `/tmp/seestar_v3_decompiled/sources/com/zwoasi/kit/cmd/HeaterParams.java` - Heater params structure
- `/tmp/seestar_v3_decompiled/sources/com/zwoasi/kit/cmd/SetOutputParams.java` - Output control params
- `/tmp/seestar_v3_decompiled/sources/com/zwo/seestar/socket/command/StartViewCmd.java` - View command
- `/tmp/seestar_v3_decompiled/sources/com/zwoasi/kit/data/DeviceStateData.java` - State structure
- `/tmp/seestar_v3_decompiled/sources/com/zwoasi/kit/cmd/CmdMethod.java` - Command enum

### Device State Fields
```java
// From DeviceStateData.java:310-317
public final boolean getHeaterEnable() {
    Boolean heaterEnable;
    SeestarSetting seestarSetting = this.setting;
    if (seestarSetting == null || (heaterEnable = seestarSetting.getHeaterEnable()) == null) {
        return false;
    }
    return heaterEnable.booleanValue();
}
```

**Note**: `heater_enable` field EXISTS in device state (read-only status), but heater CONTROL uses `pi_output_set2`, NOT `set_setting`.

---

## References

- APK Version: Seestar v3.0.0
- Decompilation Tool: jadx
- Analysis Date: 2025-12-29
- Analyzer: Claude Code + Human Review

