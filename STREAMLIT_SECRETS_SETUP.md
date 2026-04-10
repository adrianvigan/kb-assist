# Streamlit Cloud Secrets Setup

## Required Secrets for Revision Links

Add these to your Streamlit Cloud app secrets:

1. Go to https://share.streamlit.io/
2. Click on your app (kb-assist)
3. Click "Settings" (⚙️)
4. Click "Secrets"
5. Add the following:

```toml
# Base URL for your dashboard
BASE_URL = "https://kb-assist-nte7klmsth3htfzcx8d6yt.streamlit.app"

# OR if you have a separate revision portal app:
REVISION_PORTAL_URL = "https://your-revision-portal.streamlit.app"

# PostgreSQL Database (already added)
DATABASE_URL = "postgresql://neondb_owner:npg_9eIPfUK1aRSq@ep-crimson-mode-anmi3txu-pooler.c-6.us-east-1.aws.neon.tech/kb_assist_db?sslmode=require&channel_binding=require"

# Azure OpenAI (already added)
AZURE_OPENAI_ENDPOINT = "https://kb-assist-openai.openai.azure.com/"
AZURE_OPENAI_API_KEY = "5IW4lvuUQHSUoXPlqpkoGtwHfuQxGdTYbDepqI5gQE9DUFYVLksaJQQJ99CCACYeBjFXJ3w3AAABACOGmPoj"
AZURE_OPENAI_DEPLOYMENT = "kb-assistant"
AZURE_OPENAI_API_VERSION = "2024-02-15-preview"

# Email Settings (already added)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USE_TLS = true
SMTP_USERNAME = "adrianvigan2020@gmail.com"
SMTP_PASSWORD = "pppzohoqyfmtyldb"
SMTP_FROM_EMAIL = "adrianvigan2020@gmail.com"
SMTP_FROM_NAME = "KB Assist System"
```

## What Each Secret Does:

- **BASE_URL**: Main dashboard URL - used for revision links if REVISION_PORTAL_URL not set
- **REVISION_PORTAL_URL**: (Optional) Separate revision portal URL for engineers
- **DATABASE_URL**: PostgreSQL connection string
- **AZURE_OPENAI_***: AI configuration for KB generation
- **SMTP_***: Email sending configuration

## Quick Fix:

Just add this line to your secrets:
```toml
BASE_URL = "https://kb-assist-nte7klmsth3htfzcx8d6yt.streamlit.app"
```

Save and the revision links will work!
