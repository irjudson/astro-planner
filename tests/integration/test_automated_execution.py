#!/usr/bin/env python3
"""
Automated telescope execution test (non-interactive).

This script will:
1. Generate an observing plan for tonight
2. Connect to your Seestar S50 telescope
3. Execute the first target from the plan
4. Monitor progress

IMPORTANT: This will actually move your telescope!
This is an automated test with NO confirmation prompts.
Only run this when you're ready for the telescope to move.
"""

import requests
import json
import time
import sys
from datetime import date
from typing import Dict, Any, Optional

# API base URL
BASE_URL = "http://localhost:9247/api"

# Telescope connection details
TELESCOPE_HOST = "192.168.2.47"  # Seestar S50 IP address
TELESCOPE_PORT = 4700  # Port 4700 for firmware v5.x


def print_banner(text: str):
    """Print a prominent banner."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def print_warning(text: str):
    """Print a warning message."""
    print(f"\n⚠️  WARNING: {text}\n")


def generate_plan() -> Dict[str, Any]:
    """Generate tonight's observing plan."""
    print_banner("Step 1: Generate Observing Plan")

    plan_request = {
        "location": {
            "latitude": 45.9183,
            "longitude": -111.5433,
            "elevation": 1234
        },
        "observing_date": date.today().isoformat(),
        "constraints": {
            "min_altitude": 30,
            "max_altitude": 80,
            "min_target_duration_minutes": 20,
            "object_types": ["galaxy", "nebula", "cluster"],
            "planning_mode": "balanced"
        }
    }

    print(f"📅 Date: {plan_request['observing_date']}")
    print(f"📍 Location: Three Forks, MT")
    print(f"\nGenerating plan...")

    response = requests.post(
        f"{BASE_URL}/plan",
        json=plan_request,
        headers={"Content-Type": "application/json"}
    )

    if response.status_code != 200:
        print(f"❌ Failed to generate plan: {response.text}")
        sys.exit(1)

    plan = response.json()

    print(f"✅ Plan generated!")
    print(f"\n📊 Session: {plan['session']['total_imaging_minutes']} minutes")
    print(f"🎯 Targets scheduled: {len(plan['scheduled_targets'])}")

    if len(plan['scheduled_targets']) > 0:
        first_target = plan['scheduled_targets'][0]
        print(f"\n🌟 First target: {first_target['target']['name']}")
        print(f"   Type: {first_target['target']['object_type']}")
        print(f"   Magnitude: {first_target['target']['magnitude']}")
        print(f"   Start: {first_target['start_time']}")
        print(f"   Duration: {first_target['duration_minutes']} minutes")
        print(f"   Altitude: {first_target['start_altitude']:.1f}° → {first_target['end_altitude']:.1f}°")

    return plan


def connect_telescope() -> bool:
    """Connect to the Seestar S50 telescope."""
    print_banner("Step 2: Connect to Telescope")

    print(f"📡 Connecting to {TELESCOPE_HOST}:{TELESCOPE_PORT}...")

    response = requests.post(
        f"{BASE_URL}/telescope/connect",
        json={
            "host": TELESCOPE_HOST,
            "port": TELESCOPE_PORT
        },
        headers={"Content-Type": "application/json"}
    )

    if response.status_code != 200:
        print(f"❌ Failed to connect: {response.text}")
        return False

    result = response.json()
    print(f"✅ Connected!")
    print(f"   Message: {result.get('message', 'OK')}")

    # Get telescope status
    time.sleep(1)
    status_response = requests.get(f"{BASE_URL}/telescope/status")
    if status_response.status_code == 200:
        status = status_response.json()
        print(f"\n📊 Telescope Status:")
        print(f"   Connected: {status.get('connected', False)}")
        print(f"   State: {status.get('state', 'unknown')}")

    return True


