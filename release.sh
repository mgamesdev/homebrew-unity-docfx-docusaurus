#!/bin/bash

# Exit on any error
set -e

# Check if version argument is provided
if [ -z "$1" ]; then
    echo "Usage: ./release.sh <version>"
    echo "Example: ./release.sh 1.0.0"
    exit 1
fi

VERSION=$1
TAG="v$VERSION"
SCRIPT_NAME="docfx-unity-docusaurus.sh"
FORMULA_FILE="Formula/unity-docfx-docusaurus.rb"
TAP_REPO="homebrew-unity-docfx-docusaurus"

# Check if Ruby is installed
if ! command -v ruby &> /dev/null; then
    echo "Ruby is required but not installed. Please install Ruby first."
    exit 1
fi

# Check if the script exists
if [ ! -f "$SCRIPT_NAME" ]; then
    echo "Error: $SCRIPT_NAME not found in current directory"
    exit 1
fi

# Calculate SHA256
echo "Calculating SHA256..."
SHA256=$(shasum -a 256 "$SCRIPT_NAME" | awk '{print $1}')
echo "SHA256: $SHA256"

# Update formula file if it exists
if [ -f "$FORMULA_FILE" ]; then
    echo "Updating formula file..."
    sed -i '' "s/sha256 \".*\"/sha256 \"$SHA256\"/" "$FORMULA_FILE"
    # Note: URL update is skipped as we don't have a release URL yet
    echo "Formula file updated with new SHA256"
else
    echo "Warning: Formula file not found at $FORMULA_FILE"
fi

# Create git tag
echo "Creating git tag $TAG..."
git tag -a "$TAG" -m "Release $TAG"
git push origin "$TAG"

echo "Release process completed!"
echo "Next steps:"
echo "1. Create a release on GitHub manually"
echo "2. Update the formula URL with the release URL"
echo "3. Push the formula to your Homebrew tap repository" 
echo "4. Published the repository to Homebrew"