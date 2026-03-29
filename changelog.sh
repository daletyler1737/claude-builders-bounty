#!/bin/bash
# changelog.sh - Generate CHANGELOG.md from git history
# Usage: bash changelog.sh

set -e

PROJECT_NAME=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || echo '.')")
OUTPUT_FILE="CHANGELOG.md"

get_commits() {
    if git describe --tags --abbrev=0 &>/dev/null; then
        local since_tag=$(git describe --tags --abbrev=0)
        git log "$since_tag..HEAD" --pretty=format:"%s|||%b" 2>/dev/null || echo ""
    else
        git log --pretty=format:"%s|||%b" 2>/dev/null || echo ""
    fi
}

categorize() {
    local msg="$1"
    local body="${2:-}"
    local combined="$msg $body"
    local lmsg=$(echo "$msg" | tr '[:upper:]' '[:lower:]')
    
    if echo "$lmsg" | grep -qiE '^(feat|add|new|introduce|create)[\:]'; then
        echo "ADDED"
    elif echo "$lmsg" | grep -qiE '^(fix|bug|patch|resolve)[\:]'; then
        echo "FIXED"
    elif echo "$lmsg" | grep -qiE '^(remove|delete|deprecate)[\:]'; then
        echo "REMOVED"
    else
        echo "CHANGED"
    fi
}

# Build changelog
{
    echo "# Changelog"
    echo ""
    echo "## $PROJECT_NAME"
    echo ""
    echo "All notable changes are documented here."
    echo ""
    
    commits=$(get_commits)
    
    echo "### Added"
    echo ""
    echo "$commits" | while IFS='|||' read -r msg body; do
        [ -z "$msg" ] && continue
        type=$(categorize "$msg" "$body")
        if [ "$type" = "ADDED" ]; then
            echo "- $msg"
        fi
    done
    
    echo ""
    echo "### Fixed"
    echo ""
    echo "$commits" | while IFS='|||' read -r msg body; do
        [ -z "$msg" ] && continue
        type=$(categorize "$msg" "$body")
        if [ "$type" = "FIXED" ]; then
            echo "- $msg"
        fi
    done
    
    echo ""
    echo "### Changed"
    echo ""
    echo "$commits" | while IFS='|||' read -r msg body; do
        [ -z "$msg" ] && continue
        type=$(categorize "$msg" "$body")
        if [ "$type" = "CHANGED" ]; then
            echo "- $msg"
        fi
    done
    
    echo ""
    echo "### Removed"
    echo ""
    echo "$commits" | while IFS='|||' read -r msg body; do
        [ -z "$msg" ] && continue
        type=$(categorize "$msg" "$body")
        if [ "$type" = "REMOVED" ]; then
            echo "- $msg"
        fi
    done
    
} > "$OUTPUT_FILE"

count=$(grep -c '^- ' "$OUTPUT_FILE" || echo 0)
echo "✅ CHANGELOG.md generated with $count entries"
