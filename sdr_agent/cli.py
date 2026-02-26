"""Command-line interface for the Funnel Filler SDR agent."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .agent import SDRAgent
from .models import Channel, CompanyStatus, LeadStatus

app = typer.Typer(
    name="funnel-filler",
    help="AI-powered SDR agent for outbound prospecting and lead qualification.",
)
console = Console()


def _get_agent() -> SDRAgent:
    return SDRAgent()


# -- Lead Commands --

@app.command()
def add(
    name: str = typer.Argument(..., help="Lead's full name"),
    email: str = typer.Option("", help="Email address"),
    company: str = typer.Option("", help="Company name"),
    title: str = typer.Option("", help="Job title"),
    industry: str = typer.Option("", help="Industry"),
    linkedin: str = typer.Option("", help="LinkedIn profile URL"),
    notes: str = typer.Option("", help="Additional notes"),
):
    """Add a new lead to the pipeline."""
    agent = _get_agent()
    lead = agent.add_lead(name, email, company, title, industry, linkedin, notes)
    console.print(f"[green]Added lead:[/green] {lead.name} ({lead.id})")
    agent.close()


@app.command()
def import_csv(
    path: str = typer.Argument(..., help="Path to CSV file"),
):
    """Import leads from a CSV file."""
    agent = _get_agent()
    leads = agent.import_leads_from_csv(path)
    console.print(f"[green]Imported {len(leads)} leads[/green]")
    agent.close()


@app.command(name="list")
def list_leads(
    status: str = typer.Option("", help="Filter by status (new, contacted, qualified, etc.)"),
):
    """List all leads in the pipeline."""
    agent = _get_agent()
    lead_status = LeadStatus(status) if status else None
    leads = agent.list_leads(lead_status)

    if not leads:
        console.print("[dim]No leads found.[/dim]")
        agent.close()
        return

    table = Table(title="Leads Pipeline")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Company")
    table.add_column("Title")
    table.add_column("Status")
    table.add_column("Score", justify="right")

    status_colors = {
        "new": "white",
        "researching": "cyan",
        "outreach_pending": "yellow",
        "contacted": "blue",
        "replied": "green",
        "qualified": "bold green",
        "meeting_booked": "bold magenta",
        "disqualified": "red",
        "unresponsive": "dim",
    }

    for lead in leads:
        color = status_colors.get(lead.status.value, "white")
        table.add_row(
            lead.id,
            lead.name,
            lead.company,
            lead.title,
            f"[{color}]{lead.status.value}[/{color}]",
            str(lead.score),
        )

    console.print(table)
    agent.close()


@app.command()
def search(query: str = typer.Argument(..., help="Search query")):
    """Search leads by name, company, email, or title."""
    agent = _get_agent()
    leads = agent.search_leads(query)
    if not leads:
        console.print("[dim]No leads found.[/dim]")
    else:
        for lead in leads:
            console.print(f"  {lead.id}  {lead.name} @ {lead.company} — [{lead.status.value}]")
    agent.close()


# -- Prospecting Commands --

@app.command(name="set-icp")
def set_icp(
    name: str = typer.Option("default", help="Name for this ICP profile"),
    titles: str = typer.Option("", help="Job titles, comma-separated (e.g. 'VP Sales,Head of Marketing')"),
    seniorities: str = typer.Option("", help="Seniority levels, comma-separated (e.g. 'director,vp,c_suite')"),
    industries: str = typer.Option("", help="Industries, comma-separated (e.g. 'SaaS,FinTech')"),
    company_sizes: str = typer.Option("", help="Employee ranges, comma-separated (e.g. '1,50;51,200;201,1000')"),
    locations: str = typer.Option("", help="Locations, comma-separated (e.g. 'San Francisco,New York')"),
    keywords: str = typer.Option("", help="Keywords, comma-separated (e.g. 'AI,machine learning')"),
):
    """Define your Ideal Customer Profile for automated prospecting."""
    agent = _get_agent()

    def split(val: str) -> list[str]:
        return [v.strip() for v in val.split(",") if v.strip()] if val else []

    # Company sizes use semicolons as delimiters since ranges contain commas
    size_list = [v.strip() for v in company_sizes.split(";")] if company_sizes else []

    icp = agent.set_icp(
        name=name,
        titles=split(titles),
        seniorities=split(seniorities),
        industries=split(industries),
        company_sizes=size_list,
        locations=split(locations),
        keywords=split(keywords),
    )

    console.print(Panel(f"[bold]{icp.name}[/bold]", title="ICP Saved"))
    if icp.titles:
        console.print(f"  [cyan]Titles:[/cyan] {', '.join(icp.titles)}")
    if icp.seniorities:
        console.print(f"  [cyan]Seniorities:[/cyan] {', '.join(icp.seniorities)}")
    if icp.industries:
        console.print(f"  [cyan]Industries:[/cyan] {', '.join(icp.industries)}")
    if icp.company_sizes:
        console.print(f"  [cyan]Company sizes:[/cyan] {', '.join(icp.company_sizes)}")
    if icp.locations:
        console.print(f"  [cyan]Locations:[/cyan] {', '.join(icp.locations)}")
    if icp.keywords:
        console.print(f"  [cyan]Keywords:[/cyan] {', '.join(icp.keywords)}")

    console.print("\n[dim]Run 'funnel-filler prospect' to find matching leads.[/dim]")
    agent.close()


@app.command(name="show-icp")
def show_icp(
    name: str = typer.Option("default", help="ICP profile name"),
):
    """Show the current Ideal Customer Profile."""
    agent = _get_agent()
    icp = agent.get_icp(name)

    if not icp:
        console.print(f"[yellow]No ICP named '{name}' found.[/yellow]")
        console.print("[dim]Create one with 'funnel-filler set-icp'.[/dim]")
        agent.close()
        return

    console.print(Panel(f"[bold]{icp.name}[/bold]", title="Ideal Customer Profile"))
    if icp.titles:
        console.print(f"  [cyan]Titles:[/cyan] {', '.join(icp.titles)}")
    if icp.seniorities:
        console.print(f"  [cyan]Seniorities:[/cyan] {', '.join(icp.seniorities)}")
    if icp.industries:
        console.print(f"  [cyan]Industries:[/cyan] {', '.join(icp.industries)}")
    if icp.company_sizes:
        console.print(f"  [cyan]Company sizes:[/cyan] {', '.join(icp.company_sizes)}")
    if icp.locations:
        console.print(f"  [cyan]Locations:[/cyan] {', '.join(icp.locations)}")
    if icp.keywords:
        console.print(f"  [cyan]Keywords:[/cyan] {', '.join(icp.keywords)}")
    agent.close()


@app.command()
def prospect(
    icp_name: str = typer.Option("default", "--icp", help="ICP profile to use"),
    count: int = typer.Option(25, help="Number of prospects to find (max 100)"),
    page: int = typer.Option(1, help="Page number for pagination"),
):
    """Find new leads matching your ICP via Apollo."""
    agent = _get_agent()
    with console.status("Searching Apollo for prospects..."):
        leads = agent.prospect(icp_name, count=min(count, 100), page=page)

    if not leads:
        console.print("[yellow]No new prospects found (or all matches are already in your pipeline).[/yellow]")
        agent.close()
        return

    table = Table(title=f"Found {len(leads)} New Prospects")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Title")
    table.add_column("Company")
    table.add_column("Email")

    for lead in leads:
        table.add_row(lead.id, lead.name, lead.title, lead.company, lead.email)

    console.print(table)
    console.print(f"\n[green]{len(leads)} leads added to pipeline.[/green]")
    console.print("[dim]Use 'funnel-filler enrich <id>' or 'funnel-filler research <id>' to learn more.[/dim]")
    agent.close()


# -- Scoring Commands --

@app.command()
def score(lead_id: str = typer.Argument(..., help="Lead ID to score")):
    """Score a lead using AI analysis + rule-based adjustments (0-100)."""
    agent = _get_agent()
    with console.status("Scoring lead..."):
        result = agent.score_lead(lead_id)

    lead = agent.get_lead(lead_id)
    name = lead.name if lead else lead_id

    # Score color
    s = result["score"]
    if s >= 80:
        color = "bold green"
    elif s >= 60:
        color = "green"
    elif s >= 40:
        color = "yellow"
    else:
        color = "red"

    console.print(Panel(
        f"[{color}]{s}/100[/{color}]  (AI: {result['ai_score']} + Rules: {result['rule_adjustment']:+d})",
        title=f"Score for {name}",
    ))

    if result.get("reasoning"):
        console.print(f"\n[bold]Reasoning:[/bold] {result['reasoning']}")

    if result.get("strengths"):
        console.print("\n[bold]Strengths:[/bold]")
        for item in result["strengths"]:
            console.print(f"  [green]+[/green] {item}")

    if result.get("concerns"):
        console.print("\n[bold]Concerns:[/bold]")
        for item in result["concerns"]:
            console.print(f"  [red]-[/red] {item}")

    if result.get("rule_details"):
        console.print("\n[bold]Rule adjustments:[/bold]")
        for rule in result["rule_details"]:
            sign = "+" if rule["points"] > 0 else ""
            console.print(f"  [dim]{sign}{rule['points']}[/dim] {rule['rule']}")

    agent.close()


# -- Enrichment Commands --

@app.command()
def enrich(lead_id: str = typer.Argument(..., help="Lead ID to enrich")):
    """Enrich a lead with real data from Apollo.io (email, title, company info, etc.)."""
    agent = _get_agent()
    with console.status("Enriching lead via Apollo..."):
        lead, updated = agent.enrich_lead(lead_id)

    if not updated:
        console.print(f"[yellow]No new data found for {lead.name}.[/yellow]")
        console.print("[dim]Tip: ensure the lead has a name + company or email for best results.[/dim]")
        agent.close()
        return

    console.print(Panel(f"[bold]{lead.name}[/bold] @ {lead.company}", title="Enrichment Complete"))

    # Show updated core fields
    core_fields = {k: v for k, v in updated.items() if k != "apollo_data"}
    if core_fields:
        console.print("[bold]Updated fields:[/bold]")
        for field_name, value in core_fields.items():
            console.print(f"  [green]{field_name}:[/green] {value}")

    # Show extra Apollo data
    apollo_data = updated.get("apollo_data", {})
    if apollo_data:
        console.print("\n[bold]Additional data from Apollo:[/bold]")
        for key, value in apollo_data.items():
            if key == "organization":
                console.print(f"  [cyan]organization:[/cyan]")
                for org_key, org_val in value.items():
                    console.print(f"    [dim]{org_key}:[/dim] {org_val}")
            else:
                console.print(f"  [cyan]{key}:[/cyan] {value}")

    # Show auto-score if it ran
    auto_score = updated.get("auto_score")
    if auto_score:
        s = auto_score["score"]
        console.print(f"\n[bold]Auto-score:[/bold] {s}/100 — {auto_score.get('reasoning', '')}")

    agent.close()


# -- Research & Outreach Commands --

@app.command()
def research(lead_id: str = typer.Argument(..., help="Lead ID to research")):
    """Research a lead and enrich their profile with AI."""
    agent = _get_agent()
    with console.status("Researching lead..."):
        lead = agent.research_lead(lead_id)

    console.print(Panel(f"[bold]{lead.name}[/bold] @ {lead.company}", title="Research Complete"))
    for key, value in lead.research.items():
        console.print(f"  [cyan]{key}:[/cyan] {value}")
    agent.close()


@app.command()
def outreach(
    lead_id: str = typer.Argument(..., help="Lead ID"),
    channel: str = typer.Option("email", help="Channel: email or linkedin"),
):
    """Generate a personalized outreach message for a lead."""
    agent = _get_agent()
    ch = Channel.EMAIL if channel == "email" else Channel.LINKEDIN

    with console.status("Generating outreach..."):
        message = agent.generate_outreach(lead_id, ch)

    console.print(Panel(
        f"[bold]Subject:[/bold] {message.subject}\n\n{message.body}",
        title=f"Outreach for {lead_id}",
        border_style="green",
    ))
    agent.close()


@app.command()
def sequence(lead_id: str = typer.Argument(..., help="Lead ID")):
    """Start an automated follow-up sequence for a lead."""
    agent = _get_agent()
    seq_id = agent.start_sequence(lead_id)
    console.print(f"[green]Started sequence {seq_id} for lead {lead_id}[/green]")
    console.print("[dim]Run 'funnel-filler run-sequences' to execute due steps.[/dim]")
    agent.close()


@app.command(name="run-sequences")
def run_sequences():
    """Check and execute all due follow-up sequence steps."""
    agent = _get_agent()
    with console.status("Running sequences..."):
        results = agent.run_sequences()

    if not results:
        console.print("[dim]No sequences due right now.[/dim]")
    else:
        for lead, message in results:
            console.print(f"[green]Sent to {lead.name}:[/green] {message.subject}")
    agent.close()


# -- Send Outreach Commands --

@app.command(name="send-email")
def send_email(lead_id: str = typer.Argument(..., help="Lead ID to email")):
    """Generate and send a personalized outreach email via Resend."""
    agent = _get_agent()
    with console.status("Generating and sending email via Resend..."):
        result = agent.send_email(lead_id)

    message = result["message"]
    console.print(Panel(
        f"[bold]To:[/bold] {result['sent_to']}\n"
        f"[bold]Subject:[/bold] {message.subject}\n\n"
        f"{message.body}",
        title="Email Sent via Resend",
        border_style="green",
    ))
    console.print(f"\n[green]Sent![/green] Resend ID: {result['resend_id']}")
    agent.close()


@app.command(name="send-linkedin")
def send_linkedin(
    lead_id: str = typer.Argument(..., help="Lead ID"),
    message_type: str = typer.Option(
        "connect", help="Type: 'connect' for connection request, 'message' for DM"
    ),
):
    """Generate a LinkedIn outreach message for a lead."""
    agent = _get_agent()
    with console.status("Generating LinkedIn message..."):
        message = agent.send_linkedin(lead_id, message_type)

    lead = agent.get_lead(lead_id)
    name = lead.name if lead else lead_id
    linkedin_url = lead.linkedin_url if lead else ""

    if message_type == "connect":
        title = f"LinkedIn Connection Request for {name}"
        console.print(Panel(
            f"{message.body}\n\n[dim]({len(message.body)} / 300 chars)[/dim]",
            title=title,
            border_style="blue",
        ))
    else:
        title = f"LinkedIn Message for {name}"
        console.print(Panel(
            message.body,
            title=title,
            border_style="blue",
        ))

    if linkedin_url:
        console.print(f"\n[bold]LinkedIn profile:[/bold] {linkedin_url}")
        console.print("[dim]Open the link above, then paste the message.[/dim]")
    else:
        console.print("\n[yellow]No LinkedIn URL found.[/yellow] Enrich the lead to get their profile URL.")

    agent.close()


@app.command(name="auto-outreach")
def auto_outreach(
    lead_id: str = typer.Argument(..., help="Lead ID to run full outreach on"),
    email: bool = typer.Option(True, help="Send email via Resend"),
    linkedin: bool = typer.Option(True, help="Generate LinkedIn message"),
):
    """Full automated outreach: enrich → research → score → send email → generate LinkedIn message."""
    agent = _get_agent()

    channels = []
    if email:
        channels.append("email")
    if linkedin:
        channels.append("linkedin")

    with console.status("Running automated outreach pipeline..."):
        result = agent.auto_outreach(lead_id, channels)

    lead = agent.get_lead(lead_id)
    name = lead.name if lead else lead_id

    console.print(Panel(f"[bold]{name}[/bold]", title="Auto-Outreach Complete"))

    for action in result["actions"]:
        step = action["step"]
        status = action["status"]

        if status == "error":
            console.print(f"  [red]✗[/red] {step}: {action['error']}")
        elif step == "enrich":
            console.print(f"  [green]✓[/green] Enriched ({len(action.get('fields_updated', []))} fields)")
        elif step == "research":
            console.print(f"  [green]✓[/green] Researched")
        elif step == "send_email":
            console.print(f"  [green]✓[/green] Email sent to {action['sent_to']}")
            console.print(f"      Subject: {action['subject']}")
        elif step == "linkedin_connect":
            console.print(f"  [green]✓[/green] LinkedIn connection request generated")
            console.print(f"      Message: {action['message'][:80]}...")
            if action.get("profile_url") and action["profile_url"] != "Not available":
                console.print(f"      Profile: {action['profile_url']}")

    agent.close()


# -- Response & Qualification Commands --

@app.command()
def reply(
    lead_id: str = typer.Argument(..., help="Lead ID"),
    text: str = typer.Argument(..., help="The prospect's reply text"),
):
    """Process a prospect's reply and get AI analysis + next action."""
    agent = _get_agent()
    with console.status("Analyzing reply..."):
        result = agent.handle_reply(lead_id, text)

    console.print(Panel(
        f"[bold]Score:[/bold] {result['score']}/100\n"
        f"[bold]Next Action:[/bold] {result['next_action']}",
        title="Lead Qualification",
        border_style="cyan",
    ))

    if result.get("analysis"):
        console.print("\n[bold]Response Analysis:[/bold]")
        for k, v in result["analysis"].items():
            console.print(f"  [cyan]{k}:[/cyan] {v}")

    if result.get("qualification"):
        console.print("\n[bold]Qualification Details:[/bold]")
        for k, v in result["qualification"].items():
            console.print(f"  [cyan]{k}:[/cyan] {v}")

    agent.close()


