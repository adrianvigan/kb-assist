# KB Assist - Complete Environment Variables Guide

## 🔑 Required Environment Variables

Below are ALL environment variables needed for the complete KB Assist system.

---

## 1. 🗄️ DATABASE (Required for ALL components)

### **DATABASE_URL**
**Required by:** API Server, Dashboard, Revision Portal
**Format:** PostgreSQL connection string
**Example:**
```
DATABASE_URL=postgresql://username:password@host:5432/database?sslmode=require
```

**Where to get it:**
- From Neon.tech dashboard → Connection Details → "Pooled connection"
- Example from Neon:
  ```
  postgresql://neondb_owner:xxxxx@ep-crimson-mode-anmi3txu-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require
  ```

---

## 2. 🤖 AZURE OPENAI (Required for AI features)

### **AZURE_OPENAI_ENDPOINT**
**Required by:** API Server (for AI validation)
**Format:** `https://your-resource-name.openai.azure.com/`
**Example:**
```
AZURE_OPENAI_ENDPOINT=https://kb-assist-ai.openai.azure.com/
```

### **AZURE_OPENAI_API_KEY**
**Required by:** API Server (for AI validation)
**Format:** Your Azure OpenAI API key
**Example:**
```
AZURE_OPENAI_API_KEY=1234567890abcdef1234567890abcdef
```

### **AZURE_OPENAI_DEPLOYMENT**
**Required by:** API Server (for AI validation)
**Format:** Your deployment name
**Example:**
```
AZURE_OPENAI_DEPLOYMENT=kb-assistant
```

### **AZURE_OPENAI_API_VERSION** (Optional)
**Default:** `2024-02-15-preview`
**Example:**
```
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

**Where to get it:**
- Azure Portal → Your OpenAI Resource → Keys and Endpoint

---

## 3. 📧 EMAIL CONFIGURATION (Required for notifications)

### **SMTP_SERVER**
**Default:** `smtp-mail.outlook.com` (for Office 365)
**Example:**
```
SMTP_SERVER=smtp-mail.outlook.com
```

### **SMTP_PORT**
**Default:** `587`
**Example:**
```
SMTP_PORT=587
```

### **SMTP_USE_TLS**
**Default:** `True`
**Example:**
```
SMTP_USE_TLS=True
```

### **SMTP_USERNAME**
**Required by:** API Server, Dashboard
**Format:** Your email address
**Example:**
```
SMTP_USERNAME=kbassist@trendmicro.com
```

### **SMTP_PASSWORD**
**Required by:** API Server, Dashboard
**Format:** Your email password or app-specific password
**Example:**
```
SMTP_PASSWORD=your-app-specific-password
```

### **SMTP_FROM_EMAIL** (Optional)
**Default:** Same as SMTP_USERNAME
**Example:**
```
SMTP_FROM_EMAIL=kbassist@trendmicro.com
```

### **SMTP_FROM_NAME** (Optional)
**Default:** `KB Assist System`
**Example:**
```
SMTP_FROM_NAME=KB Assist System
```

**How to get Office 365 App Password:**
1. Go to https://account.microsoft.com/security
2. Select "Advanced security options"
3. Under "App passwords", create new
4. Use that password as `SMTP_PASSWORD`

---

## 4. 🌐 URL CONFIGURATION

### **BASE_URL** (Optional)
**Default:** `http://localhost:5000`
**Used for:** Email verification links
**Example:**
```
BASE_URL=https://kb-assist-nte7klmsth3htfzcx8d6yt.streamlit.app
```

### **REVISION_PORTAL_URL**
**Required by:** Dashboard (for sending revision links to engineers)
**Format:** URL to standalone revision portal
**Example:**
```
REVISION_PORTAL_URL=https://kb-assist-revision.streamlit.app
```

### **LINK_EXPIRATION_DAYS** (Optional)
**Default:** `7`
**Example:**
```
LINK_EXPIRATION_DAYS=7
```

