# Google Cloud Setup Guide - Step by Step

This guide walks you through setting up Google Cloud for the African AI Governance Newsletter.

---

## Part 1: Create Google Cloud Project

### Step 1.1: Access Google Cloud Console

1. Open your browser and go to: **https://console.cloud.google.com/**
2. Sign in with your Google account
3. If this is your first time, accept the Terms of Service

### Step 1.2: Create New Project

1. Look at the top-left of the page, next to "Google Cloud"
2. Click the **project dropdown** (might say "Select a project" or show an existing project name)
3. In the popup, click **"NEW PROJECT"** (top right of the modal)
4. Fill in:
   - **Project name:** `ai-governance-newsletter`
   - **Organization:** Leave as default (or select your org if you have one)
   - **Location:** Leave as default
5. Click **"CREATE"**
6. Wait 30-60 seconds for project creation
7. Click the notification bell (top right) → Click on your new project to select it

**Verification:** The project dropdown at the top should now show `ai-governance-newsletter`

---

## Part 2: Enable Required APIs

### Step 2.1: Open API Library

1. Click the **hamburger menu (☰)** at the top left
2. Navigate to: **APIs & Services** → **Library**
3. You'll see the API Library search page

### Step 2.2: Enable Google Sheets API

1. In the search box, type: **Google Sheets API**
2. Click on **"Google Sheets API"** in the results
3. Click the blue **"ENABLE"** button
4. Wait for it to enable (few seconds)

### Step 2.3: Enable Google Drive API

1. Click the back arrow or go to: **APIs & Services** → **Library** again
2. Search for: **Google Drive API**
3. Click on **"Google Drive API"**
4. Click **"ENABLE"**

**Verification:** Go to **APIs & Services** → **Enabled APIs** - you should see both APIs listed.

---

## Part 3: Create Service Account

### Step 3.1: Navigate to Credentials

1. Click **hamburger menu (☰)** → **APIs & Services** → **Credentials**
2. You'll see the Credentials dashboard

### Step 3.2: Create Service Account

1. Click **"+ CREATE CREDENTIALS"** at the top
2. Select **"Service account"** from the dropdown
3. Fill in the form:
   - **Service account name:** `newsletter-bot`
   - **Service account ID:** (auto-fills as `newsletter-bot`)
   - **Service account description:** `Automated newsletter scraper for AI governance news`
4. Click **"CREATE AND CONTINUE"**

### Step 3.3: Skip Optional Steps

1. **"Grant this service account access to project"** - Click **"CONTINUE"** (skip this)
2. **"Grant users access to this service account"** - Click **"DONE"** (skip this)

**Verification:** You should see `newsletter-bot@ai-governance-newsletter.iam.gserviceaccount.com` in your service accounts list.

---

## Part 4: Generate JSON Key File

### Step 4.1: Open Service Account

1. On the Credentials page, find **"Service Accounts"** section at the bottom
2. Click on your service account name (`newsletter-bot@...`)
3. You'll see the Service Account details page

### Step 4.2: Create Key

1. Click the **"KEYS"** tab at the top
2. Click **"ADD KEY"** dropdown → **"Create new key"**
3. Select **"JSON"** (should be selected by default)
4. Click **"CREATE"**

### Step 4.3: Save the Key File

1. A JSON file will automatically download to your computer
2. The filename will be something like: `ai-governance-newsletter-abc123.json`
3. **IMPORTANT:** Keep this file safe! It contains your credentials.
4. Open the file in a text editor - you'll need the contents for GitHub Secrets

**What the JSON looks like:**
```json
{
  "type": "service_account",
  "project_id": "ai-governance-newsletter",
  "private_key_id": "abc123...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "newsletter-bot@ai-governance-newsletter.iam.gserviceaccount.com",
  "client_id": "123456789",
  ...
}
```

**Copy the SERVICE ACCOUNT EMAIL** - You'll need it to share the Google Sheet:
`newsletter-bot@ai-governance-newsletter.iam.gserviceaccount.com`

---

## Part 5: Get Gemini API Key

### Step 5.1: Access Google AI Studio

1. Open a new tab and go to: **https://aistudio.google.com/app/apikey**
2. Sign in with the same Google account

### Step 5.2: Create API Key

1. Click **"Create API key"**
2. Select your project (`ai-governance-newsletter`)
3. Click **"Create API key in existing project"**
4. Your API key will be displayed - **COPY IT NOW**

**Example API key format:** `AIzaSyB...abc123`

### Step 5.3: Save Your API Key

1. Copy the API key to a secure location
2. You'll add this to GitHub Secrets as `GEMINI_API_KEY`

---

## Part 6: Set Up Google Sheet

### Step 6.1: Create New Sheet

1. Go to: **https://sheets.google.com/**
2. Click **"+ Blank"** to create a new spreadsheet
3. Click on "Untitled spreadsheet" and rename to: **AI Governance Newsletter Database**

### Step 6.2: Add Headers

In Row 1, enter these headers (one per cell, A1 through L1):

| Cell | Header |
|------|--------|
| A1 | Title |
| B1 | URL |
| C1 | Publication |
| D1 | Date Published |
| E1 | Primary Category |
| F1 | Sub-Category |
| G1 | Geography |
| H1 | Relevance Score |
| I1 | Africa Related |
| J1 | Date Scraped |
| K1 | Review Status |
| L1 | Your Commentary |

### Step 6.3: Share with Service Account

