# African AI Governance Newsletter - Automated Pipeline

A free, automated system to scrape, classify, and curate AI governance news from Africa and Africa-related sources.

## 🎯 What This Does

- **Scrapes** 30+ African tech and AI governance sources 3x daily (5am, 2pm, 9pm Cairo time)
- **Extracts** only metadata: Title, URL, Publication, Date
- **Classifies** content using Google Gemini AI (free tier)
- **Stores** everything in Google Sheets (free)
- **Presents** a review dashboard for you to add expert commentary

## 💰 Cost: $0/month

| Service | Free Limit | Your Usage |
|---------|------------|------------|
| GitHub Actions | 2,000 mins/month | ~90 mins |
| Google Gemini API | 15 RPM, 1M tokens/day | ~100 requests/day |
| Google Sheets | Unlimited | ~3,000 rows/month |
| Substack | Unlimited subscribers | N/A |

---

## 📋 Setup Instructions

### Step 1: Google Cloud Setup (15 minutes)

#### 1.1 Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown at the top → **New Project**
3. Name it: `ai-governance-newsletter`
4. Click **Create**
5. Wait for project creation, then select it from the dropdown

#### 1.2 Enable Required APIs

1. Go to **APIs & Services** → **Library**
2. Search for **Google Sheets API** → Click → **Enable**
3. Search for **Google Drive API** → Click → **Enable**

#### 1.3 Create Service Account

1. Go to **APIs & Services** → **Credentials**
2. Click **+ CREATE CREDENTIALS** → **Service account**
3. Fill in:
   - Service account name: `newsletter-bot`
   - Service account ID: (auto-fills)
   - Description: `Automated newsletter scraper`
4. Click **Create and Continue**
5. Skip the optional steps → Click **Done**

#### 1.4 Generate JSON Key

1. Click on your new service account (newsletter-bot@...)
2. Go to **Keys** tab
3. Click **Add Key** → **Create new key**
4. Select **JSON** → Click **Create**
5. **Save this file securely** - you'll need the contents for GitHub Secrets

#### 1.5 Get Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click **Create API Key**
3. Select your project
4. Copy and save the API key

---

### Step 2: Google Sheet Setup (5 minutes)

#### 2.1 Create the Sheet

