# Funnel Filler

AI-powered SDR agent for outbound prospecting and lead qualification. Uses Claude to research leads, generate personalized outreach, handle responses, qualify prospects, and book meetings.

## What It Does

- **Lead Management** — Add leads manually or import from CSV, track them through your pipeline
- **AI Research** — Automatically research leads to find pain points and conversation angles
- **Personalized Outreach** — Generate cold emails tailored to each prospect's role, company, and industry
- **Follow-up Sequences** — Automated multi-touch sequences with AI-generated follow-ups
- **Response Analysis** — Analyze prospect replies, detect sentiment, and recommend next actions
- **Lead Qualification** — Score leads 0-100 based on fit, engagement, and intent signals
- **Meeting Booking** — Generate meeting request messages for qualified leads

## Setup

```bash
# Clone and install
git clone <repo-url>
cd Funnel-Filler
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your Anthropic API key and company info
```

### Required

- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/)

## Usage

### Add leads

```bash
# Add a single lead
funnel-filler add "Jane Smith" \
  --email jane@acme.com \
  --company "Acme Corp" \
  --title "VP of Sales" \
  --industry "SaaS"

# Import from CSV
funnel-filler import-csv leads.csv
```

CSV format: `name,email,company,title,industry,linkedin_url,notes`

### Research a lead

```bash
funnel-filler research <lead-id>
```

This uses AI to generate a research brief with company summary, role analysis, likely pain points, and conversation starters.

### Generate outreach

```bash
# Generate a personalized cold email
funnel-filler outreach <lead-id>

# Start an automated follow-up sequence (5 touches over 3 weeks)
funnel-filler sequence <lead-id>

# Run any due follow-up steps
funnel-filler run-sequences
```

### Handle responses

```bash
# Process a prospect's reply
funnel-filler reply <lead-id> "Thanks for reaching out. We're actually looking at solutions like this..."
```

This analyzes sentiment, qualifies the lead, and recommends the next action (book meeting, follow up, send more info, etc.).

### Book meetings

```bash
funnel-filler meeting <lead-id>
```

### View your pipeline

```bash
# Pipeline summary
funnel-filler pipeline

# List all leads (optionally filter by status)
funnel-filler list
funnel-filler list --status qualified

# View lead details
funnel-filler show <lead-id>

# Search leads
funnel-filler search "acme"
```

## Full Workflow Example

```bash
# 1. Add a lead
funnel-filler add "Sarah Chen" \
  --email sarah@techstartup.io \
  --company "TechStartup" \
  --title "Head of Growth" \
  --industry "B2B SaaS"

# 2. Research them
funnel-filler research <lead-id>

# 3. Generate personalized outreach
funnel-filler outreach <lead-id>

# 4. Start automated follow-ups
funnel-filler sequence <lead-id>

# 5. When they reply, analyze it
funnel-filler reply <lead-id> "Interesting, can you tell me more?"

# 6. If qualified, book a meeting
funnel-filler meeting <lead-id>

# 7. Check your pipeline
funnel-filler pipeline
```

## Project Structure

```
sdr_agent/
├── __init__.py          # Package init
├── agent.py             # Main orchestrator
├── cli.py               # CLI interface
├── config.py            # Configuration management
├── models.py            # Data models (Lead, Message, Sequence)
├── storage.py           # SQLite persistence layer
├── modules/
│   ├── outreach.py      # AI outreach generation
│   ├── qualifier.py     # Lead qualification & response analysis
│   ├── researcher.py    # Lead research & enrichment
│   ├── scheduler.py     # Meeting scheduling
│   └── sequencer.py     # Follow-up sequence automation
└── templates/           # (future) message templates
```

## Configuration

All settings are loaded from environment variables (see `.env.example`):

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key |
| `COMPANY_NAME` | No | Your company name (for outreach) |
| `COMPANY_DESCRIPTION` | No | What your company does |
| `SENDER_NAME` | No | SDR's name |
| `SENDER_TITLE` | No | SDR's title |
| `CALENDAR_LINK` | No | Calendly/Cal.com link for booking |
| `SMTP_*` | No | SMTP settings for sending emails |

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```
