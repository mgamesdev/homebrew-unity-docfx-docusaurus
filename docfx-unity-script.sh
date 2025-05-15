#!/bin/bash
# DocFX Unity package documentation generator
# This script is for generating DocFX documentation for Unity packages locally.

set -e

# Define variables
PACKAGE_NAME=$(basename "$(pwd)")
GITHUB_REPOSITORY_OWNER=$(git config user.name)
SITE_URL="http://localhost:8080" # Default URL for local preview

# Check for required tools
if ! command -v dotnet &> /dev/null; then
    echo "Error: dotnet is not installed. Please install .NET SDK first."
    exit 1
fi

if ! dotnet tool list -g | grep docfx &> /dev/null; then
    echo "Installing DocFX..."
    dotnet tool update -g docfx
fi

# Step 1: Move everything inside the manual/ folder
echo "Setting up documentation structure..."
if [ -d Documentation~ ] && [ "$(ls -A Documentation~)" ]; then
    mv -v Documentation~/ manual/
    mkdir -p Documentation~
    mv -v manual/ Documentation~/manual/
else
    mkdir -p Documentation~/manual
fi

# Step A: Generate index page
echo "Generating index page..."
echo 'This page redirects to the [manual](manual/).' > Documentation~/index.md

# Step B: Generate main Table of Contents
echo "Generating main Table of Contents..."
echo '- name: Manual
  href: manual/
  homepage: manual/index.md
- name: Scripting API
  href: api/
  homepage: api/index.md' > Documentation~/toc.yml

# Step C: Generate manual Table of Contents
echo "Generating manual Table of Contents..."
if [ -f Documentation~/manual/TableOfContents.md ]; then
    mv Documentation~/manual/TableOfContents.md Documentation~/manual/toc.md
fi
if [ -f Documentation~/manual/toc.md ]; then
    sed -i -e 's/*/#/g' Documentation~/manual/toc.md
    sed -i -e 's/     /#/g' Documentation~/manual/toc.md
fi

# Step D: Generate manual index page
echo "Generating manual index page..."
if [ ! -f Documentation~/manual/index.md ] && [ -f README.md ]; then
    cp README.md Documentation~/manual/index.md
fi

# Step E: Generate api index page
echo "Generating API index page..."
mkdir -p Documentation~/api
if [ -f Documentation~/api_index.md ]; then
    cp Documentation~/api_index.md Documentation~/api/index.md
    rm Documentation~/api_index.md
else
    echo 'This is the documentation for the Scripting APIs of this package.' > Documentation~/api/index.md
fi

# Step F: Generate changelog page
echo "Generating changelog page..."
if [ -f CHANGELOG.md ]; then
    mkdir -p Documentation~/changelog
    cp CHANGELOG.md Documentation~/changelog/CHANGELOG.md
    echo '# [Changes](CHANGELOG.md)' > Documentation~/changelog/toc.md
    echo '- name: Changelog' >> Documentation~/toc.yml
    echo '  href: changelog/' >> Documentation~/toc.yml
    echo '  homepage: changelog/CHANGELOG.md' >> Documentation~/toc.yml
fi

# Step G: Generate license page
echo "Generating license page..."
if [ -f LICENSE ] && [ ! -f LICENSE.md ]; then
    mv -v LICENSE LICENSE.md
fi
if [ -f LICENSE.md ]; then
    mkdir -p Documentation~/license
    cp LICENSE.md Documentation~/license/LICENSE.md
    echo '# [License](LICENSE.md)' > Documentation~/license/toc.md
    if [ -f 'Third Party Notices.md' ]; then
        cp 'Third Party Notices.md' 'Documentation~/license/Third Party Notices.md'
        sed -i '1i# [Third Party Notices](Third Party Notices.md)' Documentation~/license/toc.md
    fi
    echo '- name: License' >> Documentation~/toc.yml
    echo '  href: license/' >> Documentation~/toc.yml
    echo '  homepage: license/LICENSE.md' >> Documentation~/toc.yml
fi

# Step H: Read package.json
echo "Reading package.json..."
if [ -f package.json ]; then
    PACKAGE_CONTENT=$(cat package.json)
else
    PACKAGE_CONTENT='{}'
fi

# Extract display name and version from package.json
DISPLAY_NAME=$(echo "$PACKAGE_CONTENT" | grep -o '"displayName"[^,]*' | cut -d'"' -f4)
if [ -z "$DISPLAY_NAME" ]; then
    DISPLAY_NAME="$PACKAGE_NAME"
fi

VERSION=$(echo "$PACKAGE_CONTENT" | grep -o '"version"[^,]*' | cut -d'"' -f4)
if [ -z "$VERSION" ]; then
    VERSION="1.0.0"
fi

# Clean the values to remove any potential newlines and escape special characters
DISPLAY_NAME=$(printf '%s' "$DISPLAY_NAME" | tr -d '\n' | sed 's/"/\\"/g')
VERSION=$(printf '%s' "$VERSION" | tr -d '\n' | sed 's/"/\\"/g')
GITHUB_REPOSITORY_OWNER=$(printf '%s' "$GITHUB_REPOSITORY_OWNER" | tr -d '\n' | sed 's/"/\\"/g')

