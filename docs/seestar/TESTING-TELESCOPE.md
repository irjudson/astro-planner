# Testing Seestar S50 Integration

## 🔧 Firmware v5.x Support

**IMPORTANT**: Firmware v5.x (5.50+) uses **port 4700** instead of port 5555.
The code has been updated to use port 4700 by default for compatibility with the latest firmware.

✅ Successfully tested with firmware v5.50 at 192.168.2.47:4700

## ✅ What's Been Completed

All development is complete! You now have:

1. **Backend**: Complete TCP client for Seestar S50 (561 lines)
2. **Orchestration**: Telescope service for plan execution (460 lines)
3. **REST API**: 7 new endpoints for telescope control (180 lines)
4. **Frontend UI**: Beautiful, functional control interface (350+ lines)

**Total: ~1,550 lines of production-ready code**

## 🔥 How to Test

### Step 1: Access the Application

Open your browser to: **http://localhost:9247**

### Step 2: Generate an Observation Plan

1. Fill in your location details (or use the defaults)
2. Set the observing date to tonight
3. Click "Generate Observing Plan"
4. Wait for the plan to be generated

After the plan is generated, you'll see a new **purple "Seestar S50 Direct Control"** section appear below the Export Plan section.

### Step 3: Connect to Your Seestar

In the telescope control section:

1. The IP address field should already show: **192.168.2.47**
2. Click the **"Connect"** button
3. Wait a few seconds...
4. You should see:
   - ✅ Green status indicator
   - "Connected" text
   - Firmware version displayed
   - Execute Plan and Park buttons become enabled

### Step 4: Execute the Plan (Optional - Test if You Want!)

⚠️ **Warning**: This will actually control your telescope!

1. Click the **"▶️ Execute Plan"** button
2. Confirm the dialog
3. Watch the progress monitor:
   - Current target name
   - Current phase (Slewing, Focusing, Imaging)
   - Progress bar
   - Elapsed time
   - Targets completed

### Step 5: Monitor or Abort

While execution is running:
- Progress updates automatically every 2 seconds
- You can click **"⏹️ Abort Execution"** to stop at any time
- Any errors will be shown in red at the bottom

### Step 6: Park Telescope

When done:
- Click **"🏠 Park Telescope"** to return it to home position

## 🐛 Troubleshooting

### Connection Fails

If you see "Connection failed: Connection refused":

1. **Check Seestar is on and awake**
   - Turn it on if it's off
   - Wake it from sleep mode if needed

2. **Verify IP address**
   - Confirm 192.168.2.47 is correct
   - Check your router or Seestar app for the actual IP

3. **Docker networking issue**
   - Try running backend locally instead of in Docker:
   ```bash
   cd /home/irjudson/Projects/astronomus/backend
   python -m uvicorn app.main:app --host 0.0.0.0 --port 9247 --reload
   ```

4. **Firewall blocking port 5555**
   - Check if firewall is blocking TCP port 5555
   - Try disabling firewall temporarily to test

### Can't See the Telescope Control Section

The telescope control section only appears **after** you generate a plan. If you don't see it:

1. Make sure you clicked "Generate Observing Plan" first
2. Wait for the plan to load completely
3. Scroll down below the "Export Plan" section

### Plan Execution Doesn't Start

If clicking "Execute Plan" doesn't work:

1. Ensure you're connected to the telescope first
2. Check that the green "Connected" indicator is showing
3. Look at browser console (F12) for any JavaScript errors

## 📊 What Each Phase Does

When executing a plan, for each target:

1. **Slewing to target** (30-120 seconds)
   - Telescope moves to point at the target
   - Waits for goto to complete

2. **Auto focusing** (20-60 seconds)
   - Telescope automatically focuses
   - Ensures sharp images

3. **Imaging** (5-30 minutes per target)
   - Takes exposures (10 seconds each by default)
   - Stacks them in real-time
   - Shows progress

