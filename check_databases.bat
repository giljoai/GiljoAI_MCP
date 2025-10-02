@echo off
set PGPASSWORD=4010
echo Checking for giljo databases...
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -t -c "SELECT datname FROM pg_database WHERE datname LIKE 'giljo%%';"
echo.
echo Done checking databases.