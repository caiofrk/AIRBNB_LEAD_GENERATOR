#!/bin/bash
# Clone Flutter stable branch
echo "Downloading Flutter..."
git clone https://github.com/flutter/flutter.git -b stable --depth 1

# Export flutter to path
export PATH="$PATH:`pwd`/flutter/bin"

# Fetch dependencies
echo "Getting packages..."
flutter pub get

# Build max optimized release version
echo "Compiling for Web..."
flutter build web --release