@app.command()
def meeting(
    lead_id: str = typer.Argument(..., help="Lead ID"),
    channel: str = typer.Option("email", help="Channel: email or linkedin"),
):
    """Generate a meeting request message for a qualified lead."""
    agent = _get_agent()
    ch = Channel.EMAIL if channel == "email" else Channel.LINKEDIN

    with console.status("Generating meeting request..."):
        message = agent.request_meeting(lead_id, ch)

    console.print(Panel(
        f"[bold]Subject:[/bold] {message.subject}\n\n{message.body}",
        title=f"Meeting Request for {lead_id}",
        border_style="magenta",
    ))
    agent.close()


# -- Pipeline Commands --

@app.command()
def pipeline():
    """Show a summary of the lead pipeline."""
    agent = _get_agent()
    summary = agent.pipeline_summary()

    if not summary:
        console.print("[dim]Pipeline is empty. Add leads with 'funnel-filler add'.[/dim]")
        agent.close()
        return

    table = Table(title="Pipeline Summary")
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right")

    total = 0
    for status, count in summary.items():
        table.add_row(status, str(count))
        total += count

    table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]")
    console.print(table)
    agent.close()


@app.command()
def show(lead_id: str = typer.Argument(..., help="Lead ID")):
    """Show detailed info for a specific lead."""
    agent = _get_agent()
    lead = agent.get_lead(lead_id)

    if not lead:
        console.print(f"[red]Lead {lead_id} not found.[/red]")
        agent.close()
        return

    info = Text()
    info.append(f"Name: {lead.name}\n", style="bold")
    info.append(f"Email: {lead.email}\n")
    info.append(f"Company: {lead.company}\n")
    info.append(f"Title: {lead.title}\n")
    info.append(f"Industry: {lead.industry}\n")
    info.append(f"Status: {lead.status.value}\n")
    info.append(f"Score: {lead.score}/100\n")
    info.append(f"Created: {lead.created_at}\n")

    console.print(Panel(info, title=f"Lead {lead.id}", border_style="blue"))

    if lead.research:
        console.print("\n[bold]Research:[/bold]")
        for k, v in lead.research.items():
            console.print(f"  [cyan]{k}:[/cyan] {v}")

    messages = agent.db.get_messages_for_lead(lead_id)
    if messages:
        console.print(f"\n[bold]Messages ({len(messages)}):[/bold]")
        for msg in messages:
            direction = "INBOUND" if msg.is_inbound else "OUTBOUND"
            console.print(f"  [{direction}] {msg.message_type.value}: {msg.subject}")

    agent.close()


