param([Parameter(Mandatory=$true)][string]$Source)
# Independent source oracle: .NET ZIP + XML DOM/XPath. Does not import JS reader.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [IO.Compression.ZipFile]::OpenRead($Source)
try {
    $reader = New-Object IO.StreamReader($zip.GetEntry('word/document.xml').Open())
    try { $xmlText = $reader.ReadToEnd() } finally { $reader.Dispose() }
} finally { $zip.Dispose() }
$xml = New-Object Xml.XmlDocument
$xml.PreserveWhitespace = $true
$xml.XmlResolver = $null
$xml.LoadXml($xmlText)
$script:ns = New-Object Xml.XmlNamespaceManager($xml.NameTable)
$script:ns.AddNamespace('w', 'http://schemas.openxmlformats.org/wordprocessingml/2006/main')

function Get-Path($node) {
    $parts = New-Object 'System.Collections.Generic.List[string]'
    while ($node -is [Xml.XmlElement]) {
        $number = 1
        $previous = $node.PreviousSibling
        while ($null -ne $previous) {
            if ($previous -is [Xml.XmlElement] -and $previous.Name -ceq $node.Name) { $number++ }
            $previous = $previous.PreviousSibling
        }
        $parts.Insert(0, ($node.Name + '[' + $number + ']'))
        $node = $node.ParentNode
    }
    return '/' + ($parts -join '/')
}
function Get-Text($paragraph) {
    $result = New-Object Text.StringBuilder
    foreach ($node in $paragraph.SelectNodes('.//w:t|.//w:tab|.//w:br|.//w:cr', $script:ns)) {
        switch ($node.LocalName) {
            't' { [void]$result.Append($node.InnerText) }
            'tab' { [void]$result.Append("`t") }
            default { [void]$result.Append("`n") }
        }
    }
    return $result.ToString()
}
function Get-Record($p) { return @{ id = (Get-Path $p); text = (Get-Text $p) } }
function Get-Descriptor($cell, [string]$level) {
    $excluded = @{}
    foreach ($row in $cell.SelectNodes('.//w:tbl/w:tr', $script:ns)) {
        $cols = $row.SelectNodes('./w:tc', $script:ns)
        if ($cols.Count -eq 2) {
            $left = $cols[0].SelectNodes('.//w:p', $script:ns)
            $label = ($left | ForEach-Object { Get-Text $_ }) -join ''
            if ($label -cne $level) { throw "Unknown nested level $label / $level" }
            foreach ($p in $left) { $excluded[(Get-Path $p)] = $true }
        } elseif ($cols.Count -ne 1) { throw 'Unknown nested table shape' }
    }
    $records = @($cell.SelectNodes('.//w:p', $script:ns) | ForEach-Object {
        $record = Get-Record $_
        if ($record.text.Trim() -cne '' -and -not $excluded.ContainsKey($record.id)) { $record }
    })
    return @{ text = (($records | ForEach-Object { $_.text }) -join "`n"); records = $records }
}

$body = $xml.SelectSingleNode('/w:document/w:body', $script:ns)
$families = New-Object 'System.Collections.Generic.List[object]'
$family = $null
$indicator = $null
foreach ($node in $body.ChildNodes) {
    if (-not ($node -is [Xml.XmlElement])) { continue }
    if ($node.LocalName -eq 'p') {
        $text = Get-Text $node
        if ($text -cmatch '^(CR-[0-9]{2}) \u00b7 (.+)$') {
            $family = @{ code = $Matches[1]; title = $Matches[2]; heading = (Get-Record $node); declaration = $null;
                indicators = (New-Object 'System.Collections.Generic.List[object]') }
            $families.Add($family); $indicator = $null
        } elseif ($text -cmatch '^(CR-[A-Z]+[0-9]+) \u00b7 (.+)$') {
            $indicator = @{ code = $Matches[1]; question = $Matches[2]; family_code = $family.code;
                heading = (Get-Record $node); gate = $null; levels = @{}; safety = (New-Object 'System.Collections.Generic.List[object]') }
            $family.indicators.Add($indicator)
        } elseif ($text.StartsWith('Indicadores:')) { $family.declaration = Get-Record $node }
        elseif ($text.StartsWith('Control de seguridad:')) { $indicator.safety.Add((Get-Record $node)) }
    } elseif ($node.LocalName -eq 'tbl') {
        if ($null -eq $indicator) { throw 'Table without indicator' }
        foreach ($row in $node.SelectNodes('./w:tr', $script:ns)) {
            $cells = $row.SelectNodes('./w:tc', $script:ns)
            if ($cells.Count -ne 2) { throw 'Invalid outer row' }
            $label = ($cells[0].SelectNodes('.//w:p', $script:ns) | ForEach-Object { Get-Text $_ }) -join ''
            $value = Get-Descriptor $cells[1] $label
            if ($label -ceq 'Aplicabilidad / N/A') { $indicator.gate = $value }
            elseif ($label -cmatch '^[0-3]$') { $indicator.levels[$label] = $value }
            else { throw "Unexpected label $label" }
        }
    }
}
$all = @($body.SelectNodes('.//w:p', $script:ns) | ForEach-Object { Get-Record $_ })
$object = @{
    oracle = 'independent-dotnet-xml-dom/1';
    source_sha256 = (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash.ToLowerInvariant();
    paragraph_count = $all.Count; table_count = $body.SelectNodes('.//w:tbl', $script:ns).Count;
    paragraphs = $all; families = @($families.ToArray())
}
ConvertTo-Json -InputObject $object -Depth 40 -Compress
