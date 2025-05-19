# DocFX Unity Docusaurus

A command-line tool that generates DocFX documentation from Unity packages and converts it to Docusaurus format.

## Features

- Generate DocFX documentation from Unity packages
- Convert DocFX YAML to Docusaurus Markdown
- Customizable output directories
- Skip either DocFX generation or Docusaurus conversion
- Verbose mode for debugging

## Installation

### Using Homebrew (macOS & Linux)

You can install Unity DocFX Docusaurus using Homebrew:

```bash
# Add the tap repository
brew tap mgamesdev/unity-docfx-docusaurus

# Install the tool
brew install unity-docfx-docusaurus
```

### Manual Installation

Clone this repository:

```bash
git clone https://github.com/mgamesdev/unity-docfx-docusaurus.git
cd unity-docfx-docusaurus
```

Make the script executable:

```bash
chmod +x docfx-unity-docusaurus.sh
```

Optionally, create a symbolic link to make it available system-wide:

```bash
sudo ln -s "$(pwd)/docfx-unity-docusaurus.sh" /usr/local/bin/unity-docfx-docusaurus
```

### Prerequisites

- [DocFX](https://dotnet.github.io/docfx/)
- [Node.js](https://nodejs.org/)

## Requirements

- .NET SDK (for DocFX)
- Python 3 (for Docusaurus conversion)
- DocFX (will be installed automatically if not present)

## Usage

```bash
# Basic usage - generates both DocFX and Docusaurus documentation
docfx-unity-docusaurus

# Show help
docfx-unity-docusaurus --help

# Generate documentation and output Docusaurus files to a specific directory
docfx-unity-docusaurus --output-dir docs/api

# Only convert existing DocFX YAML to Docusaurus (skips DocFX generation)
docfx-unity-docusaurus --skip-docfx --output-dir custom-output

# Only generate DocFX documentation (skips Docusaurus conversion)
docfx-unity-docusaurus --skip-docusaurus

# Enable verbose output for debugging
docfx-unity-docusaurus --verbose
```

## Command-Line Options

```
Options:
  -h, --help                Show this help message
  -o, --output-dir DIR      Set Docusaurus output directory (default: docusaurus)
  -d, --docfx-dir DIR       Set DocFX output directory (default: _site)
  -u, --site-url URL        Set site URL (default: http://localhost:8080)
  -s, --skip-docfx          Skip DocFX generation, only run Docusaurus conversion
  -c, --skip-docusaurus     Skip Docusaurus conversion, only run DocFX generation
  -g, --github-owner NAME   Set GitHub repository owner (default: git user.name)
  -p, --python-script PATH  Path to docfx_markdown_gen_log.py (default: current directory)
  -v, --verbose             Enable verbose output
```

## How It Works

1. **DocFX Generation**: The tool first generates DocFX documentation from your Unity package's C# files.
2. **Docusaurus Conversion**: It then converts the DocFX YAML files to Docusaurus Markdown format.

## Output

- DocFX documentation is generated in the `_site` directory (or custom directory specified with `--docfx-dir`)
- Docusaurus documentation is generated in the `docusaurus` directory (or custom directory specified with `--output-dir`)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