# -- Company Commands --

@app.command(name="add-company")
def add_company(
    name: str = typer.Argument(..., help="Company name"),
    domain: str = typer.Option("", help="Company domain (e.g. acme.com)"),
    industry: str = typer.Option("", help="Industry"),
    employees: int = typer.Option(0, help="Number of employees"),
    location: str = typer.Option("", help="Location (e.g. San Francisco, CA)"),
    website: str = typer.Option("", help="Website URL"),
    linkedin: str = typer.Option("", help="LinkedIn company URL"),
    notes: str = typer.Option("", help="Additional notes"),
):
    """Add a new company to the pipeline."""
    agent = _get_agent()
    company = agent.add_company(
        name, domain, industry, employees, location,
        website_url=website, linkedin_url=linkedin, notes=notes,
    )
    console.print(f"[green]Added company:[/green] {company.name} ({company.id})")
    agent.close()


@app.command(name="list-companies")
def list_companies_cmd(
    status: str = typer.Option("", help="Filter by status (new, enriched, qualified, target, disqualified)"),
):
    """List all companies in the pipeline."""
    agent = _get_agent()
    company_status = CompanyStatus(status) if status else None
    companies = agent.list_companies(company_status)

    if not companies:
        console.print("[dim]No companies found.[/dim]")
        agent.close()
        return

    table = Table(title="Companies Pipeline")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Domain")
    table.add_column("Industry")
    table.add_column("Employees", justify="right")
    table.add_column("Status")
    table.add_column("Score", justify="right")

    status_colors = {
        "new": "white",
        "researching": "cyan",
        "enriched": "yellow",
        "qualified": "bold green",
        "target": "bold magenta",
        "disqualified": "red",
    }

    for c in companies:
        color = status_colors.get(c.status.value, "white")
        table.add_row(
            c.id,
            c.name,
            c.domain,
            c.industry,
            str(c.employee_count) if c.employee_count else "",
            f"[{color}]{c.status.value}[/{color}]",
            str(c.score),
        )

    console.print(table)
    agent.close()


