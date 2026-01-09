#!/usr/bin/env python3
"""
Interactive script to record Seestar telescope sessions.

Usage:
    python scripts/record_seestar_session.py --name goto_success --host 192.168.2.47
    python scripts/record_seestar_session.py --name imaging_session --host 192.168.2.47 --description "Full imaging workflow"

The script will:
1. Start a recording proxy between your client and the telescope
2. Allow you to run commands interactively
3. Save the complete session as a JSON recording for playback in tests
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from app.clients.seestar_client import SeestarClient
from tests.fixtures.seestar_recorder import SeestarSessionRecorder


async def interactive_session(recorder: SeestarSessionRecorder, proxy_host: str, proxy_port: int):
    """Run interactive session with the telescope through recording proxy.

    Args:
        recorder: Session recorder instance
        proxy_host: Proxy server host
        proxy_port: Proxy server port
    """
    print("\n" + "=" * 70)
    print("SEESTAR SESSION RECORDER")
    print("=" * 70)
    print(f"\nProxy listening on {proxy_host}:{proxy_port}")
    print("All traffic will be recorded for playback in tests.\n")

    # Create client connected through proxy
    client = SeestarClient()

    try:
        print("Connecting to telescope through proxy...")
        await client.connect(proxy_host, proxy_port)
        print(f"✓ Connected! Status: {client.status.state.value}\n")

        print("Available commands:")
        print("  status        - Show telescope status")
        print("  goto <ra> <dec> <name> - Slew to coordinates")
        print("  focus         - Start autofocus")
        print("  imaging       - Start imaging")
        print("  stop          - Stop current operation")
        print("  park          - Park telescope")
        print("  info          - Get system info")
        print("  quit          - End recording and save")
        print()

        while True:
            try:
                cmd = input(">>> ").strip()
                if not cmd:
                    continue

                parts = cmd.split()
                command = parts[0].lower()

                if command == "quit":
                    print("\nEnding session...")
                    break

                elif command == "status":
                    print(f"State: {client.status.state.value}")
                    print(f"RA: {client.status.ra}, Dec: {client.status.dec}")
                    print(f"Connected: {client.connected}")

                elif command == "goto":
                    if len(parts) < 4:
                        print("Usage: goto <ra> <dec> <name>")
                        continue
                    ra, dec, name = float(parts[1]), float(parts[2]), parts[3]
                    print(f"Slewing to {name} (RA={ra}, Dec={dec})...")
                    success = await client.goto_target(ra, dec, name)
                    print(f"✓ Goto {'started' if success else 'failed'}")

                elif command == "focus":
                    print("Starting autofocus...")
                    success = await client.auto_focus()
                    print(f"✓ Autofocus {'started' if success else 'failed'}")

                elif command == "imaging":
                    print("Starting imaging session...")
                    success = await client.start_imaging(restart=True)
                    print(f"✓ Imaging {'started' if success else 'failed'}")

                elif command == "stop":
                    print("Stopping current operation...")
                    success = await client.stop_imaging()
                    print(f"✓ Stop {'successful' if success else 'failed'}")

                elif command == "park":
                    print("Parking telescope...")
                    success = await client.park()
                    print(f"✓ Park {'started' if success else 'failed'}")

                elif command == "info":
                    print("Getting system info...")
                    info = await client.get_pi_info()
                    print(f"Firmware: {info.get('firmware_version', 'unknown')}")
                    print(f"Device ID: {info.get('device_id', 'unknown')}")

                else:
                    print(f"Unknown command: {command}")

            except KeyboardInterrupt:
                print("\n\nInterrupted. Ending session...")
                break
            except Exception as e:
                print(f"Error: {e}")
                logger.exception("Command error")

    finally:
        print("\nDisconnecting...")
        await client.disconnect()
        print("✓ Disconnected")


async def main():
    """Main entry point for recording script."""
    parser = argparse.ArgumentParser(description="Record Seestar telescope session for testing")
    parser.add_argument("--name", required=True, help="Recording name (e.g., 'goto_success')")
    parser.add_argument("--host", default="192.168.2.47", help="Telescope IP address (default: 192.168.2.47)")
    parser.add_argument("--port", type=int, default=4700, help="Telescope port (default: 4700)")
    parser.add_argument("--description", default="", help="Description of what's being recorded")
    parser.add_argument(
        "--output",
        help="Output path (default: tests/fixtures/recordings/<name>.json)",
    )

    args = parser.parse_args()

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        output_path = f"tests/fixtures/recordings/{args.name}.json"

    print(f"\nRecording session: {args.name}")
    print(f"Description: {args.description or '(none)'}")
    print(f"Telescope: {args.host}:{args.port}")
    print(f"Output: {output_path}\n")

    # Create recorder
    recorder = SeestarSessionRecorder(description=args.description or args.name)

    # Start recording proxy
    async with recorder.intercept_connection(args.host, args.port) as (proxy_host, proxy_port):
        try:
            await interactive_session(recorder, proxy_host, proxy_port)
        except Exception as e:
            logger.exception("Session error")
            print(f"\nSession error: {e}")

    # Save recording
    print(f"\nSaving recording to {output_path}...")
    recorder.save(output_path)

    print("\n" + "=" * 70)
    print("RECORDING COMPLETE")
    print("=" * 70)
    print(f"Saved: {output_path}")
    print(f"Interactions: {len(recorder.interactions)}")
    print(f"Duration: {recorder.metadata.duration_seconds:.1f}s")
    print("\nYou can now use this recording in tests with:")
    print(f"  playback = SeestarPlaybackServer.from_recording('{output_path}')")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
