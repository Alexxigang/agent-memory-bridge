param(
    [string]$OutputDir = "dist/demo-release",
    [string]$ZipPath = "dist/demo-release.zip"
)

$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "src"

python -m memory_migrate_plugin.cli release `
  --input ./fixtures/cline-memory-bank `
  --to agents-md `
  --profile agent-rules `
  --output-dir $OutputDir `
  --zip $ZipPath

python -m memory_migrate_plugin.cli verify --manifest (Join-Path $OutputDir 'manifest.json')
Write-Output "Demo release created at $OutputDir"
