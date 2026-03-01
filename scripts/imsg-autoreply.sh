#!/bin/bash
# iMessage Auto-Reply with OpenClaw
# Polls imsg history every 2 seconds for new incoming messages
# Dispatches replies in the background so polling never blocks
# Adds protocol-aware link handling and hourly update scheduling

LOG="$HOME/.openclaw/autoreply.log"
PIDFILE="$HOME/.openclaw/autoreply.pid"
LAST_FILE="$HOME/.openclaw/.last_id"
PROTOCOL="$HOME/.openclaw/imessage/protocol.json"
STATE_FILE="$HOME/.openclaw/imessage/hourly_state.json"
FAST_ONLY_FLAG="$HOME/.openclaw/imessage/USE_FAST_BRIDGE_ONLY"

DEFAULT_HANDLE="ptrck.notux@icloud.com"
DEFAULT_INTERVAL_MIN=60

echo $$ > "$PIDFILE"
trap 'rm -f "$PIDFILE"' EXIT

log() { echo "[$(date)] $1" >> "$LOG"; }

# If fast-bridge-only is enabled, exit immediately to avoid double replies.
if [ -f "$FAST_ONLY_FLAG" ]; then
  log "Fast-bridge-only flag present; auto-reply disabled."
  exit 0
fi

load_protocol() {
  if [ -f "$PROTOCOL" ]; then
    PRIMARY_HANDLE=$(jq -r '.primary_handle // empty' "$PROTOCOL")
    PROTOCOL_NOTE=$(jq -r '.obsidian_protocol_path // empty' "$PROTOCOL")
    INTERVAL_MIN=$(jq -r '.hourly_updates.interval_minutes // empty' "$PROTOCOL")
  fi
  PRIMARY_HANDLE=${PRIMARY_HANDLE:-$DEFAULT_HANDLE}
  PROTOCOL_NOTE=${PROTOCOL_NOTE:-""}
  INTERVAL_MIN=${INTERVAL_MIN:-$DEFAULT_INTERVAL_MIN}
}

now_epoch() { date +%s; }

save_state() {
  local active="$1"
  local sender="$2"
  local topic="$3"
  local next_at="$4"
  cat > "$STATE_FILE" << STATE
{
  "active": $active,
  "sender": "${sender}",
  "topic": "${topic}",
  "next_at": ${next_at}
}
STATE
}

load_state() {
  if [ -f "$STATE_FILE" ]; then
    STATE_ACTIVE=$(jq -r '.active // false' "$STATE_FILE")
    STATE_SENDER=$(jq -r '.sender // empty' "$STATE_FILE")
    STATE_TOPIC=$(jq -r '.topic // empty' "$STATE_FILE")
    STATE_NEXT_AT=$(jq -r '.next_at // 0' "$STATE_FILE")
  else
    STATE_ACTIVE=false
    STATE_SENDER=""
    STATE_TOPIC=""
    STATE_NEXT_AT=0
  fi
}

is_hourly_request() {
  echo "$1" | grep -Eiq "hourly update|hourly updates|every hour|each hour"
}

is_stop_request() {
  local txt="$1"
  echo "$txt" | grep -Eiq "^(stop|cancel|end)$|stop updates|cancel updates|end updates"
}

is_done_request() {
  echo "$1" | grep -Eiq "^done$"
}

has_link() {
  echo "$1" | grep -Eq "https?://|www\."
}

is_social_media_url() {
  echo "$1" | grep -Eq "tiktok\.com|x\.com/|twitter\.com|youtu(\.be|be\.com)|instagram\.com/reel"
}

send_imessage() {
  local to="$1"
  local text="$2"
  imsg send --to "$to" --text "$text" >/dev/null 2>&1 || true
}

maybe_send_hourly_update() {
  load_state
  if [ "$STATE_ACTIVE" = "true" ] && [ -n "$STATE_SENDER" ]; then
    local now=$(now_epoch)
    if [ "$now" -ge "$STATE_NEXT_AT" ]; then
      local topic="$STATE_TOPIC"
      [ -z "$topic" ] && topic="the current task"
      send_imessage "$STATE_SENDER" "Hourly update: still working on ${topic}. Reply 'stop' to end updates."
      local next_at=$((now + INTERVAL_MIN*60))
      save_state true "$STATE_SENDER" "$STATE_TOPIC" "$next_at"
      log "Sent hourly update to $STATE_SENDER"
    fi
  fi
}

load_protocol

LAST=$(cat "$LAST_FILE" 2>/dev/null || echo "0")
log "Auto-reply poller starting (last ID: $LAST)"

while true; do
  maybe_send_hourly_update

  MSG=$(imsg history --chat-id 1 --limit 1 --json 2>/dev/null)
  [ -z "$MSG" ] && sleep 2 && continue

  ID=$(echo "$MSG" | jq -r '.id // empty')
  FROM_ME=$(echo "$MSG" | jq -r '.is_from_me | tostring')
  TEXT=$(echo "$MSG" | jq -r '.text // empty')
  SENDER=$(echo "$MSG" | jq -r '.sender // empty')

  if [ -n "$ID" ] && [ "$ID" -gt "$LAST" ] && [ "$FROM_ME" = "false" ] && [ -n "$TEXT" ]; then
    LAST=$ID
    echo "$ID" > "$LAST_FILE"

    # Only respond to the primary handle
    if [ -n "$PRIMARY_HANDLE" ] && [ "$SENDER" != "$PRIMARY_HANDLE" ]; then
      log "Ignoring message from non-primary sender: $SENDER"
      sleep 2
      continue
    fi

    log "Received from $SENDER (ID $ID): $TEXT"

    # Hourly updates state handling
    if is_stop_request "$TEXT" || is_done_request "$TEXT"; then
      save_state false "" "" 0
      log "Stopped hourly updates by user request"
    elif is_hourly_request "$TEXT"; then
      # Store the full message as topic context
      local_now=$(now_epoch)
      next_at=$((local_now + INTERVAL_MIN*60))
      save_state true "$SENDER" "$TEXT" "$next_at"
      log "Started hourly updates for $SENDER"
    fi

    # Build protocol instructions
    EXTRA="Follow the Messaging Protocol note"
    if [ -n "$PROTOCOL_NOTE" ]; then
      EXTRA+=" at $PROTOCOL_NOTE"
    fi
    if is_social_media_url "$TEXT"; then
      EXTRA+=" [Future Sight context: A social media URL was sent. Use your browsing and transcription tools to fetch and review the content. If the content is related to Pokémon TCG (cards, sets, sealed product, singles, prices, investment), treat this as a Future Sight reaction request — do NOT ask if this is Future Sight related, proceed directly. Ask: 'What are you looking for? (1) Draft a reaction post, (2) Research the claim/product, (3) Find the creator handle to tag, (4) All of the above.' Research using the Pokemon Card Browser and available price data, then draft a response post in Future Sight's voice: first-person, confident, data-informed, with a clear buy/hold/watch/avoid stance where relevant. Include the creator handle for tagging if findable. If the content is NOT Pokémon TCG related, ignore this context and proceed normally.]"
    elif has_link "$TEXT"; then
      EXTRA+=". If links are present: reply conversationally first, then ingest links, then send a brief confirmation."
    fi
    EXTRA+=" If the user asked for hourly updates, do not send a separate ack; the system will handle the schedule."

    # Reply via OpenClaw agent
    (
      openclaw agent --to "$SENDER" --message "$TEXT

[$EXTRA]" --channel imessage --deliver --json > /dev/null 2>&1
      log "Dispatched agent reply to $SENDER (ID $ID)"
    ) &
  fi

  sleep 2
done
