#!/bin/bash
set -e

echo "🚀 Zenith v0.3.0 Test Installation Script"
echo "========================================"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where the wheel is located
WHEEL_PATH="$(pwd)/dist/zenith_web-0.3.0-py3-none-any.whl"

if [ ! -f "$WHEEL_PATH" ]; then
    echo -e "${RED}❌ Error: Wheel not found at $WHEEL_PATH${NC}"
    echo "Please run this script from the Zenith repository root"
    exit 1
fi

echo -e "${BLUE}📦 Package location: $WHEEL_PATH${NC}"
echo

# Function to test in a repository
test_in_repo() {
    local repo_path=$1
    local repo_name=$(basename "$repo_path")
    
    echo -e "${BLUE}📂 Testing in: $repo_name${NC}"
    
    if [ ! -d "$repo_path" ]; then
        echo -e "${RED}  ❌ Directory not found: $repo_path${NC}"
        return 1
    fi
    
    cd "$repo_path"
    
    # Create virtual environment if needed
    if [ ! -d ".venv" ]; then
        echo "  Creating virtual environment..."
        uv venv > /dev/null 2>&1
    fi
    
    # Upgrade Zenith
    echo "  Installing Zenith v0.3.0..."
    uv pip install --upgrade "$WHEEL_PATH" > /dev/null 2>&1
    
    # Test imports
    echo "  Testing imports..."
    if uv run python -c "
from zenith import Zenith, File, UploadedFile, IMAGE_TYPES, MB
print('    ✅ Core imports working')
print(f'    ✅ File API: {File}')
print(f'    ✅ UploadedFile: {UploadedFile}')
print(f'    ✅ Constants: {len(IMAGE_TYPES)} image types, MB={MB}')
" 2>/dev/null; then
        echo -e "${GREEN}  ✅ All tests passed for $repo_name${NC}"
        return 0
    else
        echo -e "${RED}  ❌ Import tests failed for $repo_name${NC}"
        return 1
    fi
}

# Test in other repos if they exist
echo -e "${BLUE}🧪 Testing in production repositories:${NC}"
echo

# Add your test repositories here
TEST_REPOS=(
    "../wealthscope"
    "../yt-text"
    "../djscout"
    # Add more repos as needed
)

success_count=0
failed_count=0

for repo in "${TEST_REPOS[@]}"; do
    if test_in_repo "$repo"; then
        ((success_count++))
    else
        ((failed_count++))
    fi
    echo
done

# Summary
echo "========================================"
echo -e "${BLUE}📊 Test Summary:${NC}"
echo -e "  ${GREEN}✅ Successful: $success_count${NC}"
echo -e "  ${RED}❌ Failed: $failed_count${NC}"
echo

if [ $failed_count -eq 0 ] && [ $success_count -gt 0 ]; then
    echo -e "${GREEN}🎉 All tests passed! Ready for release.${NC}"
else
    echo -e "${RED}⚠️  Some tests failed. Please review before releasing.${NC}"
fi

# Instructions for manual testing
echo
echo "📝 For manual testing in any repo:"
echo "  1. cd <repo_path>"
echo "  2. uv pip install --upgrade $WHEEL_PATH"
echo "  3. Test your application"
echo
echo "🚀 To publish to PyPI (when ready):"
echo "  1. pip install twine"
echo "  2. twine upload dist/*"
