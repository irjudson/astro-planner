#!/bin/bash
# Extract Seestar S50 RSA private key from official APK
# This key is required for authentication with firmware 6.45+

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SECRETS_DIR="$BACKEND_DIR/secrets"
KEY_FILE="$SECRETS_DIR/seestar_private_key.pem"

echo "==================================================="
echo "Seestar S50 RSA Private Key Extraction"
echo "==================================================="
echo ""
echo "This script extracts the RSA private key from the"
echo "official Seestar S50 Android app. This key is"
echo "embedded in the app and used for authentication"
echo "with firmware version 6.45+."
echo ""

# Check if key already exists
if [ -f "$KEY_FILE" ]; then
    echo "✓ Private key already exists at:"
    echo "  $KEY_FILE"
    echo ""
    read -p "Overwrite existing key? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing key. Exiting."
        exit 0
    fi
fi

# Create secrets directory
mkdir -p "$SECRETS_DIR"

echo ""
echo "==================================================="
echo "OPTION 1: Automatic Extraction (Requires APK)"
echo "==================================================="
echo ""
echo "To extract automatically, you need the Seestar APK:"
echo ""
echo "1. Download from: https://i.seestar.com (Official)"
echo "   - Look for 'Seestar_vX.X.X.apk'"
echo ""
echo "2. Place APK in /tmp/ directory"
echo ""
read -p "Do you have the APK ready? (y/N) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Find APK
    APK_FILE=$(find /tmp -name "Seestar*.apk" -o -name "seestar*.apk" | head -1)

    if [ -z "$APK_FILE" ]; then
        echo "✗ APK not found in /tmp/"
        echo "  Please place the Seestar APK in /tmp/ and try again."
        exit 1
    fi

    echo "✓ Found APK: $APK_FILE"

    # Create temp directory
    TEMP_DIR=$(mktemp -d)
    trap "rm -rf $TEMP_DIR" EXIT

    echo "Extracting APK..."
    unzip -q "$APK_FILE" -d "$TEMP_DIR"

    echo "Searching for private key in native libraries..."

    # The key is embedded in the native library libseestar.so or similar
    # We search for the PEM header
    NATIVE_LIBS="$TEMP_DIR/lib"

    if [ ! -d "$NATIVE_LIBS" ]; then
        echo "✗ No native libraries found in APK"
        echo "  APK structure may have changed."
        exit 1
    fi

    # Search for the private key in all .so files
    KEY_FOUND=false
    for SO_FILE in $(find "$NATIVE_LIBS" -name "*.so"); do
        if strings "$SO_FILE" | grep -q "BEGIN PRIVATE KEY"; then
            echo "✓ Found key in: $(basename $SO_FILE)"

            # Extract the complete PEM block
            strings "$SO_FILE" | awk '/BEGIN PRIVATE KEY/,/END PRIVATE KEY/' > "$KEY_FILE"

            if [ -s "$KEY_FILE" ]; then
                KEY_FOUND=true
                break
            fi
        fi
    done

    if [ "$KEY_FOUND" = true ]; then
        echo "✓ Successfully extracted private key to:"
        echo "  $KEY_FILE"
        echo ""
        echo "✓ Key file permissions set to 600 (owner read/write only)"
        chmod 600 "$KEY_FILE"
        exit 0
    else
        echo "✗ Could not extract key from APK"
        echo "  The APK structure may have changed."
        echo "  Please use Option 2 below or contact the maintainer."
    fi
else
    echo ""
    echo "Skipping automatic extraction."
fi

echo ""
echo "==================================================="
echo "OPTION 2: Manual Key Provision"
echo "==================================================="
echo ""
echo "If you have the private key already, paste it now."
echo "The key should be in PEM format:"
echo ""
echo "-----BEGIN PRIVATE KEY-----"
echo "MIICd..."
echo "-----END PRIVATE KEY-----"
echo ""
echo "Or press Ctrl+C to exit and contact the maintainer:"
echo "  https://github.com/irjudson/astro-planner/issues"
echo ""
read -p "Paste key now? (y/N) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Paste the complete PEM key (including BEGIN/END lines)."
    echo "Press Ctrl+D when done:"
    echo ""

    cat > "$KEY_FILE"

    if [ -s "$KEY_FILE" ] && grep -q "BEGIN PRIVATE KEY" "$KEY_FILE"; then
        echo ""
        echo "✓ Private key saved to:"
        echo "  $KEY_FILE"
        chmod 600 "$KEY_FILE"
        echo "✓ Key file permissions set to 600"
    else
        echo "✗ Invalid key format. Please try again."
        rm -f "$KEY_FILE"
        exit 1
    fi
else
    echo ""
    echo "No key installed. The Seestar client will not work"
    echo "until you provide a valid private key."
    echo ""
    echo "Please open an issue for assistance:"
    echo "  https://github.com/irjudson/astro-planner/issues"
    exit 1
fi