1. Click the **"Share"** button (top right, green button)
2. In the "Add people and groups" field, paste your service account email:
   `newsletter-bot@ai-governance-newsletter.iam.gserviceaccount.com`
3. Set permission to **"Editor"**
4. **UNCHECK** "Notify people"
5. Click **"Share"**

### Step 6.4: Get Your Sheet ID

Look at your browser's URL bar. It will look like:
```
https://docs.google.com/spreadsheets/d/1ABC123xyz_example_ID_here/edit#gid=0
```

The Sheet ID is the long string between `/d/` and `/edit`:
```
1ABC123xyz_example_ID_here
```

**Copy this ID** - You'll add it to GitHub Secrets as `SHEET_ID`

### Step 6.5: Add Data Validation (Optional but Recommended)

**For Review Status column (K):**
1. Click on column K header to select the entire column
2. Go to **Data** → **Data validation**
3. Click **"Add rule"**
4. Criteria: **"Dropdown (from a list)"**
5. Enter values: `Pending, Selected, Rejected`
6. Click **"Done"**

**For Conditional Formatting (Relevance Score):**
1. Select column H (click the header)
2. Go to **Format** → **Conditional formatting**
3. Add rules:
   - **8-10 (green):** Custom formula `=AND(H1>=8, H1<=10)` → Green fill
   - **5-7 (yellow):** Custom formula `=AND(H1>=5, H1<=7)` → Yellow fill
   - **1-4 (red):** Custom formula `=AND(H1>=1, H1<=4)` → Red fill

---

## Part 7: Set Up GitHub Repository

### Step 7.1: Create Repository

1. Go to: **https://github.com/**
2. Sign in to your account
3. Click **"+"** in the top right → **"New repository"**
4. Fill in:
   - **Repository name:** `african-ai-governance-newsletter`
   - **Description:** `Automated AI governance news scraper for Africa`
   - **Visibility:** Private (recommended)
5. **DO NOT** initialize with README (we'll upload our own)
6. Click **"Create repository"**

### Step 7.2: Upload Files

**Option A: Using GitHub Web Interface**
1. Click **"uploading an existing file"** on the empty repo page
2. Drag and drop all files maintaining the folder structure
3. Click **"Commit changes"**

**Option B: Using Git Command Line**
```bash
git clone https://github.com/YOUR_USERNAME/african-ai-governance-newsletter.git
cd african-ai-governance-newsletter
# Copy all files into this folder
git add .
git commit -m "Initial commit"
git push origin main
```

### Step 7.3: Add GitHub Secrets

1. Go to your repository on GitHub
2. Click **"Settings"** tab
3. In the left sidebar, click **"Secrets and variables"** → **"Actions"**
4. Click **"New repository secret"** for each:

| Secret Name | Value |
|-------------|-------|
| `GEMINI_API_KEY` | Your Gemini API key (e.g., `AIzaSyB...`) |
| `GOOGLE_SHEETS_CREDS` | **ENTIRE CONTENTS** of the JSON key file (including `{` and `}`) |
| `SHEET_ID` | Your Google Sheet ID (e.g., `1ABC123xyz...`) |

**For GOOGLE_SHEETS_CREDS:**
1. Open your downloaded JSON key file
2. Select ALL the text (Ctrl+A / Cmd+A)
3. Copy it (Ctrl+C / Cmd+C)
4. Paste into the Secret value field

---

## Part 8: Test Your Setup

### Step 8.1: Trigger Manual Run

1. Go to your repository on GitHub
2. Click **"Actions"** tab
3. Click **"Scrape AI Governance News"** in the left sidebar
4. Click **"Run workflow"** dropdown (right side)
5. Click the green **"Run workflow"** button

### Step 8.2: Monitor Execution

1. Click on the running workflow to see details
2. Click on **"scrape"** job to see logs
3. Watch for any errors

**Expected output:**
```
📚 Loading sources configuration...
   Loaded 30 RSS feeds
📋 Fetching existing URLs from Google Sheet...
   Found 0 existing entries
...
SUMMARY
  Articles processed:    X
  Successfully classified: Y
  Saved to sheet:        Z
```

### Step 8.3: Verify in Google Sheet

1. Open your Google Sheet
2. You should see new rows with classified articles
3. Check that all columns are populated correctly

---

## Troubleshooting

### "Permission denied" or "Sheet not found"
- Verify the Sheet ID is correct
- Confirm you shared the sheet with the service account email
- Check the service account has "Editor" permission

### "Invalid credentials" or "Authentication failed"  
- Verify `GOOGLE_SHEETS_CREDS` contains the FULL JSON (including `{` and `}`)
- Make sure there are no extra spaces or line breaks
- Re-download the JSON key if needed

### "Gemini API error"
- Verify `GEMINI_API_KEY` is correct
- Check you haven't exceeded free tier limits (15 requests/minute)
- Ensure the API key is for the correct project

### "No articles found"
- Check if RSS feeds are accessible
- Verify keywords in sources.json match current news
- Try running manually during active news hours

---

## Success Checklist

- [ ] Google Cloud project created
- [ ] Google Sheets API enabled
- [ ] Google Drive API enabled
- [ ] Service account created
- [ ] JSON key downloaded
- [ ] Gemini API key created
- [ ] Google Sheet created with headers
- [ ] Sheet shared with service account
- [ ] GitHub repository created
- [ ] All three secrets added to GitHub
- [ ] Manual workflow run successful
- [ ] Articles appearing in Google Sheet

**Congratulations! Your newsletter pipeline is live!** 🎉