@app.command(name="show-company")
def show_company(company_id: str = typer.Argument(..., help="Company ID")):
    """Show detailed info for a specific company."""
    agent = _get_agent()
    company = agent.get_company(company_id)

    if not company:
        console.print(f"[red]Company {company_id} not found.[/red]")
        agent.close()
        return

    info = Text()
    info.append(f"Name: {company.name}\n", style="bold")
    info.append(f"Domain: {company.domain}\n")
    info.append(f"Industry: {company.industry}\n")
    info.append(f"Employees: {company.employee_count}\n")
    info.append(f"Location: {company.location}\n")
    info.append(f"Website: {company.website_url}\n")
    info.append(f"LinkedIn: {company.linkedin_url}\n")
    info.append(f"Revenue: {company.annual_revenue}\n")
    info.append(f"Founded: {company.founded_year}\n")
    info.append(f"Status: {company.status.value}\n")
    info.append(f"Score: {company.score}/100\n")
    info.append(f"Created: {company.created_at}\n")

    if company.description:
        info.append(f"\n{company.description}\n")

    console.print(Panel(info, title=f"Company {company.id}", border_style="blue"))

    if company.technologies:
        console.print(f"\n[bold]Technologies:[/bold] {', '.join(company.technologies)}")

    if company.keywords:
        console.print(f"[bold]Keywords:[/bold] {', '.join(company.keywords)}")

    if company.research:
        console.print("\n[bold]Research:[/bold]")
        for k, v in company.research.items():
            console.print(f"  [cyan]{k}:[/cyan] {v}")

    agent.close()


