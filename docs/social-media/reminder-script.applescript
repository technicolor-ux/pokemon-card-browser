-- Future Sight Prediction Reminder Script
-- Usage: Fill in the variables below, then run via Script Editor or:
--   osascript reminder-script.applescript
--
-- Or call from Terminal with inline variables:
--   osascript -e 'set productName to "..."' ... reminder-script.applescript

-- ─────────────────────────────────────────
-- EDIT THESE VARIABLES BEFORE RUNNING
-- ─────────────────────────────────────────

set productName to "Prismatic Evolutions ETB"
set stanceName to "Buy"
set followUpDate to "March 1, 2027"   -- Format: "Month D, YYYY"
set postURL to "https://www.threads.net/@futuresight/post/EXAMPLE"
set predictionSummary to "Bought at $65, expecting floor to hold above $80 by March 2027 based on Eevee IP and reprint risk."

-- ─────────────────────────────────────────
-- SCRIPT — DO NOT EDIT BELOW THIS LINE
-- ─────────────────────────────────────────

set reminderTitle to "Future Sight Follow-Up: " & productName & " — " & stanceName
set reminderBody to postURL & return & predictionSummary
set reminderDueDate to date followUpDate

tell application "Reminders"
	-- Create the "Future Sight" list if it doesn't exist
	if not (exists list "Future Sight") then
		make new list with properties {name:"Future Sight"}
	end if

	set targetList to list "Future Sight"

	-- Create the reminder
	set newReminder to make new reminder at end of targetList with properties {¬
		name:reminderTitle, ¬
		due date:reminderDueDate, ¬
		body:reminderBody}

	return "Reminder created: " & reminderTitle & " (due " & followUpDate & ")"
end tell
