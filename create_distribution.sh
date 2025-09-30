#!/bin/bash

# GiljoAI MCP Distribution Package Creator
# Creates a clean distribution package ready for users

# Default values
OUTPUT_DIR="./dist"
PACKAGE_NAME="giljo-mcp"
INCLUDE_DEV_TOOLS=false

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -o|--output) OUTPUT_DIR="$2"; shift ;;
        -n|--name) PACKAGE_NAME="$2"; shift ;;
        -d|--dev-tools) INCLUDE_DEV_TOOLS=true ;;
        -h|--help)
            echo "Usage: $0 [-o output_dir] [-n package_name] [-d include_dev_tools]"
            exit 0
            ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

echo "================================================"
echo "GiljoAI MCP Distribution Package Creator"
echo "================================================"
echo ""

# Create timestamp for package version
TIMESTAMP=$(date +"%Y%m%d-%H%M")
PACKAGE_DIR="$OUTPUT_DIR/$PACKAGE_NAME-$TIMESTAMP"

echo "[1/6] Creating distribution directory..."
rm -rf "$PACKAGE_DIR" 2>/dev/null
mkdir -p "$PACKAGE_DIR"

echo "[2/6] Copying core application files..."

# Core directories
CORE_DIRS=("src" "api" "frontend" "tests" "scripts" "examples")
for dir in "${CORE_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "  - Copying $dir/"
        cp -r "$dir" "$PACKAGE_DIR/" 2>/dev/null || true
    fi
done

echo "[3/6] Copying configuration files..."

# Essential files
ESSENTIAL_FILES=(
    "config.yaml.example"
    ".env.example"
    "requirements.txt"
    "setup.py"
    "pyproject.toml"
    "INSTALL.md"
    "README.md"
    "install.bat"
    "quickstart.sh"
    "MANIFEST.txt"
)

for file in "${ESSENTIAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  - Copying $file"
        cp "$file" "$PACKAGE_DIR/"
    fi
done

# Optional files
if [ -f "alembic.ini" ]; then
    cp "alembic.ini" "$PACKAGE_DIR/"
fi

if [ "$INCLUDE_DEV_TOOLS" = true ]; then
    echo "[4/6] Including development tools..."
    DEV_FILES=(".ruff.toml" ".eslintrc.json" ".prettierrc" "mypy.ini")
    for file in "${DEV_FILES[@]}"; do
        if [ -f "$file" ]; then
            echo "  - Including $file"
            cp "$file" "$PACKAGE_DIR/"
        fi
    done
else
    echo "[4/6] Skipping development tools (use -d to include)"
fi

echo "[5/6] Cleaning up package..."

# Remove Python cache and other unwanted files
find "$PACKAGE_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find "$PACKAGE_DIR" -type f -name "*.pyc" -delete 2>/dev/null
find "$PACKAGE_DIR" -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null
find "$PACKAGE_DIR" -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null
find "$PACKAGE_DIR" -type d -name ".git" -exec rm -rf {} + 2>/dev/null

# Remove any accidentally included local files
find "$PACKAGE_DIR" -type f -name "*.log" -delete 2>/dev/null
find "$PACKAGE_DIR" -type f -name "*.db" -delete 2>/dev/null
find "$PACKAGE_DIR" -type f -name "*.db-shm" -delete 2>/dev/null
find "$PACKAGE_DIR" -type f -name "*.db-wal" -delete 2>/dev/null
find "$PACKAGE_DIR" -type f -name ".env" -delete 2>/dev/null
find "$PACKAGE_DIR" -type f -name "config.yaml" -delete 2>/dev/null

echo "[6/6] Creating archive..."

# Determine archive format based on available tools
ZIP_PATH="$OUTPUT_DIR/$PACKAGE_NAME-$TIMESTAMP"

if command -v zip &> /dev/null; then
    # Create ZIP file
    cd "$OUTPUT_DIR"
    zip -r "$PACKAGE_NAME-$TIMESTAMP.zip" "$(basename "$PACKAGE_DIR")" -q
    cd - > /dev/null
    ZIP_PATH="$ZIP_PATH.zip"

    # Calculate size
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        SIZE=$(stat -f%z "$ZIP_PATH" 2>/dev/null || echo "0")
    else
        # Linux
        SIZE=$(stat -c%s "$ZIP_PATH" 2>/dev/null || echo "0")
    fi
    SIZE_MB=$(echo "scale=2; $SIZE / 1048576" | bc)

elif command -v tar &> /dev/null; then
    # Create tar.gz file
    tar -czf "$ZIP_PATH.tar.gz" -C "$OUTPUT_DIR" "$(basename "$PACKAGE_DIR")"
    ZIP_PATH="$ZIP_PATH.tar.gz"

    # Calculate size
    if [[ "$OSTYPE" == "darwin"* ]]; then
        SIZE=$(stat -f%z "$ZIP_PATH" 2>/dev/null || echo "0")
    else
        SIZE=$(stat -c%s "$ZIP_PATH" 2>/dev/null || echo "0")
    fi
    SIZE_MB=$(echo "scale=2; $SIZE / 1048576" | bc)
else
    echo "Error: Neither zip nor tar command found"
    exit 1
fi

echo ""
echo "================================================"
echo "Distribution Package Created Successfully!"
echo "================================================"
echo ""
echo "Package: $ZIP_PATH"
echo "Size: ${SIZE_MB} MB"
echo ""
echo "Distribution directory: $PACKAGE_DIR"
echo ""
echo "To test the package:"
echo "1. Extract $(basename "$ZIP_PATH") to a new location"
echo "2. Run quickstart.sh (Mac/Linux) or install.bat (Windows)"
echo "3. Follow the instructions in INSTALL.md"
echo ""