@app.command(name="search-companies")
def search_companies_cmd(query: str = typer.Argument(..., help="Search query")):
    """Search companies by name, domain, industry, or description."""
    agent = _get_agent()
    companies = agent.search_companies(query)
    if not companies:
        console.print("[dim]No companies found.[/dim]")
    else:
        for c in companies:
            console.print(f"  {c.id}  {c.name} ({c.domain}) — [{c.status.value}]")
    agent.close()


@app.command(name="enrich-company")
def enrich_company(company_id: str = typer.Argument(..., help="Company ID to enrich")):
    """Enrich a company with real data from Apollo.io (industry, employees, revenue, tech stack, etc.)."""
    agent = _get_agent()
    with console.status("Enriching company via Apollo..."):
        company, updated = agent.enrich_company(company_id)

    if not updated:
        console.print(f"[yellow]No new data found for {company.name}.[/yellow]")
        console.print("[dim]Tip: ensure the company has a name or domain for best results.[/dim]")
        agent.close()
        return

    console.print(Panel(f"[bold]{company.name}[/bold] ({company.domain})", title="Company Enrichment Complete"))

    # Show updated core fields (exclude apollo_data and auto_score)
    core_fields = {k: v for k, v in updated.items() if k not in ("apollo_data", "auto_score")}
    if core_fields:
        console.print("[bold]Updated fields:[/bold]")
        for field_name, value in core_fields.items():
            if isinstance(value, list):
                console.print(f"  [green]{field_name}:[/green] {', '.join(str(v) for v in value)}")
            else:
                console.print(f"  [green]{field_name}:[/green] {value}")

    # Show extra Apollo data
    apollo_data = updated.get("apollo_data", {})
    if apollo_data:
        console.print("\n[bold]Additional data from Apollo:[/bold]")
        for key, value in apollo_data.items():
            if isinstance(value, list):
                display = ", ".join(str(v) for v in value[:10])
                if len(value) > 10:
                    display += f" (+{len(value) - 10} more)"
                console.print(f"  [cyan]{key}:[/cyan] {display}")
            else:
                console.print(f"  [cyan]{key}:[/cyan] {value}")

    # Show auto-score if it ran
    auto_score = updated.get("auto_score")
    if auto_score:
        s = auto_score["score"]
        console.print(f"\n[bold]Auto-score:[/bold] {s}/100 — {auto_score.get('reasoning', '')}")

    agent.close()


