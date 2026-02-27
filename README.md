# Funnel Filler

AI-powered SDR agent for outbound prospecting and lead qualification. Uses Claude to research leads, generate personalized outreach, handle responses, qualify prospects, and book meetings.

## What It Does

- **Lead Prospecting** — Find leads matching your Ideal Customer Profile via Apollo.io
- **Data Enrichment** — Enrich leads with email, phone, title, and company data from Apollo
- **AI Research** — Automatically research leads to find pain points and conversation angles
- **Lead Scoring** — Score leads 0-100 based on title fit, data completeness, and AI analysis
- **Email Outreach** — Generate and send personalized cold emails via Resend
- **LinkedIn Outreach** — Generate personalized LinkedIn connection requests and messages
- **Follow-up Sequences** — Automated multi-touch sequences with AI-generated follow-ups
- **Response Analysis** — Analyze prospect replies, detect sentiment, and recommend next actions
- **Lead Qualification** — Qualify leads based on engagement, intent, and fit signals
- **Meeting Booking** — Generate meeting request messages for qualified leads
- **Company Prospecting** — Find and score target companies, then discover contacts within them

## Setup

```bash
# Clone and install
git clone <repo-url>
cd Funnel-Filler
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your API keys and company info
```

### Requirements

- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/) (required)
- An [Apollo.io API key](https://www.apollo.io/) (required for prospecting and enrichment)
- A [Resend API key](https://resend.com/) (required for sending emails)

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for AI operations |
| `APOLLO_API_KEY` | For prospecting | Apollo.io key for lead discovery and enrichment |
| `RESEND_API_KEY` | For email | Resend key for sending outreach emails |
| `RESEND_FROM_EMAIL` | For email | Sender address (e.g., `Your Name <you@domain.com>`) |
| `COMPANY_NAME` | Recommended | Your company name (personalizes outreach) |
| `COMPANY_DESCRIPTION` | Recommended | What your company does |
| `SENDER_NAME` | Recommended | SDR's name |
| `SENDER_TITLE` | No | SDR's title (default: "Sales Development Representative") |
| `CALENDAR_LINK` | No | Calendly/Cal.com link for meeting booking |
| `DB_PATH` | No | SQLite database path (default: `funnel_filler.db`) |
| `ANTHROPIC_MODEL` | No | Claude model (default: `claude-sonnet-4-6`) |

---

## Quick Start: Full Pipeline

The fastest way to use Funnel Filler is the `lead-pipeline` command, which runs the entire process end-to-end:

```bash
# 1. Define your Ideal Customer Profile
funnel-filler set-icp \
  --titles "VP Sales,Head of Marketing,CRO" \
  --seniorities "director,vp,c_suite" \
  --industries "SaaS,FinTech" \
  --company-sizes "50,200;201,1000" \
  --locations "San Francisco,New York"

# 2. Run the full pipeline
funnel-filler lead-pipeline --count 10
```

This will:
1. **Prospect** — Find 10 leads matching your ICP via Apollo
2. **Enrich** — Pull additional data (email, phone, title) for each lead
3. **Research** — AI-generate a research brief for each lead
4. **Score** — Score each lead 0-100
5. **Generate LinkedIn messages** — Create personalized connection requests
6. **Open LinkedIn profiles** — One at a time, with the message copied to your clipboard

You then **paste and send each LinkedIn message manually** on LinkedIn.

To also send emails automatically:

```bash
funnel-filler lead-pipeline --count 10 --email --linkedin
```

---

## The Full Process: Step by Step

### Step 1: Configure Your ICP (Ideal Customer Profile)

Before prospecting, define who you're targeting:

```bash
funnel-filler set-icp \
  --name "default" \
  --titles "VP Sales,Head of Marketing,Director of Revenue" \
  --seniorities "director,vp,c_suite" \
  --industries "SaaS,B2B Software,FinTech" \
  --company-sizes "50,200;201,1000" \
  --locations "San Francisco,New York,Austin" \
  --keywords "AI,machine learning"
```

View your ICP:

```bash
funnel-filler show-icp --name "default"
```

> **Note:** Company sizes use semicolons to separate ranges (e.g., `50,200;201,1000` means "50-200 employees" and "201-1000 employees").

### Step 2: Find Leads

**Option A — Automated prospecting via Apollo:**

```bash
funnel-filler prospect --icp "default" --count 25
```

**Option B — Add leads manually:**

```bash
funnel-filler add "Jane Smith" \
  --email jane@acme.com \
  --company "Acme Corp" \
  --title "VP of Sales" \
  --industry "SaaS"
```

**Option C — Import from CSV:**

```bash
funnel-filler import-csv leads.csv
```

CSV format: `name,email,company,title,industry,linkedin_url,notes`

### Step 3: Enrich Leads

Pull additional data from Apollo (email, phone, LinkedIn URL, company info):

```bash
funnel-filler enrich <lead-id>
```

### Step 4: Research Leads

Generate an AI research brief with company summary, role analysis, pain points, and conversation starters:

```bash
funnel-filler research <lead-id>
```

### Step 5: Score Leads

Score leads 0-100 using AI analysis combined with rule-based signals:

```bash
funnel-filler score <lead-id>
```

Scoring factors:
- **AI analysis** — Claude evaluates fit based on research data
- **Title signals** — C-suite (+15), VP (+12), Director (+10), Manager (+5)
- **Data completeness** — Has email (+10), has LinkedIn (+5), has research (+5)

### Step 6: Send Outreach

**Email** (sent automatically via Resend):

```bash
funnel-filler send-email <lead-id>
```

**LinkedIn** (generated for you to send manually):

```bash
funnel-filler send-linkedin <lead-id> --message-type connect
```

This will:
1. Generate a personalized message (connection requests are capped at 300 characters)
2. Copy the message to your clipboard
3. Open the lead's LinkedIn profile in your browser
4. You paste the message and send it on LinkedIn

**Both channels at once:**

```bash
funnel-filler auto-outreach <lead-id> --email --linkedin
```

This enriches, researches, scores, sends email, and generates the LinkedIn message in one step.

### Step 7: Start Follow-up Sequences

Start an automated multi-touch sequence (5 touches over ~3 weeks):

```bash
funnel-filler sequence <lead-id>
```

Run any due follow-up steps:

```bash
funnel-filler run-sequences
```

### Step 8: Handle Replies

When a prospect responds, log and analyze their reply:

```bash
funnel-filler reply <lead-id> "Thanks for reaching out. We're looking at solutions like this..."
```

This will:
- Analyze sentiment and response category
- Score qualification (0-100)
- Recommend next action: `BOOK_MEETING`, `SEND_MORE_INFO`, `FOLLOW_UP`, `NURTURE`, or `DISQUALIFY`
- Automatically pause any active follow-up sequences

### Step 9: Book Meetings

For qualified leads, generate a meeting request:

```bash
funnel-filler meeting <lead-id> --channel email
```

---

## Automated Pipelines

### Lead Pipeline

Prospect, enrich, research, and outreach — all in one command:

```bash
funnel-filler lead-pipeline \
  --icp-name "default" \
  --count 10 \
  --email \
  --linkedin
```

At the end, the pipeline will display a summary and iterate through LinkedIn-ready leads, copying each message to your clipboard and opening each profile for you to send.

### Organization Pipeline

Start from companies, then find contacts within each:

```bash
funnel-filler org-pipeline \
  --icp-name "default" \
  --count 5 \
  --contacts 3 \
  --email \
  --linkedin
```

This will:
1. Prospect 5 companies matching your ICP
2. Enrich and score each company
3. Find up to 3 contacts at each company
4. Enrich, research, and score each contact
5. Send emails and generate LinkedIn messages

---

## Pipeline & Lead Management

```bash
# View pipeline summary (lead counts by status)
funnel-filler pipeline

# View company pipeline summary
funnel-filler company-pipeline

# List all leads
funnel-filler list

# Filter by status
funnel-filler list --status qualified

# View lead details
funnel-filler show <lead-id>

# Search leads
funnel-filler search "acme"
```

### Lead Statuses

| Status | Meaning |
|--------|---------|
| `new` | Just added to the system |
| `researching` | Being enriched or researched |
| `outreach_pending` | Research complete, ready for outreach |
| `contacted` | Outreach sent |
| `replied` | Prospect responded |
| `qualified` | Meets criteria for a meeting |
| `meeting_booked` | Meeting scheduled |
| `disqualified` | Not a fit |
| `unresponsive` | No reply after follow-up sequences |

---

## Company Management

```bash
# Add a company manually
funnel-filler add-company "Acme Inc" \
  --domain "acme.com" \
  --industry "SaaS" \
  --employees 250 \
  --location "San Francisco, CA"

# Prospect companies via Apollo
funnel-filler prospect-companies --icp "default" --count 10

# Enrich and score
funnel-filler enrich-company <company-id>
funnel-filler score-company <company-id>

# List and search
funnel-filler list-companies
funnel-filler list-companies --status enriched
funnel-filler search-companies "acme"
funnel-filler show-company <company-id>
```

---

## Understanding "LinkedIn Ready"

When the pipeline shows a lead as **"LinkedIn ready"**, it means:

1. A personalized LinkedIn message has been **generated and saved** to the database
2. The message has **not been sent** — there is no automated LinkedIn sending
3. After the pipeline completes, the tool will **copy the message to your clipboard** and **open the lead's LinkedIn profile** in your browser
4. You **paste and send the message manually** on LinkedIn

LinkedIn does not provide an API for sending connection requests or DMs, so this manual step is required to stay within LinkedIn's terms of service.

To send a LinkedIn message for a specific lead later:

```bash
funnel-filler send-linkedin <lead-id> --message-type connect
```

---

## Complete Command Reference

### Lead Management
| Command | Description |
|---------|-------------|
| `add <name>` | Add a single lead (`--email`, `--company`, `--title`, `--industry`) |
| `import-csv <file>` | Import leads from CSV |
| `list` | List all leads (`--status` to filter) |
| `show <id>` | Show detailed lead info |
| `search <query>` | Search by name, company, email, or title |

### ICP & Prospecting
| Command | Description |
|---------|-------------|
| `set-icp` | Define Ideal Customer Profile |
| `show-icp` | Display ICP (`--name` to specify) |
| `prospect` | Find leads via Apollo (`--icp`, `--count`, `--page`) |
| `prospect-companies` | Find companies via Apollo |

### Enrichment & Research
| Command | Description |
|---------|-------------|
| `enrich <id>` | Enrich lead with Apollo data |
| `enrich-company <id>` | Enrich company with Apollo data |
| `research <id>` | AI-generate research brief |
| `score <id>` | Score lead 0-100 |
| `score-company <id>` | Score company 0-100 |

### Outreach
| Command | Description |
|---------|-------------|
| `outreach <id>` | Generate outreach message (`--channel email\|linkedin`) |
| `send-email <id>` | Generate and send email via Resend |
| `send-linkedin <id>` | Generate LinkedIn message (`--message-type connect\|message`) |
| `auto-outreach <id>` | Full outreach pipeline for one lead (`--email`, `--linkedin`) |

### Sequences & Responses
| Command | Description |
|---------|-------------|
| `sequence <id>` | Start follow-up sequence (5 touches, ~3 weeks) |
| `run-sequences` | Execute any due sequence steps |
| `reply <id> <text>` | Log and analyze prospect reply |
| `meeting <id>` | Generate meeting request (`--channel`) |

### Pipelines
| Command | Description |
|---------|-------------|
| `lead-pipeline` | Full pipeline: prospect → enrich → research → outreach |
| `org-pipeline` | Company pipeline: companies → contacts → outreach |
| `pipeline` | View lead pipeline summary |
| `company-pipeline` | View company pipeline summary |

### Company Management
| Command | Description |
|---------|-------------|
| `add-company <name>` | Add company (`--domain`, `--industry`, `--employees`, `--location`) |
| `list-companies` | List companies (`--status` to filter) |
| `show-company <id>` | Show company details |
| `search-companies <query>` | Search companies |

---

## Project Structure

```
sdr_agent/
├── __init__.py              # Package init
├── agent.py                 # Main SDR agent orchestrator
├── cli.py                   # CLI interface (Typer)
├── config.py                # Configuration from environment
├── models.py                # Data models (Lead, Message, Sequence, Company, ICP)
├── storage.py               # SQLite persistence layer
├── modules/
│   ├── enricher.py          # Lead enrichment via Apollo.io
│   ├── company_enricher.py  # Company enrichment via Apollo.io
│   ├── prospector.py        # Lead prospecting via Apollo.io
│   ├── company_prospector.py # Company prospecting via Apollo.io
│   ├── researcher.py        # AI lead research
│   ├── scorer.py            # AI + rule-based lead scoring
│   ├── company_scorer.py    # Company scoring
│   ├── outreach.py          # AI email outreach generation
│   ├── linkedin_outreach.py # AI LinkedIn message generation
│   ├── resend_sender.py     # Email delivery via Resend API
│   ├── qualifier.py         # Response analysis & lead qualification
│   ├── scheduler.py         # Meeting scheduling
│   └── sequencer.py         # Follow-up sequence automation
└── templates/               # (future) message templates
```

## Data Storage

All data is stored in a local SQLite database (`funnel_filler.db` by default). Tables:

- **leads** — Contact records with status, score, research data, and tags
- **messages** — All generated/sent messages (email and LinkedIn)
- **sequences** — Follow-up sequence state and progress
- **icps** — Saved Ideal Customer Profiles
- **companies** — Target company records

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```
