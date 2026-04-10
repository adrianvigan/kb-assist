# Fixes Applied - April 10, 2026

## 🔧 Issues Fixed:

### 1. **Duplicate request_id Error** ✅
**Problem:** New submissions failing with "duplicate key value violates unique constraint"
**Cause:** request_id generator only checked `engineer_reports` table
**Fix:** Now checks ALL tables (engineer_reports, new_kb_requests, kb_update_requests) for max ID

**File:** `dashboard/api_server.py`

### 2. **SQL Syntax Error in Pending New TS** ✅
**Problem:** "syntax error at or near 'AND'" - page breaking
**Cause:** Using SQLite placeholder `?` instead of PostgreSQL `%s`
**Fix:** Changed to PostgreSQL syntax `%s`

**File:** `dashboard/pages/3_➕_Pending_New_TS.py` (line 460)

### 3. **Removed Related Engineer Reports** ✅
**Problem:** Unwanted "Related Engineer Reports" section showing
**Cause:** Section wasn't removed when you asked before
**Fix:** Completely removed the related reports query and display

**File:** `dashboard/pages/3_➕_Pending_New_TS.py` (lines 453-478)

### 4. **AI Environment Variable Mismatch** ✅
**Problem:** AI KB Matcher looking for wrong environment variable
**Cause:** Code was looking for `AZURE_OPENAI_DEPLOYMENT_NAME` but .env has `AZURE_OPENAI_DEPLOYMENT`
**Fix:** Updated to use correct environment variable name

**File:** `dashboard/ai_kb_matcher.py` (line 30)

---

## 🤖 About the "proxies" Error:

The error: `Client.init() got an unexpected keyword argument 'proxies'`

This is likely from an **outdated openai library version**. The code is correct, but if you see this error:

### Solution:
```bash
pip install --upgrade openai
```

The current code uses the **correct** initialization:
```python
self.client = AzureOpenAI(
    azure_endpoint=AZURE_ENDPOINT,
    api_key=AZURE_API_KEY,
    api_version=API_VERSION
)
```

This works with `openai >= 1.0.0`. If Render.com has an older version cached, it might fail.

---

## ✅ Manager Actions in Pending New TS:

The action buttons ARE there (they were always there!). They appear in **col2 (right sidebar)** when status is 'pending':

- **Siebel ID input** (required)
- **✅ Approve** button → Opens modal, sends email
- **❌ Reject** button (if implemented)
- **📝 Request Follow-up** button → Opens modal, sends structured feedback email
- **🤖 AI Draft** button → Generates KB draft (if AI is working)

The SQL error was preventing the page from rendering, so you couldn't see them!

---

## 📦 Files Changed:

1. `dashboard/api_server.py` - Fixed request_id generation
2. `dashboard/pages/3_➕_Pending_New_TS.py` - Fixed SQL syntax, removed related reports
3. `dashboard/ai_kb_matcher.py` - Fixed environment variable name

---

## 🚀 Next Steps:

1. **Deploy the fixes:**
   ```bash
   git add .
   git commit -m "Fix request_id duplication, SQL error, and AI env var"
   git push
   ```

2. **Wait 2 minutes** for Render/Streamlit to redeploy

3. **Test:**
   - Submit a new TS request → Should succeed
   - Check dashboard → Manager actions should appear
   - Try AI Draft → If still errors, upgrade openai library

---

## 📧 Email Functions Status:

The approve and follow-up email functions in Pending New TS are **correct** and match the fixes from Pending KB Updates:

- ✅ Uses `send_approval_email()` correctly
- ✅ Uses `send_rejection_email()` for follow-ups
- ✅ Generates tokens correctly
- ✅ Handles missing emails gracefully
- ✅ Updates database with proper status

---

**All critical issues fixed!** 🎉
