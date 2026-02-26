#!/bin/bash
# Launch the Pokemon card browser with a local HTTP server
# Serves from ~ so /pokemon_card_images/ and /pokemon_card_data/ resolve correctly

PORT=8765
ROOT="$HOME"
HTML="pokemon_card_browser.html"

# Kill any existing server on this port
lsof -ti:$PORT | xargs kill -9 2>/dev/null

echo "Starting Pokemon card browser at http://localhost:$PORT/$HTML"
echo "Press Ctrl+C to stop."

# Start Python HTTP server in the background
cd "$ROOT"
/usr/bin/python3 -m http.server $PORT --bind 127.0.0.1 &
SERVER_PID=$!

sleep 0.5

# Open in Chrome
open -a "Google Chrome" "http://localhost:$PORT/$HTML"

# Wait for Ctrl+C then clean up
trap "kill $SERVER_PID 2>/dev/null; echo 'Server stopped.'" EXIT
wait $SERVER_PID
