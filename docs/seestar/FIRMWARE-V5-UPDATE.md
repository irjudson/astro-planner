# Seestar Firmware v5.x Port Change

## 🔍 Discovery

While testing connection to your Seestar S50 running **firmware v5.50**, we discovered that the control protocol port has changed from the v4.x firmware.

### Port Change Summary
- **Firmware v4.x**: Port 5555
- **Firmware v5.x**: Port 4700

## 📋 Investigation Steps

1. **Initial Issue**: Connection refused on port 5555
2. **Diagnosis**:
   - Ran nmap scan on 192.168.2.47
   - Found port 5555 was NOT open
   - Discovered many new ports in 4000-4800 range
3. **Port Testing**:
   - Tested various ports with JSON commands
   - **Port 4700 responded** with full device state in JSON-RPC 2.0 format
4. **Confirmation**:
   - Response included `firmware_ver_int: 2550` (v5.50)
   - Full device state with all expected fields

## ✅ Code Changes Made

### Backend
1. **seestar_client.py**:
   - Changed `DEFAULT_PORT = 5555` → `DEFAULT_PORT = 4700`
   - Updated docstring

2. **routes.py**:
   - Changed default port in `TelescopeConnectRequest` from 5555 to 4700

### Frontend
3. **index.html**:
   - Updated both telescope connect calls from port 5555 to 4700

## 🧪 Test Results

```bash
$ curl -X POST http://localhost:9247/api/telescope/connect \
  -H "Content-Type: application/json" \
  -d '{"host": "192.168.2.47", "port": 4700}'
```

**Response**:
```json
{
  "connected": true,
  "host": "192.168.2.47",
  "port": 4700,
  "state": "connected",
  "firmware_version": "5.50",
  "message": "Connected to Seestar S50"
}
```

✅ **Connection successful!**

## 📊 Status Check

```bash
$ curl http://localhost:9247/api/telescope/status
```

**Response**:
```json
{
  "connected": true,
  "state": "connected",
  "current_target": null,
  "firmware_version": "5.50",
  "is_tracking": false,
  "last_update": "2025-11-01T23:14:36.268829",
  "last_error": null
}
```

## 🎯 Next Steps

### For You
1. **Hard refresh browser** (Ctrl+Shift+R) to load updated JavaScript
2. Navigate to **Observe** tab or generate a plan
3. Click **Connect** button
4. Should see green ✅ "Connected" with firmware v5.50

### Testing Plan Execution
Once connected, you can test:
1. Generate an observation plan
2. Click "Execute Plan"
3. Monitor progress in real-time
4. Test abort functionality
5. Test park telescope

## 🔬 Technical Details

### JSON-RPC Response from Port 4700
The initial `get_device_state` command returned extensive device info including:
- Device model: "Seestar S50"
- Firmware: 5.50 (firmware_ver_int: 2550)
- Location coordinates: [-111.486000, 45.728900]
- EQ mode: enabled
- Battery: 97%
- Mount state, camera info, focuser position, etc.

### Protocol Compatibility
The JSON-RPC 2.0 protocol appears identical to v4.x firmware, just on a different port. All existing commands should work without modification.

## 📝 Documentation Updated
- ✅ `TESTING-TELESCOPE.md` - Added firmware v5.x notice
- ✅ `seestar_client.py` - Updated comments and defaults
- ✅ `routes.py` - Updated default port
- ✅ `index.html` - Updated connection calls
- ✅ `FIRMWARE-V5-UPDATE.md` - This document

## 🚀 Status

**FULLY OPERATIONAL** ✅

Your Seestar S50 with firmware v5.50 is now successfully connected and ready for automated observation plans!
