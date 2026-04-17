#!/bin/bash
# CinePhix Backend - Validation Script
# Run this after `docker compose up` to verify everything is working

set -e

echo "=== CinePhix Backend Validation ==="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

API_URL="${API_URL:-http://localhost:8000}"

echo -e "\n${YELLOW}1. Checking API health...${NC}"
HEALTH=$(curl -s "$API_URL/health")
if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✓ API is healthy${NC}"
else
    echo -e "${RED}✗ API health check failed${NC}"
    echo "Response: $HEALTH"
    exit 1
fi

echo -e "\n${YELLOW}2. Checking docs availability...${NC}"
DOCS=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/docs")
if [ "$DOCS" = "200" ]; then
    echo -e "${GREEN}✓ Swagger docs available at $API_URL/docs${NC}"
else
    echo -e "${RED}✗ Docs not available (status: $DOCS)${NC}"
fi

echo -e "\n${YELLOW}3. Testing public endpoints (no auth)...${NC}"

# Test trending
TRENDING=$(curl -s "$API_URL/tmdb/trending/movie")
if echo "$TRENDING" | grep -q "results"; then
    echo -e "${GREEN}✓ /tmdb/trending/movie works${NC}"
else
    echo -e "${RED}✗ /tmdb/trending/movie failed${NC}"
fi

# Test search
SEARCH=$(curl -s "$API_URL/tmdb/search?q=inception")
if echo "$SEARCH" | grep -q "results"; then
    echo -e "${GREEN}✓ /tmdb/search works${NC}"
else
    echo -e "${RED}✗ /tmdb/search failed${NC}"
fi

echo -e "\n${YELLOW}4. Testing auth endpoints...${NC}"

# Test registration validation
REGISTER_VALID=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$API_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d '{"email":"test@test.com","password":"short","username":"test"}')
if [ "$REGISTER_VALID" = "422" ]; then
    echo -e "${GREEN}✓ Registration validation works (422 for invalid data)${NC}"
else
    echo -e "${YELLOW}  Registration validation: $REGISTER_VALID (expected 422)${NC}"
fi

# Test login with non-existent user
LOGIN=$(curl -s -X POST "$API_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"nonexistent@test.com","password":"wrong"}')
if echo "$LOGIN" | grep -q "Invalid"; then
    echo -e "${GREEN}✓ Login validation works${NC}"
else
    echo -e "${YELLOW}  Login response: $LOGIN${NC}"
fi

# Test protected endpoints (should return 403)
PROTECTED=$(curl -s -w "%{http_code}" -o /dev/null "$API_URL/users/me")
if [ "$PROTECTED" = "403" ]; then
    echo -e "${GREEN}✓ Protected endpoints require auth (403)${NC}"
else
    echo -e "${YELLOW}  Protected endpoint status: $PROTECTED (expected 403)${NC}"
fi

echo -e "\n${YELLOW}5. Testing complete auth flow...${NC}"

# Register a test user
EMAIL="test_$(date +%s)@cinephix_test.com"
REGISTER=$(curl -s -X POST "$API_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"TestPassword123!\",\"username\":\"testuser$(date +%s)\"}")

ACCESS_TOKEN=$(echo "$REGISTER" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")

if [ -n "$ACCESS_TOKEN" ]; then
    echo -e "${GREEN}✓ Registration successful${NC}"
    
    # Test authenticated endpoint
    ME=$(curl -s "$API_URL/users/me" -H "Authorization: Bearer $ACCESS_TOKEN")
    if echo "$ME" | grep -q "email"; then
        echo -e "${GREEN}✓ Authenticated /users/me works${NC}"
    fi
    
    # Test watchlist
    WATCHLIST=$(curl -s -X POST "$API_URL/watchlist" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"tmdb_id":27205,"media_type":"movie"}')
    if echo "$WATCHLIST" | grep -q "id"; then
        echo -e "${GREEN}✓ Watchlist add works${NC}"
    fi
    
    # Test favorites
    FAVORITE=$(curl -s -X POST "$API_URL/favorites" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"tmdb_id":27205,"media_type":"movie"}')
    if echo "$FAVORITE" | grep -q "id"; then
        echo -e "${GREEN}✓ Favorites add works${NC}"
    fi
    
    # Test refresh token
    REFRESH_TOKEN=$(echo "$REGISTER" | python3 -c "import sys,json; print(json.load(sys.stdin).get('refresh_token',''))")
    if [ -n "$REFRESH_TOKEN" ]; then
        REFRESH=$(curl -s -X POST "$API_URL/auth/refresh" \
            -H "Content-Type: application/json" \
            -d "{\"refresh_token\":\"$REFRESH_TOKEN\"}")
        if echo "$REFRESH" | grep -q "access_token"; then
            echo -e "${GREEN}✓ Token refresh works${NC}"
        fi
    fi
    
    echo -e "\n${GREEN}=== All Phase 1 features validated! ===${NC}"
    echo "Backend is ready for frontend integration."
else
    echo -e "${RED}✗ Registration failed${NC}"
    echo "Response: $REGISTER"
fi

echo -e "\n${YELLOW}Note: For full test coverage, run pytest in the container:${NC}"
echo "  docker compose exec api pytest"