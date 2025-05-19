class UnityDocfxDocusaurus < Formula
  desc 'Generate DocFX documentation from Unity packages and convert to Docusaurus format'
  homepage 'https://github.com/mgamesdev/unity-docfx-docusaurus'
  url 'https://github.com/mgamesdev/unity-docfx-docusaurus/archive/refs/tags/v1.0.0.tar.gz' # This will be updated by the workflow
  sha256 '7bbac0e84510570ec' # This will be updated by the workflow
  license 'MIT'

  # Add a comment to help maintainers understand the URL format
  # The URL will be updated by the GitHub Actions workflow to match the current release tag
  # Example: v1.0.0 -> https://github.com/mgamesdev/unity-docfx-docusaurus/archive/refs/tags/v1.0.0.tar.gz

  depends_on 'dotnet'
  depends_on 'python@3'

  def install
    # Install the main script
    bin.install 'docfx-unity-docusaurus.sh' => 'docfx-unity-docusaurus'

    # Install the Python conversion script
    libexec.install 'docfx_markdown_gen_log.py'

    # Create a wrapper script that knows where to find the Python script
    (bin / 'unity-docfx-docusaurus').write <<~EOS
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
    chmod 0o755, bin / 'unity-docfx-docusaurus'
  end

  test do
    # Simple test to verify the script is installed and executable
    system "#{bin}/unity-docfx-docusaurus", '--help'
  end
end
