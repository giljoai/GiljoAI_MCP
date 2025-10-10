@echo off
REM Fix PostgreSQL user authentication for giljo_user
REM Password: 4010

echo ===============================================
echo   PostgreSQL User Fix Script
echo ===============================================
echo.
echo This script will:
echo 1. Check if giljo_user exists
echo 2. Recreate the user with correct password
echo 3. Grant necessary permissions
echo.
echo PostgreSQL Password: 4010
echo.
pause

echo.
echo Dropping existing user if present...
psql -U postgres -c "DROP USER IF EXISTS giljo_user;"

echo.
echo Creating giljo_user with password '4010'...
psql -U postgres -c "CREATE USER giljo_user WITH PASSWORD '4010';"

echo.
echo Granting privileges to giljo_user...
psql -U postgres -c "ALTER USER giljo_user CREATEDB;"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE giljo_mcp TO giljo_user;"

echo.
echo Verifying user creation...
psql -U postgres -c "\du giljo_user"

echo.
echo ===============================================
echo   User setup complete!
echo ===============================================
echo.
echo Now try starting the backend again.
echo.
pause
