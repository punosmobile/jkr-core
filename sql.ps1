param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$SqlQuery,
    
    [string]$DBHost = "localhost",
    [string]$User = "jkr_admin",
    [int]$Port = 5435,
    [string]$Database = "jatehuolto",
    [string]$Password = "qwerty"
)

# Aseta ympäristömuuttujat
$env:PGPASSWORD = $Password
$env:PAGER = ""

# Aja SQL-kysely
psql -h $DBHost -U $User -p $Port -d $Database -c $SqlQuery

# Tyhjennä salasana ympäristömuuttujista turvallisuussyistä
$env:PGPASSWORD = $null