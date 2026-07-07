param(
    [switch]$Interactive,
    [switch]$UseToday
)

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $repoRoot "scripts\update_trip.py"

$args = @($scriptPath)
if ($Interactive) {
    $args += "--interactive"
}
if ($UseToday) {
    $args += "--use-today"
}

python @args
