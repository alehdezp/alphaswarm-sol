#!/bin/bash
# Crawl4AI Docker Wrapper for Phase 17
# Usage: ./scripts/crawl4ai_wrapper.sh <url> <source_id>

URL="$1"
SOURCE_ID="$2"
OUTPUT_DIR=".vrs/crawl_cache"

if [ -z "$URL" ] || [ -z "$SOURCE_ID" ]; then
    echo "Usage: $0 <url> <source_id>"
    echo "Example: $0 https://rekt.news rekt-news"
    exit 1
fi

# Ensure output directory exists
mkdir -p "${OUTPUT_DIR}"

# Ensure Docker is running
if ! docker ps >/dev/null 2>&1; then
    echo "Docker not running. Starting OrbStack..."
    open -a OrbStack
    sleep 5

    # Check again
    if ! docker ps >/dev/null 2>&1; then
        echo "ERROR: Could not start Docker. Please start Docker Desktop or OrbStack manually."
        exit 1
    fi
fi

# Check if crawl4ai container exists
if ! docker ps -a | grep -q crawl4ai; then
    echo "Pulling crawl4ai image..."
    docker pull unclecode/crawl4ai:latest || {
        echo "ERROR: Failed to pull crawl4ai image"
        exit 1
    }
fi

# Start container if not running
if ! docker ps | grep -q crawl4ai; then
    echo "Starting crawl4ai container..."
    docker run -d -p 11235:11235 --name crawl4ai unclecode/crawl4ai:latest || {
        # Try to remove and restart if exists but stopped
        docker rm crawl4ai 2>/dev/null
        docker run -d -p 11235:11235 --name crawl4ai unclecode/crawl4ai:latest
    }
    sleep 5
fi

# Verify container is healthy
if ! docker ps | grep -q crawl4ai; then
    echo "ERROR: crawl4ai container failed to start"
    exit 1
fi

# Crawl URL
TIMESTAMP=$(date -u +"%Y-%m-%dT%H-%M-%S.%6N")
OUTPUT_FILE="${OUTPUT_DIR}/${SOURCE_ID}_${TIMESTAMP}.json"

echo "Crawling ${URL}..."
echo "Source ID: ${SOURCE_ID}"

curl -X POST http://localhost:11235/crawl \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"${URL}\",
    \"source_id\": \"${SOURCE_ID}\",
    \"js_code\": [],
    \"wait_for\": \"\"
  }" \
  -o "${OUTPUT_FILE}" 2>/dev/null

if [ $? -eq 0 ] && [ -f "${OUTPUT_FILE}" ]; then
    echo "✓ Crawl complete!"
    echo "✓ Saved to: ${OUTPUT_FILE}"

    # Show brief summary
    if command -v jq >/dev/null 2>&1; then
        echo ""
        echo "Summary:"
        jq -r '.pages_crawled, .total_tokens, .success' "${OUTPUT_FILE}" 2>/dev/null | \
          xargs printf "  Pages: %s\n  Tokens: %s\n  Success: %s\n"
    fi
else
    echo "ERROR: Crawl failed"
    exit 1
fi
