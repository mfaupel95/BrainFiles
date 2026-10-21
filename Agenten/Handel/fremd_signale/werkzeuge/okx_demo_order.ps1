param([string]$Phase = 'liste', [string]$Sl = '')
$d = 'C:\Users\faupe\Documents\BrainFiles\Agenten\MCP-Server\okx-agentkit'
$init = @(
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"0"}}}',
 '{"jsonrpc":"2.0","method":"notifications/initialized"}'
)
function Rufe($zeilen, $id) {
  $o = ($init + $zeilen) | & "$d\start-demo.cmd" 2>&1
  $j = $o | Where-Object { "$_" -match ('"id":' + $id + '[,}]') } | Select-Object -First 1
  if (-not $j) { return $null }
  return ($j | ConvertFrom-Json)
}
function Aufruf($name, $args_, $id) {
  $req = @{ jsonrpc = '2.0'; id = $id; method = 'tools/call'; params = @{ name = $name; arguments = $args_ } } | ConvertTo-Json -Depth 8 -Compress
  $r = Rufe @($req) $id
  if (-not $r) { return 'keine Antwort' }
  if ($r.error) { return ('Fehler: ' + ($r.error | ConvertTo-Json -Compress)) }
  return (($r.result.content | ForEach-Object { $_.text }) -join '')
}
if ($Phase -eq 'liste') {
  $r = Rufe @('{"jsonrpc":"2.0","id":2,"method":"tools/list"}') 2
  $t = $r.result.tools | Where-Object { $_.name -match 'swap' }
  $t | ForEach-Object { $_.name }
  ''
  ($r.result.tools | Where-Object { $_.name -eq 'swap_place_order' } | ConvertTo-Json -Depth 8 -Compress).Substring(0, 900)
}
if ($Phase -eq 'kurs') {
  $t = Aufruf 'market_get_ticker' @{ instId = 'BTC-USDT-SWAP' } 3
  $t.Substring(0, [Math]::Min(500, $t.Length))
}
if ($Phase -eq 'kaufen') {
  $t = Aufruf 'swap_place_order' @{ instId = 'BTC-USDT-SWAP'; tdMode = 'cross'; side = 'buy'; ordType = 'market'; sz = '1'; posSide = 'net'; slTriggerPx = $Sl; slOrdPx = '-1' } 4
  $t.Substring(0, [Math]::Min(900, $t.Length))
}
if ($Phase -eq 'schliessen') {
  $t = Aufruf 'swap_place_order' @{ instId = 'BTC-USDT-SWAP'; tdMode = 'cross'; side = 'sell'; ordType = 'market'; sz = '1'; posSide = 'net'; reduceOnly = $true } 5
  $t.Substring(0, [Math]::Min(900, $t.Length))
}
if ($Phase -eq 'positionen') {
  $t = Aufruf 'swap_get_positions' @{ instType = 'SWAP' } 6
  $t.Substring(0, [Math]::Min(1500, $t.Length))
}
