#!/bin/bash
# Signals API Demo Script (Bash version)
# Tests all major endpoints for backend demo purposes.
#
# Usage:
#   ./scripts/demo_server.sh [company_name]
#   ./scripts/demo_server.sh Anthropic
#
# Requirements: curl, jq (optional but recommended)

set -e

BASE_URL="${BASE_URL:-http://localhost:3001}"
COMPANY="${1:-Anthropic}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_section() {
    echo ""
    echo "============================================================"
    echo "$1"
    echo "============================================================"
    echo ""
}

print_response() {
    local title="$1"
    local status_code="$2"
    local response="$3"
    
    if [ "$status_code" -lt 400 ]; then
        echo -e "${GREEN}✓${NC} $title"
        echo "  Status: $status_code"
    else
        echo -e "${RED}✗${NC} $title"
        echo "  Status: $status_code"
    fi
    
    if command -v jq &> /dev/null; then
        echo "$response" | jq '.' 2>/dev/null || echo "$response"
    else
        echo "$response"
    fi
    echo ""
}

# Test 1: Health Check
print_section "1. Health Check"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/health" || echo -e "\n000")
HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | head -n -1)
HEALTH_CODE=$(echo "$HEALTH_RESPONSE" | tail -n 1)

if [ "$HEALTH_CODE" = "000" ]; then
    echo -e "${RED}✗ Cannot connect to server. Is it running?${NC}"
    echo "   Try: uvicorn app.main:app --reload --port 3001"
    exit 1
fi

print_response "Health Check" "$HEALTH_CODE" "$HEALTH_BODY"

# Test 2: List Companies
print_section "2. List Companies"
COMPANIES_RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/companies")
COMPANIES_BODY=$(echo "$COMPANIES_RESPONSE" | head -n -1)
COMPANIES_CODE=$(echo "$COMPANIES_RESPONSE" | tail -n 1)
print_response "List Companies" "$COMPANIES_CODE" "$COMPANIES_BODY"

if command -v jq &> /dev/null; then
    COMPANY_COUNT=$(echo "$COMPANIES_BODY" | jq '.companies | length' 2>/dev/null || echo "0")
    if [ "$COMPANY_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓ Found $COMPANY_COUNT companies${NC}"
        FIRST_NAME=$(echo "$COMPANIES_BODY" | jq -r '.companies[0].name // "N/A"' 2>/dev/null)
        echo "  First Company: $FIRST_NAME"
    fi
fi

# Test 3: Search Companies
print_section "3. Search Companies"
SEARCH_RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/companies/search?q=AI")
SEARCH_BODY=$(echo "$SEARCH_RESPONSE" | head -n -1)
SEARCH_CODE=$(echo "$SEARCH_RESPONSE" | tail -n 1)
print_response "Search Companies (query: 'AI')" "$SEARCH_CODE" "$SEARCH_BODY"

# Test 4: Analyze Company
print_section "4. Analyze Company (Pipeline)"
echo -e "${YELLOW}Analyzing: $COMPANY${NC}"
echo "This may take 30-60 seconds..."
echo ""

ANALYZE_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "$BASE_URL/api/analyze" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"$COMPANY\"}" \
    --max-time 120)

ANALYZE_BODY=$(echo "$ANALYZE_RESPONSE" | head -n -1)
ANALYZE_CODE=$(echo "$ANALYZE_RESPONSE" | tail -n 1)
print_response "Analyze Company: $COMPANY" "$ANALYZE_CODE" "$ANALYZE_BODY"

# Extract slug if available
SLUG=""
if command -v jq &> /dev/null; then
    SLUG=$(echo "$ANALYZE_BODY" | jq -r '.data.slug // empty' 2>/dev/null)
    if [ -z "$SLUG" ]; then
        # Try to get from companies list
        SLUG=$(echo "$COMPANIES_BODY" | jq -r '.companies[0].slug // .companies[0].id // empty' 2>/dev/null | sed 's|.*/||')
    fi
fi

# Test 5: Company Details (if we have a slug)
if [ -n "$SLUG" ]; then
    print_section "5. Company Details"
    DETAILS_RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/company/$SLUG")
    DETAILS_BODY=$(echo "$DETAILS_RESPONSE" | head -n -1)
    DETAILS_CODE=$(echo "$DETAILS_RESPONSE" | tail -n 1)
    print_response "Get Company: $SLUG" "$DETAILS_CODE" "$DETAILS_BODY"
    
    # Test 6: Company Highlights
    print_section "6. Company Highlights"
    HIGHLIGHTS_RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/company/$SLUG/highlights")
    HIGHLIGHTS_BODY=$(echo "$HIGHLIGHTS_RESPONSE" | head -n -1)
    HIGHLIGHTS_CODE=$(echo "$HIGHLIGHTS_RESPONSE" | tail -n 1)
    print_response "Get Highlights: $SLUG" "$HIGHLIGHTS_CODE" "$HIGHLIGHTS_BODY"
fi

# Test 7: All Highlights
print_section "7. All Highlights"
ALL_HIGHLIGHTS_RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/highlights?limit=5")
ALL_HIGHLIGHTS_BODY=$(echo "$ALL_HIGHLIGHTS_RESPONSE" | head -n -1)
ALL_HIGHLIGHTS_CODE=$(echo "$ALL_HIGHLIGHTS_RESPONSE" | tail -n 1)
print_response "Get All Highlights" "$ALL_HIGHLIGHTS_CODE" "$ALL_HIGHLIGHTS_BODY"

# Test 8: Chat
print_section "8. Chat (Streaming)"
CHAT_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "$BASE_URL/api/chat" \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"What is $COMPANY?\"}" \
    --max-time 30)
CHAT_BODY=$(echo "$CHAT_RESPONSE" | head -n -1)
CHAT_CODE=$(echo "$CHAT_RESPONSE" | tail -n 1)
echo -e "${GREEN}✓${NC} Chat endpoint"
echo "  Status: $CHAT_CODE"
echo "  Note: Full streaming requires SSE client"
echo ""

# Test 9: HN Search
print_section "9. Hacker News Search"
HN_RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/reports/hn/search?q=$COMPANY&limit=3")
HN_BODY=$(echo "$HN_RESPONSE" | head -n -1)
HN_CODE=$(echo "$HN_RESPONSE" | tail -n 1)
print_response "HN Search: $COMPANY" "$HN_CODE" "$HN_BODY"

# Summary
print_section "Demo Complete"
echo -e "${GREEN}✓ All tests completed!${NC}"
echo ""
echo "API Base URL: $BASE_URL"
echo "Test Company: $COMPANY"
echo ""

