# Linkedin Scrapper
A powerful web-based LinkedIn profile scraper built with Flask and
Playwright. Extract professional profiles, search for people, and export
data in JSON/CSV formats with session management and stealth browser
automation.


# Features

-   **Advanced Search** - Search LinkedIn profiles by first name, last
    name, and company

-   **Profile Extraction** - Extract complete profile data including
    experience, education, skills, certifications, and more

-   **Session Management** - Save and restore login sessions to avoid
    repeated authentication

-   **Stealth Mode** - Browser automation with anti-detection measures

-   **Multiple Export Formats** - Export data as JSON or CSV

-   **Web Interface** - User-friendly web UI with real-time progress
    updates

-   **Bulk Processing** - Search and extract multiple profiles in one go

-   **Secure** - Credentials are never stored; only session cookies are
    saved locally

# Tech Stack

-   **Backend**: Flask (Python)

-   **Browser Automation**: Playwright (async)

-   **Frontend**: HTML5, CSS3, JavaScript (vanilla)

-   **Data Export**: JSON, CSV

-   **Session Storage**: Pickle

# Prerequisites

-   Python 3.8+

-   Playwright browsers (installed automatically)

-   LinkedIn account

# Installation

## 1. Clone the Repository

``` {.bash language="bash"}
git clone https://github.com/yourusername/linkedin-profile-scraper.git
cd linkedin-profile-scraper
```

## 2. Install Dependencies

``` {.bash language="bash"}
pip install -r req.txt
```

## 3. Install Playwright Browsers

``` {.bash language="bash"}
playwright install chromium
```

## 4. Run the Application

``` {.bash language="bash"}
python app.py
```

The server will start at `http://localhost:5000`

# Project Structure

``` {.bash language="bash" basicstyle="\\ttfamily\\footnotesize"}
linkedin-scraper/
├── app.py                 # Flask web server and API endpoints
├── core.py                # LinkedIn scraper core logic
├── llm_parser.py          # AI-powered profile parser (optional)
├── session_manager.py     # Session persistence manager
├── req.txt                # Python dependencies
├── templates/
│   └── index.html         # Web UI
├── sessions/              # Saved session cookies (auto-created)
└── exports/               # Exported data storage (auto-created)
```

# API Endpoints

  **Endpoint**                      **Method**   **Description**
  --------------------------------- ------------ ------------------------------------
  /                                 GET          Web interface
  /api/scraper/init                 POST         Initialize browser
  /api/scraper/login                POST         Login to LinkedIn
  /api/scraper/search               POST         Search for people
  /api/scraper/extract              POST         Extract single profile
  /api/scraper/search-and-extract   POST         Search & extract multiple profiles
  /api/scraper/stats                GET          Get scraper statistics
  /api/scraper/export               POST         Export collected data
  /api/scraper/close                POST         Close browser

# Usage Guide

## 1. Initialize Browser

Click \"Initialize Browser\" to start a browser instance. Choose
between:

-   **Headless Mode**: Run in background (faster, no UI)

-   **Visible Mode**: See browser actions (helpful for debugging)

## 2. Login to LinkedIn

Enter your LinkedIn credentials and click \"Login\". The session will be
saved for future use.

## 3. Search for Profiles

-   Enter first name and last name (required)

-   Optional: Add company name for more specific search

-   Set maximum number of results (1-50)

## 4. Extract Profile Data

**Option A - Quick Extract**: Paste a profile URL directly

**Option B - Search & Extract**:

-   Perform search and automatically extract data from found profiles

-   Results include: name, headline, location, about, experience,
    education, skills

## 5. Export Data

Export extracted profiles as:

-   **JSON**: Complete raw data with all fields

-   **CSV**: Tabular format with key fields for spreadsheet analysis

# Data Extracted

  **Field**        **Description**
  ---------------- ------------------------------------------------------
  name             Full name
  headline         Current position/title
  location         Geographic location
  about            Summary/about section
  experiences      Work history (title, company, duration, description)
  education        Academic background
  skills           Listed skills
  featured         Featured content
  certifications   Professional certifications
  profile_url      LinkedIn profile URL
  scraped_at       Extraction timestamp

# Configuration

## Session Management

Sessions are saved in the `sessions/` directory. To reuse a session:

    scraper = LinkedInScraper(session_name="my_session")

## Browser Type

Available browser types: `chromium` (default), `firefox`

    scraper = LinkedInScraper(browser_type="firefox")

## Headless Mode

    scraper = LinkedInScraper(headless=True)  # Run without UI

# Error Handling

Common issues and solutions:

  **Issue**               **Solution**
  ----------------------- ------------------------------------------------------------
  Login fails             Check credentials, complete security verification manually
  No profiles found       Verify name spelling, try without company filter
  Extraction incomplete   Ensure profile is public or you're connected
  Session expired         Re-login to refresh session

# Legal & Ethical Considerations

# Performance Tips

-   Use session saving to avoid repeated logins

-   Run in headless mode for faster operation

-   Add delays between requests (built-in randomization)

-   Keep `max_results` reasonable (10-20 per search)

-   Close browser when done to free resources

# Troubleshooting

## Browser fails to launch

``` {.bash language="bash"}
playwright install --force chromium
```

## Module not found errors

``` {.bash language="bash"}
pip install -r req.txt --upgrade
```

## LinkedIn blocks requests

-   Add longer delays between requests

-   Use the session feature to maintain consistent identity

-   Avoid running multiple instances simultaneously

# Future Enhancements

-   Proxy rotation support

-   Multi-threaded extraction

-   Export to Excel format

-   Scheduled scraping tasks

-   Email notifications

-   PDF profile export

# License

MIT License - Use at your own risk. The authors assume no liability for
misuse.

# Disclaimer

This project is not affiliated with, authorized by, or endorsed by
LinkedIn Corporation. LinkedIn is a registered trademark of LinkedIn
Corporation.

**Happy Scraping!** 🚀
