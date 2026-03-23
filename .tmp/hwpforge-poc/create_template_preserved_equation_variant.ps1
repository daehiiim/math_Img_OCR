param(
    [string]$SourcePath = "D:\03_PROJECT\05_mathOCR\templates\generated-canonical-sample.hwpx",
    [string]$OutputPath = "D:\03_PROJECT\05_mathOCR\templates\template-preserved-equation-variant.hwpx"
)

Add-Type -AssemblyName System.IO.Compression.FileSystem

$TempDir = "D:\03_PROJECT\05_mathOCR\.tmp\hwpforge-poc\direct-equation-variant"
$SectionRelativePath = "Contents\section0.xml"

function Get-Replacements {
    return [ordered]@{
        "△ABC에서 AB 위의 점 E와 AC 위의 점 D에 대하여 ∠ABC = ∠ADE이고, AB = 14cm, AE = 6cm, AD = 8cm, DC = x(cm)일 때, x의 값은? [4점]" = "△PQR에서 PQ 위의 점 S와 PR 위의 점 T에 대하여 ∠PQR = ∠STR이고, PQ = 18cm, PS = 8cm, PT = 10cm, TR = y(cm)일 때, y의 값은? [4점]"
        "주어진 조건에서 E는 AB 위, D는 AC 위에 있으므로" = "주어진 조건에서 S는 PQ 위, T는 PR 위에 있으므로"
        "<hp:script>1</hp:script>" = "<hp:script>2</hp:script>"
        "<hp:script>3/2</hp:script>" = "<hp:script>5 over 3</hp:script>"
        "<hp:script>9/4</hp:script>" = "<hp:script>11 over 4</hp:script>"
        "<hp:script>7/3</hp:script>" = "<hp:script>8 over 3</hp:script>"
        "<hp:script>5/2</hp:script>" = "<hp:script>7 over 2</hp:script>"
        "<hp:script>ANGLE BAC= ANGLE DAE</hp:script>" = "<hp:script>ANGLE QPR= ANGLE SRT</hp:script>"
        "<hp:script>ANGLE ABC= ANGLE ADE</hp:script>" = "<hp:script>ANGLE PQR= ANGLE STR</hp:script>"
        "<hp:script>ABC</hp:script>" = "<hp:script>PQR</hp:script>"
        "<hp:script>ADE</hp:script>" = "<hp:script>SRT</hp:script>"
    }
}

function Reset-TempDirectory {
    param([string]$Path)

    if (Test-Path $Path) {
        Remove-Item $Path -Recurse -Force
    }
    New-Item -ItemType Directory -Force $Path | Out-Null
}

function Update-SectionXml {
    param(
        [string]$SectionPath,
        [hashtable]$Replacements
    )

    $text = Get-Content -Raw $SectionPath
    foreach ($old in $Replacements.Keys) {
        $text = $text.Replace($old, $Replacements[$old])
    }

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($SectionPath, $text, $utf8NoBom)
}

Reset-TempDirectory -Path $TempDir
Copy-Item -Force $SourcePath $OutputPath
[System.IO.Compression.ZipFile]::ExtractToDirectory($OutputPath, $TempDir)
Update-SectionXml -SectionPath (Join-Path $TempDir $SectionRelativePath) -Replacements (Get-Replacements)
Remove-Item $OutputPath -Force
[System.IO.Compression.ZipFile]::CreateFromDirectory($TempDir, $OutputPath)
