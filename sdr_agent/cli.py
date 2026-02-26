"""Command-line interface for the Funnel Filler SDR agent."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .agent import SDRAgent
from .models import Channel, LeadStatus

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


if __name__ == "__main__":
    app()
