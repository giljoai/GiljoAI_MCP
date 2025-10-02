@echo off
set PGPASSWORD=$DB_PASSWORD
echo Checking for giljo databases...
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -t -c "SELECT datname FROM pg_database WHERE datname LIKE 'giljo%%';"
echo.
echo Done checking databases.