1. Go to [Google Sheets](https://sheets.google.com)
2. Create a new blank spreadsheet
3. Name it: `AI Governance Newsletter Database`

#### 2.2 Add Headers

Copy these headers into Row 1 (A1 to L1):

```
Title | URL | Publication | Date Published | Primary Category | Sub-Category | Geography | Relevance Score | Africa Related | Date Scraped | Review Status | Your Commentary
```

#### 2.3 Share with Service Account

1. Click **Share** button (top right)
2. Paste your service account email (from Step 1.3, looks like: `newsletter-bot@ai-governance-newsletter.iam.gserviceaccount.com`)
3. Set permission to **Editor**
4. Uncheck "Notify people"
5. Click **Share**

#### 2.4 Get Sheet ID

From your spreadsheet URL:
```
https://docs.google.com/spreadsheets/d/[THIS_IS_YOUR_SHEET_ID]/edit
```
Copy the Sheet ID portion.

#### 2.5 Add Data Validation (Optional but Recommended)

1. Select Column K (Review Status)
2. Go to **Data** → **Data validation**
3. Add rule: **Dropdown from a list**
4. Values: `Pending, Selected, Rejected`

5. Add Conditional Formatting:
   - Select Column H (Relevance Score)
   - Format → Conditional formatting
   - Add rules for: 8-10 (green), 5-7 (yellow), 1-4 (red)

---

### Step 3: GitHub Repository Setup (10 minutes)

#### 3.1 Create Repository

1. Go to [GitHub](https://github.com) and sign in
2. Click **+** → **New repository**
3. Name: `african-ai-governance-newsletter`
4. Make it **Private** (recommended)
5. Click **Create repository**

#### 3.2 Upload Files

Upload all files from this package to your repository, maintaining the folder structure:

```
african-ai-governance-newsletter/
├── .github/
│   └── workflows/
│       └── scrape.yml
├── src/
│   ├── scraper.py
│   ├── classifier.py
│   ├── sheets_handler.py
│   └── sources.json
├── requirements.txt
└── README.md
```

#### 3.3 Add GitHub Secrets

1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret** for each:

| Secret Name | Value |
|-------------|-------|
| `GEMINI_API_KEY` | Your Gemini API key from Step 1.5 |
| `GOOGLE_SHEETS_CREDS` | **Entire contents** of the JSON key file from Step 1.4 |
| `SHEET_ID` | Your Sheet ID from Step 2.4 |

---

### Step 4: Test the Pipeline (2 minutes)

1. Go to your repo → **Actions** tab
2. Click on **Scrape AI Governance News**
3. Click **Run workflow** → **Run workflow**
4. Wait ~2 minutes for completion
5. Check your Google Sheet for new entries!

---

## 🔧 Customization

### Adjust Scrape Times

Edit `.github/workflows/scrape.yml`:

```yaml
schedule:
  # Currently set for Cairo time (UTC+2)
  - cron: '0 3 * * *'   # 5:00 AM Cairo
  - cron: '0 12 * * *'  # 2:00 PM Cairo  
  - cron: '0 19 * * *'  # 9:00 PM Cairo
```

### Add More Sources

Edit `src/sources.json` to add RSS feeds or keywords.

### Adjust Relevance Threshold

Edit `src/scraper.py`, line with:
```python
if classification and classification.get('relevance_score', 0) >= 5:
```
Change `5` to your preferred minimum score.

---

## 📊 Your Daily Workflow

1. **Morning** (after 9pm scrape): Open Google Sheet
2. **Filter**: Show only `Relevance ≥ 7` and `Status = Pending`
3. **Review**: Click URLs to read promising articles
4. **Select**: Change status to `Selected` for newsletter items
5. **Comment**: Add your expert commentary in Column L
6. **Publish**: Copy selected items to Substack/LinkedIn

---

## 🛠 Troubleshooting

### "No new articles found"
- Check if sources are returning valid RSS
- Verify keywords in `sources.json` match current news

### "Authentication failed"
- Verify `GOOGLE_SHEETS_CREDS` contains the full JSON (including curly braces)
- Confirm the Sheet is shared with the service account email

### "Gemini API error"
- Check you haven't exceeded free tier limits
- Verify API key is correct in secrets

---

## 📈 Future Enhancements

Once you've validated the concept:
- [ ] Add email automation via Substack API
- [ ] Integrate LinkedIn posting
- [ ] Add more specialized sources
- [ ] Build a simple web dashboard

---

## 📝 License

MIT License - Use freely for your newsletter!

---

Built for Wulo's African AI Governance Newsletter 🌍

## Reliability and validation

The classifier uses the supported `google-genai` SDK and defaults to
`gemini-3.5-flash-lite`. Set the repository Actions variable `GEMINI_MODEL`
to override it when migrating models. Existing API credentials stay in secrets.

Run regression tests with `python -m unittest discover -s tests -v`.
`python src/healthcheck.py` checks Sheets read access, one Gemini classification,
and RSS availability without writing rows. The validation workflow runs this
check and an end-to-end smoke scrape of up to three real candidates on trusted
pushes; pull requests only run tests without secrets. Smoke scrapes can save
qualifying real articles to the existing sheet.

Production runs fail on Sheet reads, classification/save errors, or total feed
failure. Feed requests have timeouts and run with eight workers. Individual
broken feeds are reported while working feeds continue. Metadata is written
as literal text, preserving the existing 12-column sheet structure.

GitHub disables scheduled workflows in public repositories after 60 days of
repository inactivity. After successful production runs, an isolated job records a monthly health
checkpoint in `.github/scraper-health.json`. This provides repository activity
to prevent the same inactivity shutdown. Only that job needs contents write
permission. Review Actions failures and keep the configured model supported.
The schedule uses `Africa/Cairo` to preserve 5am, 2pm and 9pm across DST.
