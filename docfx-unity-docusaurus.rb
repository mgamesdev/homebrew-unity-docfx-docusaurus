class DocfxUnityDocusaurus < Formula
  desc 'Generate DocFX documentation from Unity packages and convert to Docusaurus format'
  homepage 'https://github.com/yourusername/docfx-unity-docusaurus'
  url 'https://github.com/yourusername/docfx-unity-docusaurus/archive/refs/tags/v1.0.0.tar.gz'
  sha256 'YOUR_SHA256_HASH' # Replace with actual SHA256 hash after creating the release
  license 'MIT'

  depends_on 'dotnet'
  depends_on 'python@3'

  def install
    # Install the main script
    bin.install 'docfx-unity-docusaurus.sh' => 'docfx-unity-docusaurus'

    # Install the Python conversion script
    libexec.install 'docfx_markdown_gen_log.py'

    # Create a wrapper script that knows where to find the Python script
    (bin / 'docfx-unity-docusaurus').write <<~EOS
      #!/bin/bash
      # Wrapper script to ensure the Python script is found

      # Get the directory where this script is located
      SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

      # Set the path to the Python script
      PYTHON_SCRIPT="${SCRIPT_DIR}/../libexec/docfx_markdown_gen_log.py"

      # Run the main script with the Python script path
      "${SCRIPT_DIR}/docfx-unity-docusaurus" --python-script "$PYTHON_SCRIPT" "$@"
    EOS

    # Make the wrapper script executable
    chmod 0o755, bin / 'docfx-unity-docusaurus'
  end

  test do
    # Simple test to verify the script is installed and executable
    system "#{bin}/docfx-unity-docusaurus", '--help'
  end
end