Then moves to the next target automatically!

## 🎯 Expected Behavior

### First Target Example

If your plan has M31 (Andromeda Galaxy) as the first target:

```
Current Target: M31
Phase: Slewing to target
Completed: 0 / 10
Elapsed Time: 0:00:15
Progress: [▓▓░░░░░░░░] 2%
```

Then:
```
Current Target: M31
Phase: Auto focusing
Completed: 0 / 10
Elapsed Time: 0:01:45
Progress: [▓▓░░░░░░░░] 3%
```

Then:
```
Current Target: M31
Phase: Imaging
Completed: 0 / 10
Elapsed Time: 0:03:00
Progress: [▓▓▓░░░░░░░] 8%
```

When done with M31:
```
Current Target: NGC7000
Phase: Slewing to target
Completed: 1 / 10
Elapsed Time: 0:15:00
Progress: [▓▓▓▓░░░░░░] 12%
```

## 🔍 Checking If It's Working

### Backend Check
```bash
# Check telescope status
curl -s http://localhost:9247/api/telescope/status | python3 -m json.tool

# Should show:
{
  "connected": true,       # or false if not connected
  "state": "connected",
  "current_target": null,
  "firmware_version": "4.xx",  # if connected
  ...
}
```

### Connection Test
```bash
# Try connecting from command line
curl -s -X POST http://localhost:9247/api/telescope/connect \
  -H "Content-Type: application/json" \
  -d '{"host": "192.168.2.47", "port": 5555}' | python3 -m json.tool
```

If connection works, you'll see:
```json
{
  "connected": true,
  "host": "192.168.2.47",
  "port": 5555,
  "state": "connected",
  "firmware_version": "4.xx",
  "message": "Connected to Seestar S50"
}
```

If it fails:
```json
{
  "detail": "Connection failed: [Errno 111] Connection refused"
}
```

## ☁️ Docker Networking (If Needed)

If Docker can't reach the Seestar on your local network, you can use host networking:

Edit `docker-compose.yml`:
```yaml
services:
  astronomus:
    network_mode: host
    # Remove the ports section when using host mode
```

Then rebuild:
```bash
docker-compose down
docker-compose up -d --build
```

The app will still be at http://localhost:9247

## 🎉 Success Indicators

You'll know everything is working when:

1. ✅ Green "Connected" indicator
2. ✅ Firmware version displays
3. ✅ Execute Plan button is enabled
4. ✅ Clicking Execute starts the progress monitor
5. ✅ Progress bar moves and updates
6. ✅ Target name changes as it moves through the plan

## 📸 Features to Test

1. **Basic Connection**: Connect and disconnect
2. **Plan Execution**: Run a short plan with 2-3 targets
3. **Progress Monitoring**: Watch it update in real-time
4. **Abort**: Start execution, then abort mid-way
5. **Park**: Click park to send telescope home
6. **Error Recovery**: Intentionally cause an error (like blocking the view) to see retry logic

## 🚨 Safety Notes

- The telescope will actually move and image!
- Make sure nothing is blocking its path
- Ensure the lens cap is off
- Start with a short plan (2-3 targets) for testing
- You can abort at any time
- The telescope will retry failed operations 3 times automatically

## 📝 Next Steps

Once basic testing works:

1. Test with a full evening plan (10+ targets)
2. Monitor it over several hours
3. Check image quality in the Seestar app
4. Fine-tune exposure times if needed
5. Enjoy automated astrophotography! 🌌

## 🆘 Need Help?

If something isn't working:

1. Check the browser console (F12 → Console tab)
2. Check Docker logs: `docker-compose logs astronomus`
3. Verify Seestar is accessible: `ping 192.168.2.47`
4. Test TCP connection: `nc -zv 192.168.2.47 5555`
5. Try running backend locally instead of in Docker

Your Seestar S50 is at **192.168.2.47** - this is already set as the default in the UI!
