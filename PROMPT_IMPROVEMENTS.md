# Prompt Improvements - Nemotron-3 Migration

## Problem
Model returned `"action":["grep"]` (array) instead of `"action":"grep"` (string), causing `unknown_action` failure.

## Root Cause
- `response_format={"type": "json_object"}` guarantees valid JSON **syntax**, not **schema**
- Model had no examples showing correct structure for `read_files` and `grep` actions
- No explicit type constraints in prompt

## Solution Implemented

### 1. Added JSON Type Rules Section
```
=== JSON TYPE RULES ===
CRITICAL: Follow these type constraints exactly:
- "action" field MUST be a STRING, never an array
- "files" field MUST be an ARRAY of strings
- "edits" field MUST be an ARRAY of objects
- "confidence" field MUST be a NUMBER 0.0-1.0
```

### 2. Added 8 Comprehensive Examples

**Example 1** - read_files (CSRF finding)
```json
{"action":"read_files","files":["templates/user.html"],"reason":"Need to see form at line 131 to add csrf_token"}
```

**Example 2** - grep (find POST forms)
```json
{"action":"grep","pattern":"<form.*method=\"POST\"","reason":"Find all POST forms missing csrf_token"}
```

**Example 3** - fix with single edit (SQL injection)
```json
{"action":"fix","file":"app.py",
 "edits":[
   {"old_string":"    cur.execute(f\"SELECT * FROM users WHERE id = {uid}\")",
    "new_string":"    cur.execute(\"SELECT * FROM users WHERE id = ?\", (uid,))"}
 ],
 "explanation":"Parameterized query. Stops SQL injection. f-string removed.",
 "confidence":0.95}
```

**Example 4** - fix with multiple edits (CSRF tokens)
```json
{"action":"fix","file":"templates/admin.html",
 "edits":[
   {"old_string":"<form action=\"/edit_venue\" method=\"POST\">",
    "new_string":"<form action=\"/edit_venue\" method=\"POST\">\n    {% csrf_token %}"},
   {"old_string":"<form action=\"/add_venue\" method=\"POST\">",
    "new_string":"<form action=\"/add_venue\" method=\"POST\">\n    {% csrf_token %}"},
   {"old_string":"<form action=\"/delete_show\" method=\"POST\">",
    "new_string":"<form action=\"/delete_show\" method=\"POST\">\n    {% csrf_token %}"}
 ],
 "explanation":"Added csrf_token to 3 POST forms. Blocks CSRF. No other change.",
 "confidence":0.95}
```

**Example 5** - fix with patched_content (tiny file)
```json
{"action":"fix","file":"config.py",
 "patched_content":"import os\n\nSECRET_KEY = os.environ.get('SECRET_KEY')\nDEBUG = False\nDATABASE_URL = os.environ.get('DATABASE_URL')\n",
 "explanation":"Tiny file (5 lines). Hardcoded secret removed. Env vars now.",
 "confidence":0.9}
```

**Example 6** - give_up (false positive)
```json
{"action":"give_up","reason":"Debug mode in test_app.py. Test file, not production code."}
```

**Example 7** - BAD (wrong action type)
```json
{"action":["read_files"],"files":["app.py"]}
   ^ WRONG: "action" is array. Must be string: "action":"read_files"
```

**Example 8** - BAD (wrong strategy)
```json
{"action":"fix","file":"templates/admin.html",
 "patched_content":"<!DOCTYPE html>\n<html>\n...400 lines...\n</html>"}
   ^ WRONG: Only 3 forms changed. Use edits, not patched_content. Wastes tokens.
```

### 3. Added Defensive Validation

In `tools/fix_agent.py`, after parsing JSON:
```python
# Defensive: handle action being array (model mistake)
if isinstance(action, list):
    if len(action) == 1:
        _log(f"⚠ action was array, normalized: {action} → {action[0]}")
        action = action[0]
    elif len(action) == 0:
        return FixResult(OUTCOME_BAD_JSON, detail="action field is empty array")
    else:
        return FixResult(OUTCOME_BAD_JSON, detail=f"action field is array with {len(action)} elements")
```

This gracefully handles the edge case while logging a warning.

### 4. Verified No Typos

Checked for typos seen in logs (`old_strg`, `conten:`, `explanation\field`) - none found in actual code. Log artifacts only.

## Expected Impact

- ✅ Model will see explicit examples for ALL actions
- ✅ Type constraints prevent array/string confusion
- ✅ Defensive validation handles edge cases gracefully
- ✅ Real-world examples (SQL injection, CSRF, debug mode) improve quality
- ✅ BAD examples show what NOT to do

## Testing

Run a scan with multiple findings to verify:
1. No more `"action":["grep"]` errors
2. Model correctly formats all action types
3. Fix quality remains high (0.9+ confidence)

```bash
# Start a scan and monitor logs
tail -f logs/scan_*.log
```
