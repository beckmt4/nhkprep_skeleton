from __future__ import annotations
import json
from pathlib import Path
import typer
from rich import print
from .version import __version__
from .logging_setup import configure_logging
from .media_probe import ffprobe
from .config import RuntimeConfig
from .media_edit import remux_keep_ja_en_set_ja_default

app = typer.Typer(add_completion=False, help="NHK -> English media prep pipeline")
configure_logging()

@app.callback()
def _version(version: bool = typer.Option(False, "--version", help="Show version")) -> None:
    if version:
        print(__version__)
        raise typer.Exit(0)

@app.command()
def scan(
    video_path: Path = typer.Argument(..., exists=True, readable=True, help="Video file"),
    json_out: bool = typer.Option(False, "--json", help="Print JSON inventory"),
):
    """Probe a media file and print its stream inventory."""
    mi = ffprobe(video_path)
    if json_out:
        print(json.dumps(mi.model_dump(), ensure_ascii=False, indent=2))
    else:
        print(f"[bold]Path:[/bold] {mi.path}")
        print(f"[bold]Duration:[/bold] {mi.duration or '?'} s")
        print("[bold]Streams:[/bold]")
        for s in mi.streams:
            print(f"- idx={s.index} type={s.codec_type} lang={s.language} forced={s.forced} default={s.default} title={s.title}")

@app.command()
def process(
    video_path: Path = typer.Argument(..., exists=True, readable=True, help="Video file"),
    in_place: bool = typer.Option(False, "--in-place", help="Modify file in place"),
    prefer_ja_audio: bool = typer.Option(True, "--prefer-ja-audio/--no-prefer-ja-audio", help="Set JA audio as default"),
    max_line_chars: int = typer.Option(32, help="Max characters per subtitle line"),
    max_lines: int = typer.Option(2, help="Max lines per cue"),
    max_cps: int = typer.Option(15, help="Max characters per second"),
    execute: bool = typer.Option(False, "--execute", help="Actually write outputs (otherwise dry-run)"),
):
    """Run the end-to-end cleaning + (stub)translation pipeline.


    By default this is a dry-run that prints the plan and suggests output paths. Use --execute to write files.
    """
    cfg = RuntimeConfig(
        max_line_chars=max_line_chars, max_lines=max_lines, max_cps=max_cps,
        prefer_ja_audio=prefer_ja_audio, in_place=in_place, execute=execute
    )
    mi = ffprobe(video_path)
    print("[cyan]Plan:[/cyan] keep only JA/EN streams, remux losslessly; set JA audio default.")
    out_path = remux_keep_ja_en_set_ja_default(mi, execute=cfg.execute, in_place=cfg.in_place)
    if execute:
        print(f"[green]Wrote:[/green] {out_path}")
    else:
        print(f"[yellow]Dry-run. Would write:[/yellow] {out_path}")

if __name__ == "__main__":
    app()