@app.command(name="prospect-companies")
def prospect_companies(
    icp_name: str = typer.Option("default", "--icp", help="ICP profile to use"),
    count: int = typer.Option(25, help="Number of companies to find (max 100)"),
    page: int = typer.Option(1, help="Page number for pagination"),
):
    """Find new companies matching your ICP via Apollo."""
    agent = _get_agent()
    with console.status("Searching Apollo for companies..."):
        companies = agent.prospect_companies(icp_name, count=min(count, 100), page=page)

    if not companies:
        console.print("[yellow]No new companies found (or all matches are already in your pipeline).[/yellow]")
        agent.close()
        return

    table = Table(title=f"Found {len(companies)} New Companies")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Domain")
    table.add_column("Industry")
    table.add_column("Employees", justify="right")
    table.add_column("Location")

    for c in companies:
        table.add_row(
            c.id, c.name, c.domain, c.industry,
            str(c.employee_count) if c.employee_count else "",
            c.location,
        )

    console.print(table)
    console.print(f"\n[green]{len(companies)} companies added to pipeline.[/green]")
    console.print("[dim]Use 'funnel-filler enrich-company <id>' to get more details.[/dim]")
    agent.close()


@app.command(name="score-company")
def score_company_cmd(company_id: str = typer.Argument(..., help="Company ID to score")):
    """Score a company using AI analysis + rule-based adjustments (0-100)."""
    agent = _get_agent()
    with console.status("Scoring company..."):
        result = agent.score_company(company_id)

    company = agent.get_company(company_id)
    name = company.name if company else company_id

    # Score color
    s = result["score"]
    if s >= 80:
        color = "bold green"
    elif s >= 60:
        color = "green"
    elif s >= 40:
        color = "yellow"
    else:
        color = "red"

    console.print(Panel(
        f"[{color}]{s}/100[/{color}]  (AI: {result['ai_score']} + Rules: {result['rule_adjustment']:+d})",
        title=f"Score for {name}",
    ))

    if result.get("reasoning"):
        console.print(f"\n[bold]Reasoning:[/bold] {result['reasoning']}")

    if result.get("strengths"):
        console.print("\n[bold]Strengths:[/bold]")
        for item in result["strengths"]:
            console.print(f"  [green]+[/green] {item}")

    if result.get("concerns"):
        console.print("\n[bold]Concerns:[/bold]")
        for item in result["concerns"]:
            console.print(f"  [red]-[/red] {item}")

    if result.get("rule_details"):
        console.print("\n[bold]Rule adjustments:[/bold]")
        for rule in result["rule_details"]:
            sign = "+" if rule["points"] > 0 else ""
            console.print(f"  [dim]{sign}{rule['points']}[/dim] {rule['rule']}")

    agent.close()


@app.command(name="company-pipeline")
def company_pipeline():
    """Show a summary of the company pipeline."""
    agent = _get_agent()
    summary = agent.company_pipeline_summary()

    if not summary:
        console.print("[dim]Company pipeline is empty. Add companies with 'funnel-filler add-company'.[/dim]")
        agent.close()
        return

    table = Table(title="Company Pipeline Summary")
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right")

    total = 0
    for status, count in summary.items():
        table.add_row(status, str(count))
        total += count

    table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]")
    console.print(table)
    agent.close()


if __name__ == "__main__":
    app()