---

## 📋 Environment Variables by Component

### **API Server** (Flask - needs to be deployed separately)
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# AI Features
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_DEPLOYMENT=kb-assistant

# Email
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USE_TLS=True
SMTP_USERNAME=kbassist@trendmicro.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=kbassist@trendmicro.com
SMTP_FROM_NAME=KB Assist System
```

### **Dashboard** (Streamlit Cloud)
Add these in Streamlit Cloud → App Settings → Secrets:
```toml
DATABASE_URL = "postgresql://user:pass@host:5432/db"
REVISION_PORTAL_URL = "https://kb-assist-revision.streamlit.app"
```

### **Revision Portal** (Streamlit Cloud - separate app)
Add these in Streamlit Cloud → App Settings → Secrets:
```toml
DATABASE_URL = "postgresql://user:pass@host:5432/db"
```

---

## 🚀 Quick Setup for Each Deployment Platform

### **Option 1: Render.com (API Server)**
1. Go to Render.com → New → Web Service
2. Connect GitHub repo
3. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python dashboard/api_server.py`
4. Add Environment Variables (from dashboard):
   - `DATABASE_URL`
   - `AZURE_OPENAI_ENDPOINT`
   - `AZURE_OPENAI_API_KEY`
   - `AZURE_OPENAI_DEPLOYMENT`
   - `SMTP_USERNAME`
   - `SMTP_PASSWORD`
   - `SMTP_SERVER`
   - `SMTP_PORT`
   - `SMTP_FROM_EMAIL`

### **Option 2: Railway.app (API Server)**
1. Go to Railway.app → New Project
2. Deploy from GitHub repo
3. Add same environment variables as Render

### **Option 3: Streamlit Cloud (Dashboard & Revision Portal)**
Already set up! Just add secrets:
1. Go to app settings → Secrets
2. Add variables in TOML format (see above)

---

## 📝 Complete .env File Template

Create a `.env` file in your project root for local development:

```bash
# ========================================
# DATABASE
# ========================================
DATABASE_URL=postgresql://neondb_owner:xxxxx@ep-crimson-mode-anmi3txu-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require

# ========================================
# AZURE OPENAI (AI Features)
# ========================================
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=kb-assistant
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# ========================================
# EMAIL CONFIGURATION (Office 365)
# ========================================
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USE_TLS=True
SMTP_USERNAME=kbassist@trendmicro.com
SMTP_PASSWORD=your-app-specific-password-here
SMTP_FROM_EMAIL=kbassist@trendmicro.com
SMTP_FROM_NAME=KB Assist System

# ========================================
# URLS
# ========================================
BASE_URL=https://kb-assist-nte7klmsth3htfzcx8d6yt.streamlit.app
REVISION_PORTAL_URL=https://kb-assist-revision.streamlit.app
LINK_EXPIRATION_DAYS=7
```

---

## ✅ Verification Checklist

After setting all variables, verify:

- [ ] API Server can connect to PostgreSQL
- [ ] Dashboard can connect to PostgreSQL
- [ ] Revision Portal can connect to PostgreSQL
- [ ] AI validation works (test a submission)
- [ ] Email notifications work (test approval/rejection)
- [ ] Revision links work (test follow-up flow)

---

## 🔍 Troubleshooting

**Database Connection Failed:**
- Verify DATABASE_URL is correct
- Check if IP whitelist is configured (some DBs require it)
- Ensure SSL mode is included: `?sslmode=require`

**Email Failed:**
- Verify SMTP credentials are correct
- For Office 365, ensure you're using app-specific password
- Check if SMTP port 587 is not blocked

**AI Validation Not Working:**
- Verify all AZURE_OPENAI_* variables are set
- Check API key is valid
- Ensure deployment name matches Azure portal

---

**Last Updated:** 2026-04-10
**Version:** 2.0 (PostgreSQL migration)
