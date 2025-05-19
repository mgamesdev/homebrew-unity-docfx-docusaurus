class UnityDocfxDocusaurus < Formula
  desc 'Generate Docusaurus documentation from Unity XML docs using DocFX'
  homepage 'https://github.com/mgamesdev/unity-docfx-docusaurus'
  url 'RELEASE_URL_PLACEHOLDER'
  sha256 'SHA256_PLACEHOLDER'
  license 'MIT'

  depends_on 'docfx'
  depends_on 'node'

  def install
    bin.install 'docfx-unity-docusaurus.sh' => 'unity-docfx-docusaurus'
  end

  test do
    system "#{bin}/unity-docfx-docusaurus", '--version'
  end
end
