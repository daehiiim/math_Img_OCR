param(
    [string]$WorkSubdir = "one-question"
)

Add-Type -AssemblyName System.IO.Compression.FileSystem

$Root = "D:\03_PROJECT\05_mathOCR"
$WorkDir = Join-Path $Root (".tmp\hwpforge-poc\" + $WorkSubdir)
$BaselinePath = Join-Path $WorkDir "baseline.hwpx"
$PatchedPath = Join-Path $WorkDir "patched.hwpx"
$OriginalJsonPath = Join-Path $WorkDir "section0.original.json"
$PatchedJsonPath = Join-Path $WorkDir "section0.patched.json"
$RunSummaryPath = Join-Path $WorkDir "run-summary.json"
$VerificationPath = Join-Path $WorkDir "verification-report.json"

function Get-JsonFile {
    param([string]$Path)

    return Get-Content -Raw $Path | ConvertFrom-Json -Depth 100
}

function Get-BytesHash {
    param([byte[]]$Bytes)

    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([System.BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $sha.Dispose()
    }
}

function Get-ArchiveEntries {
    param([string]$ZipPath)

    $zip = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        $map = @{}
        foreach ($entry in $zip.Entries) {
            $stream = $entry.Open()
            $memory = New-Object System.IO.MemoryStream
            try {
                $stream.CopyTo($memory)
                $bytes = $memory.ToArray()
            }
            finally {
                $stream.Dispose()
                $memory.Dispose()
            }

            $map[$entry.FullName] = [PSCustomObject]@{
                Name = $entry.FullName
                Size = $bytes.Length
                Hash = Get-BytesHash -Bytes $bytes
                Bytes = $bytes
            }
        }
        return $map
    }
    finally {
        $zip.Dispose()
    }
}

function Get-EntryText {
    param(
        [hashtable]$ArchiveMap,
        [string]$EntryName
    )

    return [System.Text.Encoding]::UTF8.GetString($ArchiveMap[$EntryName].Bytes)
}

function Get-ChangedEntries {
    param(
        [hashtable]$BaselineEntries,
        [hashtable]$PatchedEntries
    )

    $names = @($BaselineEntries.Keys + $PatchedEntries.Keys | Sort-Object -Unique)
    $changed = foreach ($name in $names) {
        $left = $BaselineEntries[$name]
        $right = $PatchedEntries[$name]
        if ($null -eq $left -or $null -eq $right -or $left.Hash -ne $right.Hash) {
            $name
        }
    }
    return @($changed)
}

function Get-SectionMetrics {
    param([string]$XmlText)

    $binaryRefs = [regex]::Matches($XmlText, 'binaryItemIDRef="([^"]+)"') |
        ForEach-Object { $_.Groups[1].Value } |
        Sort-Object -Unique

    return [PSCustomObject]@{
        BinaryRefs = @($binaryRefs)
        BinaryRefCount = @($binaryRefs).Count
        EquationCount = ([regex]::Matches($XmlText, '<hp:equation\b')).Count
        ParaPrCount = ([regex]::Matches($XmlText, 'paraPrIDRef="')).Count
        CharPrCount = ([regex]::Matches($XmlText, 'charPrIDRef="')).Count
        StyleIdCount = ([regex]::Matches($XmlText, 'styleIDRef="')).Count
    }
}

function Get-ScaffoldCheck {
    param(
        [pscustomobject]$OriginalSection,
        [pscustomobject]$PatchedSection
    )

    $originalSlots = @($OriginalSection.preservation.text_slots)
    $patchedSlots = @($PatchedSection.preservation.text_slots)
    $scaffold = $originalSlots | Where-Object { $_.original_text -match '^\s*1[\.\)]?\s*$' } | Select-Object -First 1

    if ($null -eq $scaffold) {
        return [PSCustomObject]@{
            Found = $false
            Preserved = $false
            Path = $null
            OriginalText = $null
            PatchedText = $null
        }
    }

    $patched = $patchedSlots | Where-Object { $_.path -eq $scaffold.path } | Select-Object -First 1
    return [PSCustomObject]@{
        Found = $true
        Preserved = $null -ne $patched -and $patched.original_text -eq $scaffold.original_text
        Path = $scaffold.path
        OriginalText = $scaffold.original_text
        PatchedText = if ($null -ne $patched) { $patched.original_text } else { $null }
    }
}

function Test-RequiredEntriesUnchanged {
    param(
        [hashtable]$BaselineEntries,
        [hashtable]$PatchedEntries,
        [string[]]$EntryNames
    )

    $results = foreach ($entryName in $EntryNames) {
        $same = $BaselineEntries.ContainsKey($entryName) -and
            $PatchedEntries.ContainsKey($entryName) -and
            $BaselineEntries[$entryName].Hash -eq $PatchedEntries[$entryName].Hash

        [PSCustomObject]@{
            Entry = $entryName
            Same = $same
        }
    }
    return @($results)
}

$report = [ordered]@{
    success = $false
}

if (-not (Test-Path $RunSummaryPath)) {
    $report.failure = [ordered]@{
        code = "HWPFORGE_RUNTIME_UNAVAILABLE"
        message = "HwpForge 실행 결과 요약을 찾지 못했습니다."
    }
    $report | ConvertTo-Json -Depth 100 | Set-Content -Path $VerificationPath -Encoding UTF8
    exit 1
}

$runSummary = Get-JsonFile -Path $RunSummaryPath
$report.run_summary = $runSummary

if (-not $runSummary.success) {
    $report.failure = $runSummary.failure
    $report | ConvertTo-Json -Depth 100 | Set-Content -Path $VerificationPath -Encoding UTF8
    exit 1
}

$baselineEntries = Get-ArchiveEntries -ZipPath $BaselinePath
$patchedEntries = Get-ArchiveEntries -ZipPath $PatchedPath
$changedEntries = @(Get-ChangedEntries -BaselineEntries $baselineEntries -PatchedEntries $patchedEntries)
$requiredChecks = Test-RequiredEntriesUnchanged -BaselineEntries $baselineEntries -PatchedEntries $patchedEntries -EntryNames @(
    "Contents/header.xml",
    "Contents/masterpage0.xml",
    "Contents/masterpage1.xml",
    "Contents/content.hpf",
    "settings.xml",
    "version.xml"
)

$baselineSectionXml = Get-EntryText -ArchiveMap $baselineEntries -EntryName "Contents/section0.xml"
$patchedSectionXml = Get-EntryText -ArchiveMap $patchedEntries -EntryName "Contents/section0.xml"
$baselineMetrics = Get-SectionMetrics -XmlText $baselineSectionXml
$patchedMetrics = Get-SectionMetrics -XmlText $patchedSectionXml
$originalSection = Get-JsonFile -Path $OriginalJsonPath
$patchedSection = Get-JsonFile -Path $PatchedJsonPath
$scaffoldCheck = Get-ScaffoldCheck -OriginalSection $originalSection -PatchedSection $patchedSection

$statusE = ($changedEntries.Count -eq 1 -and $changedEntries[0] -eq "Contents/section0.xml")
$statusF = (@($requiredChecks | Where-Object { -not $_.Same }).Count -eq 0)
$statusG = (
    (@($baselineMetrics.BinaryRefs) -join "|") -eq (@($patchedMetrics.BinaryRefs) -join "|") -and
    $baselineMetrics.EquationCount -eq $patchedMetrics.EquationCount -and
    $baselineMetrics.ParaPrCount -eq $patchedMetrics.ParaPrCount -and
    $baselineMetrics.CharPrCount -eq $patchedMetrics.CharPrCount -and
    $baselineMetrics.StyleIdCount -eq $patchedMetrics.StyleIdCount
)

$report.success = $true
$report.statuses = [ordered]@{
    scenarioA_baseline_inspect = $runSummary.statuses.scenarioA_baseline_inspect
    scenarioB_section_export = $runSummary.statuses.scenarioB_section_export
    scenarioC_patch_success = $runSummary.statuses.scenarioC_patch_success
    scenarioD_reparse_success = $runSummary.statuses.scenarioD_reparse_success
    scenarioE_only_section0_changed = $statusE
    scenarioF_required_entries_unchanged = $statusF
    scenarioG_structure_metrics_preserved = $statusG
}
$report.changed_entries = @($changedEntries)
$report.required_entry_checks = @($requiredChecks)
$report.section_metrics = [ordered]@{
    baseline = $baselineMetrics
    patched = $patchedMetrics
}
$report.scaffold_check = $scaffoldCheck
$report.verdict = if (
    $report.statuses.scenarioA_baseline_inspect -and
    $report.statuses.scenarioB_section_export -and
    $report.statuses.scenarioC_patch_success -and
    $report.statuses.scenarioD_reparse_success -and
    $statusE -and
    $statusF -and
    $statusG
) {
    "PASS"
}
else {
    "FAIL"
}
$report.message = if ($report.verdict -eq "PASS") {
    "기존 양식을 유지한 채 HwpForge preserving patch 경로가 이 샘플에서는 성립합니다."
}
else {
    "현재 양식 유지한 채 HwpForge patch 경로를 메인 파이프라인으로 채택 불가"
}

$report | ConvertTo-Json -Depth 100 | Set-Content -Path $VerificationPath -Encoding UTF8

if ($report.verdict -ne "PASS") {
    exit 1
}