def execute_target(plan: Dict[str, Any], target_index: int = 0) -> Optional[str]:
    """Execute a single target from the plan."""
    print_banner(f"Step 3: Execute Target")

    if len(plan['scheduled_targets']) == 0:
        print("❌ No targets in plan!")
        return None

    target = plan['scheduled_targets'][target_index]

    print(f"🎯 Target: {target['target']['name']}")
    print(f"   Coordinates: RA {target['target']['ra_hours']:.4f}h, Dec {target['target']['dec_degrees']:.4f}°")
    print(f"   Duration: {target['duration_minutes']} minutes")
    print(f"   Recommended: {target['recommended_frames']} frames @ {target['recommended_exposure']}s")

    print_warning(f"AUTOMATED MODE: Moving telescope to {target['target']['name']} and starting imaging!")

    # Execute just this one target
    execution_request = {
        "scheduled_targets": [target],  # Only execute first target
        "park_when_done": True
    }

    print(f"\n🚀 Starting execution...")

    response = requests.post(
        f"{BASE_URL}/telescope/execute",
        json=execution_request,
        headers={"Content-Type": "application/json"}
    )

    if response.status_code != 200:
        print(f"❌ Execution failed: {response.text}")
        return None

    result = response.json()
    execution_id = result.get('execution_id', 'unknown')

    print(f"✅ Execution started!")
    print(f"   Execution ID: {execution_id}")
    print(f"   Status: {result.get('status', 'unknown')}")

    return execution_id


def monitor_progress(execution_id: str, duration_seconds: int = 60):
    """Monitor execution progress."""
    print_banner("Step 4: Monitor Progress")

    print(f"📊 Monitoring for {duration_seconds} seconds...")
    print("   (Press Ctrl+C to stop monitoring)\n")

    start_time = time.time()

    try:
        while time.time() - start_time < duration_seconds:
            response = requests.get(f"{BASE_URL}/telescope/progress")

            if response.status_code == 200:
                progress = response.json()

                state = progress.get('state', 'unknown')
                current_target = progress.get('current_target', {})

                if current_target:
                    target_name = current_target.get('name', 'Unknown')
                    print(f"   State: {state} | Target: {target_name}")
                else:
                    print(f"   State: {state}")

                # Show additional details if available
                if 'current_step' in progress:
                    print(f"   Step: {progress['current_step']}")
                if 'progress_percent' in progress:
                    print(f"   Progress: {progress['progress_percent']:.1f}%")
            else:
                print(f"   ⚠️  Could not get progress: {response.status_code}")

            time.sleep(5)  # Update every 5 seconds

    except KeyboardInterrupt:
        print("\n\n⏸️  Monitoring stopped by user")

    print("\n✅ Monitoring complete")
    print("\n💡 To continue monitoring, check:")
    print(f"   GET {BASE_URL}/telescope/progress")


def main():
    """Run the automated execution test."""
    print_banner("Astro Planner - Automated Telescope Execution Test")

    print("⚠️  AUTOMATED MODE - NO CONFIRMATION PROMPTS!")
    print("   This will immediately control your telescope!")
    print("   Make sure your Seestar S50 is:")
    print("   - Powered on")
    print(f"   - Accessible at {TELESCOPE_HOST}")
    print("   - In a safe state to receive commands")
    print("   - Clear view of the sky")
    print("\n🚀 Starting test in 3 seconds...")
    print("   (Press Ctrl+C NOW to cancel)\n")

    try:
        time.sleep(3)
    except KeyboardInterrupt:
        print("\n❌ Test cancelled by user")
        return 1

    try:
        # Step 1: Generate plan
        plan = generate_plan()

        # Step 2: Connect to telescope
        if not connect_telescope():
            print("\n❌ Cannot proceed without telescope connection")
            return 1

        # Step 3: Execute first target
        execution_id = execute_target(plan, target_index=0)

        if not execution_id:
            print("\n❌ Execution not started")
            return 1

        # Step 4: Monitor for 60 seconds
        monitor_progress(execution_id, duration_seconds=60)

        # Summary
        print_banner("Test Complete!")
        print("✅ Successfully executed the workflow:")
        print("   1. Generated observing plan")
        print("   2. Connected to telescope")
        print("   3. Started target execution")
        print("   4. Monitored progress")

        print("\n💡 The telescope is now executing the target!")
        print("   Monitor progress in the web UI or via:")
        print(f"   GET {BASE_URL}/telescope/progress")

        print("\n⚠️  To stop execution:")
        print(f"   POST {BASE_URL}/telescope/abort")

        return 0

    except KeyboardInterrupt:
        print("\n\n⏸️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