# Step I: Generate docfx.json
echo "Generating docfx.json..."
cat > Documentation~/docfx.json << EOF
{
    "metadata": [{
        "src": [{"src": "..", "files": ["**/*.cs"]}],
        "dest": "api",
        "globalNamespaceId": "Global",
        "allowCompilationErrors": true
    }],
    "build": {
        "globalMetadata": {
            "_appTitle": "${DISPLAY_NAME} | ${VERSION}",
            "_appFooter": "<span>Made by <a href=\\"https://github.com/${GITHUB_REPOSITORY_OWNER}\\" target=\\"_blank\\">${GITHUB_REPOSITORY_OWNER}</a> using <a href=\\"https://dotnet.github.io/docfx\\" target=\\"_blank\\">DocFX</a></span>",
            "_enableSearch": true,
            "_enableNewTab": false,
            "_disableNewTab": true,
            "_disableContribution": true,
            "_disableNextArticle": true
        },
        "fileMetadata": {
            "_disableContribution": {"manual/**/*.md": false}
        },
        "globalMetadataFiles": [
        ],
        "content": [
            {"files": ["index.md", "toc.yml"]},
            {"src": "license", "files": ["*.md"], "dest": "license"},
            {"src": "changelog", "files": ["*.md"], "dest": "changelog"},
            {"src": "api", "files": ["*.yml", "index.md"], "dest": "api"},
            {"src": "manual", "files": ["**/*.md"], "dest": "manual"}
        ],
        "resource": [{"files": ["manual/images/*"]}],
        "template": ["default", "modern"],
        "sitemap": {"baseUrl": "${SITE_URL}"},
        "xref": ["${SITE_URL}"],
        "xrefService": ["https://xref.docs.microsoft.com/query?uid={uid}"],
        "dest": "../_site"
    }
}
EOF

# Step J: Set Global Metadata Files if exists
echo "Setting Global Metadata Files if they exist..."
if [ -f Documentation~/manual/config.json ] && [ -f Documentation~/manual/projectMetadata.json ]; then
    sed -i '22i\            "manual/config.json"' Documentation~/docfx.json
    sed -i '22i\            "manual/projectMetadata.json",' Documentation~/docfx.json
elif [ -f Documentation~/manual/config.json ]; then
    sed -i '22i\            "manual/config.json"' Documentation~/docfx.json
elif [ -f Documentation~/manual/projectMetadata.json ]; then
    sed -i '22i\            "manual/projectMetadata.json"' Documentation~/docfx.json
fi

# Step K: Disable toc if not exists
echo "Configuring TOC settings..."
if [ ! -f Documentation~/manual/toc.md ]; then
    # Create a temporary file for the modified content
    temp_file=$(mktemp)
    # Read the file and insert the new lines at line 19
    awk 'NR==19{print "            \"_disableToc\": {\"manual/**/*.md\": false},"; print "            \"_layout\": {\"manual/**/*.md\": \"landing\"},"}1' Documentation~/docfx.json > "$temp_file"
    # Replace the original file with the modified content
    mv "$temp_file" Documentation~/docfx.json
fi

# Step L: Set favicon if exists
echo "Setting favicon if it exists..."
faviconPattern="Documentation~/manual/images/favicon.*"
if compgen -G $faviconPattern > /dev/null; then
    favicons=($faviconPattern)
    faviconPath=${favicons[0]}
    relativeFaviconPath=${faviconPath:15}
    sed -i '12i\            "_appFaviconPath": "'${relativeFaviconPath}'",' Documentation~/docfx.json
fi

# Step M: Set logo if exists
echo "Setting logo if it exists..."
logoPattern="Documentation~/manual/images/logo.*"
if compgen -G $logoPattern > /dev/null; then
    logos=($logoPattern)
    logoPath=${logos[0]}
    relativeLogoPath=${logoPath:15}
    sed -i '12i\            "_appLogoPath": "'${relativeLogoPath}'",' Documentation~/docfx.json
fi

# Step N: Set filter if exists
echo "Setting filter if it exists..."
if [ -f Documentation~/manual/filter.yml ]; then
    sed -i '5i\        "filter": "manual/filter.yml",' Documentation~/docfx.json
elif [ -f Documentation~/manual/filter.yaml ]; then
    sed -i '5i\        "filter": "manual/filter.yaml",' Documentation~/docfx.json
fi

# Step O: Build docfx site
echo "Building DocFX site..."
docfx Documentation~/docfx.json

# Step P: Generate redirect
echo "Generating redirect..."
# Create a temporary file for the modified content
temp_file=$(mktemp)
# Read the file and insert the meta tag before </head>
awk '/<\/head>/ {print "      <meta http-equiv=\"refresh\" content=\"0;URL='"$SITE_URL"'/manual/\">"}1' _site/index.html > "$temp_file"
# Replace the original file with the modified content
mv "$temp_file" _site/index.html

# Step Q: Create config.yaml file in order to log.py script works 
# outputPath: ./docusaroaus
# yamlPath: ./Documentation~/api
echo "Creating config.yaml file..."
cat > config.yaml << EOF
outputPath: ./docusaroaus
yamlPath: ./Documentation~/api
EOF

echo "DocFX documentation generation complete!"
echo "Your documentation is available in the _site directory."
echo ""
echo "To preview locally:"
echo "  cd _site"
echo "  python -m http.server 8080"
echo "  Open http://localhost:8080 in your browser"
echo ""
echo "Or use DocFX's built-in server:"
echo "  docfx serve _site"
