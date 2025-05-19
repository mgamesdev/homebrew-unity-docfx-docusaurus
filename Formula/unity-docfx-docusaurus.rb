class UnityDocfxDocusaurus < Formula
  desc 'Generate Docusaurus documentation from Unity XML docs using DocFX'
  homepage 'https://github.com/mgamesdev/unity-docfx-docusaurus'
  url 'https://github.com/mgamesdev/unity-docfx-docusaurus/archive/refs/tags/v1.0.5.tar.gz'
  sha256 '6edb6b004e3ab3e6085730f22d6a4c68dde6adfd1e8b870d047ec6b6c2e2001b'
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
