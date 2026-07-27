param(
    [Parameter(Mandatory = $true)]
    [string]$PostgresPassword
)

$psql = "C:\Program Files\PostgreSQL\16\bin\psql.exe"
$env:PGPASSWORD = $PostgresPassword

Write-Host "Creating database and user..."
& $psql -U postgres -h localhost -p 5432 -d postgres -f "$PSScriptRoot\setup_db_part1.sql"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Granting schema privileges..."
& $psql -U postgres -h localhost -p 5432 -d study_space_finder -f "$PSScriptRoot\setup_db_part2.sql"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Done. Database study_space_finder is ready."
