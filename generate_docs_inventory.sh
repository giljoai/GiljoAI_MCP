#!/usr/bin/env bash
#
# Documentation Inventory Generator
# Workaround for Cline's broken read_file tool
#
# This script generates a comprehensive inventory of all documentation files
# in F:\GiljoAI_MCP\docs with file summaries and recommendations.
#

DOCS_DIR="/f/GiljoAI_MCP/docs"
OUTPUT_FILE="/f/GiljoAI_MCP/docs/index_files_detailed.md"

echo "# Comprehensive Documentation Inventory" > "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "**Generated**: $(date +'%Y-%m-%d %H:%M:%S')" >> "$OUTPUT_FILE"
echo "**Tool**: Bash script (Cline read_file tool broken)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "---" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Count total files
TOTAL_FILES=$(find "$DOCS_DIR" -type f \( -name "*.md" -o -name "*.txt" \) | wc -l)
echo "## Statistics" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "- **Total Files**: $TOTAL_FILES" >> "$OUTPUT_FILE"
echo "- **Total Folders**: $(find "$DOCS_DIR" -type d | wc -l)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "---" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

echo "## File Inventory" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "| File Name | Current Path | File Size | Last Modified | Recommended Path |" >> "$OUTPUT_FILE"
echo "|-----------|--------------|-----------|---------------|------------------|" >> "$OUTPUT_FILE"

# Process each file
find "$DOCS_DIR" -type f \( -name "*.md" -o -name "*.txt" \) | sort | while read -r filepath; do
    filename=$(basename "$filepath")
    relative_path=$(echo "$filepath" | sed "s|$DOCS_DIR/||")
    filesize=$(stat -c%s "$filepath" 2>/dev/null || stat -f%z "$filepath" 2>/dev/null || echo "N/A")
    modtime=$(stat -c%y "$filepath" 2>/dev/null | cut -d' ' -f1 || stat -f%Sm -t "%Y-%m-%d" "$filepath" 2>/dev/null || echo "N/A")

    # Determine recommended path based on current location and filename
    recommended=""

    case "$relative_path" in
        devlogs/*)
            recommended=$(echo "$relative_path" | sed 's|devlogs/|devlog/|')
            ;;
        tests/*)
            recommended=$(echo "$relative_path" | sed 's|tests/|testing/|')
            ;;
        HANDOFF*.md|HANDOVER*.md)
            recommended="handoffs/$filename"
            ;;
        README_FIRST.md|PRODUCT_PROPOSAL.md|PROJECT_CARDS.md|PROJECT_ORCHESTRATION_PLAN.md|TECHNICAL_ARCHITECTURE.md)
            recommended="overview/$filename"
            ;;
        IMPLEMENTATION_PLAN.md|task_progress.md|Techdebt.md)
            recommended="planning/$filename"
            ;;
        LINTING_STANDARDS.md|CONTRIBUTING.md|SECURITY.md)
            recommended="standards/$filename"
            ;;
        *)
            recommended="$relative_path"
            ;;
    esac

    echo "| $filename | $relative_path | $filesize bytes | $modtime | $recommended |" >> "$OUTPUT_FILE"
done

echo "" >> "$OUTPUT_FILE"
echo "---" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "## Folder Consolidation Recommendations" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "### 1. Merge Duplicate Folders" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "\`\`\`bash" >> "$OUTPUT_FILE"
echo "cd /f/GiljoAI_MCP/docs" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "# Merge devlogs into devlog" >> "$OUTPUT_FILE"
echo "if [ -d devlogs ]; then" >> "$OUTPUT_FILE"
echo "    mv devlogs/* devlog/ 2>/dev/null" >> "$OUTPUT_FILE"
echo "    rmdir devlogs" >> "$OUTPUT_FILE"
echo "fi" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "# Merge tests into testing" >> "$OUTPUT_FILE"
echo "if [ -d tests ]; then" >> "$OUTPUT_FILE"
echo "    mv tests/* testing/ 2>/dev/null" >> "$OUTPUT_FILE"
echo "    rmdir tests" >> "$OUTPUT_FILE"
echo "fi" >> "$OUTPUT_FILE"
echo "\`\`\`" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

echo "### 2. Create Missing Category Folders" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "\`\`\`bash" >> "$OUTPUT_FILE"
echo "mkdir -p /f/GiljoAI_MCP/docs/{overview,planning,standards,handoffs}" >> "$OUTPUT_FILE"
echo "\`\`\`" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

echo "" >> "$OUTPUT_FILE"
echo "---" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "**Inventory generation complete!**" >> "$OUTPUT_FILE"

echo "✅ Inventory generated: $OUTPUT_FILE"
echo "📊 Total files processed: $TOTAL_FILES"
