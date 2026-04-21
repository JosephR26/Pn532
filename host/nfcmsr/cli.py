"""`nfcmsr` CLI entrypoint."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .msr605x import STATUS_OK, TrackData, msr_device, track2_lrc
from .pn532_serial import FirmwareError, firmware
from .profile import CardProfile, MagstripeData, NfcData, validate

console = Console()

AUTH_BANNER = (
    "This tool is for authorised security testing only. "
    "See docs/legal.md."
)


@click.group()
@click.version_option(__version__)
def main() -> None:
    """nfcmsr — PN532 + MSR605X pentesting toolkit."""


@main.group()
def nfc() -> None:
    """NFC operations via the tethered ESP32 handheld."""


@nfc.command("read")
@click.option("--port", required=True, help="ESP32 USB-serial device, e.g. /dev/ttyUSB0.")
@click.option("--timeout-ms", default=2000, show_default=True, help="PN532 scan timeout.")
@click.option("--save", "save_path", type=click.Path(dir_okay=False, path_type=Path),
              help="Write captured profile to JSON file.")
@click.option("--into", "into_path", type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="Merge NFC data into an existing profile.")
def nfc_read(port: str, timeout_ms: int, save_path: Path | None, into_path: Path | None) -> None:
    """Ask the handheld to scan the next card and pull the result."""
    console.print(f"[dim]{AUTH_BANNER}[/dim]")
    try:
        with firmware(port) as client:
            if not client.ping():
                console.print("[red]Firmware did not respond to ping.[/red]")
                sys.exit(1)
            console.print("Waiting for card...")
            data = client.scan(timeout_ms=timeout_ms)
    except FirmwareError as exc:
        console.print(f"[red]Firmware error:[/red] {exc}")
        sys.exit(1)

    if not data:
        console.print("[yellow]No card detected before timeout.[/yellow]")
        sys.exit(2)

    if into_path:
        profile = CardProfile.load(into_path)
        profile.nfc = NfcData.from_dict(data.get("nfc"))
        profile.source = "host"
    else:
        profile = CardProfile(source="host")
        profile.nfc = NfcData.from_dict(data.get("nfc"))

    _print_profile(profile)

    errors = validate(profile)
    if errors:
        console.print("[yellow]Profile does not validate against schema:[/yellow]")
        for e in errors:
            console.print(f"  {e}")

    target = save_path or into_path
    if target:
        profile.save(target)
        console.print(f"[green]Saved profile to {target}[/green]")


@main.group()
def msr() -> None:
    """Magstripe operations via the MSR605X."""


@msr.command("read")
@click.option("--port", required=True, help="MSR605X USB-serial device.")
@click.option("--save", "save_path", type=click.Path(dir_okay=False, path_type=Path),
              help="Write a new profile containing the read tracks.")
@click.option("--into", "into_path", type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="Merge magstripe data into an existing profile.")
def msr_read(port: str, save_path: Path | None, into_path: Path | None) -> None:
    """Read Tracks 1/2/3 from a swiped card."""
    console.print(f"[dim]{AUTH_BANNER}[/dim]")
    console.print("Please swipe the card...")
    with msr_device(port) as dev:
        tracks, status = dev.read_iso()

    ok = status == STATUS_OK

    if into_path:
        profile = CardProfile.load(into_path)
    else:
        profile = CardProfile(source="host")

    profile.magstripe = MagstripeData(
        track1=tracks.track1,
        track2=tracks.track2,
        track3=tracks.track3,
        track2_lrc_ok=_verify_track2_lrc(tracks.track2) if tracks.track2 else None,
        read_device="MSR605X",
    )

    _print_profile(profile)
    if not ok:
        console.print(f"[yellow]MSR605X reported status byte 0x{status:02x}[/yellow]")

    target = save_path or into_path
    if target:
        profile.save(target)
        console.print(f"[green]Saved profile to {target}[/green]")


@msr.command("write")
@click.option("--port", required=True)
@click.option("--from", "from_path", required=True,
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="Profile whose magstripe data will be written.")
@click.option("--coercivity", type=click.Choice(["hi", "lo"]), default="hi", show_default=True)
def msr_write(port: str, from_path: Path, coercivity: str) -> None:
    """Write Tracks 1/2/3 from a profile to a blank card."""
    console.print(f"[dim]{AUTH_BANNER}[/dim]")
    profile = CardProfile.load(from_path)
    mag = profile.magstripe
    if not any([mag.track1, mag.track2, mag.track3]):
        console.print("[red]Profile has no magstripe data.[/red]")
        sys.exit(1)

    console.print("Please swipe the blank card...")
    with msr_device(port) as dev:
        dev.set_coercivity(coercivity)
        status = dev.write_iso(TrackData(track1=mag.track1, track2=mag.track2, track3=mag.track3))

    if status == STATUS_OK:
        console.print("[green]Write successful.[/green]")
    else:
        console.print(f"[red]Write failed, status byte 0x{status:02x}[/red]")
        sys.exit(1)


@main.group()
def profile() -> None:
    """Card profile utilities."""


@profile.command("show")
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def profile_show(path: Path) -> None:
    """Pretty-print a card profile."""
    prof = CardProfile.load(path)
    _print_profile(prof)


@profile.command("validate")
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def profile_validate(path: Path) -> None:
    """Validate a card profile against the shared schema."""
    prof = CardProfile.load(path)
    errors = validate(prof)
    if not errors:
        console.print("[green]Profile is valid.[/green]")
        return
    console.print("[red]Profile is invalid:[/red]")
    for e in errors:
        console.print(f"  {e}")
    sys.exit(1)


@profile.command("raw")
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def profile_raw(path: Path) -> None:
    """Print the raw JSON of a profile."""
    data = json.loads(path.read_text(encoding="utf-8"))
    click.echo(json.dumps(data, indent=2))


def _verify_track2_lrc(track2: str) -> bool | None:
    if not track2 or len(track2) < 2:
        return None
    try:
        computed = track2_lrc(track2[:-1])
    except ValueError:
        return False
    from .msr605x import TRACK2_ALPHABET
    last = TRACK2_ALPHABET.find(track2[-1])
    return last >= 0 and last == computed


def _print_profile(prof: CardProfile) -> None:
    table = Table(title=f"Card profile {prof.id[:8]}…", show_header=False)
    table.add_column("field", style="bold")
    table.add_column("value")

    if prof.label:
        table.add_row("label", prof.label)
    table.add_row("captured_at", prof.captured_at)
    if prof.updated_at:
        table.add_row("updated_at", prof.updated_at)
    table.add_row("source", prof.source)

    if prof.nfc.uid:
        table.add_row("nfc.technology", prof.nfc.technology or "?")
        table.add_row("nfc.uid", prof.nfc.uid)
        if prof.nfc.atqa:
            table.add_row("nfc.atqa", prof.nfc.atqa)
        if prof.nfc.sak:
            table.add_row("nfc.sak", prof.nfc.sak)
        if prof.nfc.tag_type:
            table.add_row("nfc.tag_type", prof.nfc.tag_type)
        if prof.nfc.sectors:
            table.add_row("nfc.sectors", f"{len(prof.nfc.sectors)} captured")

    mag = prof.magstripe
    if mag.track1 or mag.track2 or mag.track3:
        for name in ("track1", "track2", "track3"):
            value = getattr(mag, name)
            if value:
                table.add_row(f"magstripe.{name}", value)
        if mag.track2_lrc_ok is not None:
            table.add_row("magstripe.track2_lrc_ok", str(mag.track2_lrc_ok))

    console.print(table)


if __name__ == "__main__":
    main()
