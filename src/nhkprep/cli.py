from __future__ import annotations
import json
from pathlib import Path
import typer
from rich import print
from .version import __version__
from .logging_setup import configure_logging
from .media_probe import ffprobe
from .config import RuntimeConfig
from .media_edit import remux_keep_ja_en_set_ja_default, detect_and_fix_language_tags
from .enhanced_language_detect import EnhancedLanguageDetector, apply_language_tags as enhanced_apply_language_tags

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
        # Use JSON mode so Path and other types are serialized safely
        print(json.dumps(mi.model_dump(mode="json"), ensure_ascii=False, indent=2))
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
    detect_languages: bool = typer.Option(False, "--detect-languages", help="Auto-detect and fix language tags"),
    force_lang_detect: bool = typer.Option(False, "--force-lang-detect", help="Force language detection even for tagged tracks"),
    lang_confidence: float = typer.Option(0.5, "--lang-confidence", help="Minimum confidence for language detection (0.0-1.0)"),
):
    """Run the end-to-end cleaning + (stub)translation pipeline.

    By default this is a dry-run that prints the plan and suggests output paths. Use --execute to write files.
    """
    cfg = RuntimeConfig(
        max_line_chars=max_line_chars, max_lines=max_lines, max_cps=max_cps,
        prefer_ja_audio=prefer_ja_audio, in_place=in_place, execute=execute
    )
    mi = ffprobe(video_path)
    
    # Language detection step (if requested)
    if detect_languages:
        print("[cyan]Step 1:[/cyan] Detecting and fixing language tags...")
        try:
            lang_results = detect_and_fix_language_tags(
                mi, 
                execute=execute,
                force_detection=force_lang_detect, 
                confidence_threshold=lang_confidence
            )
            
            # Print detection results
            print("[bold]Language Detection Results:[/bold]")
            for track_idx, detection in lang_results["detections"].items():
                track_num = track_idx + 1
                current = detection["current_language"] or "none"
                detected = detection["detected_language"] or "none"
                confidence = detection["confidence"]
                method = detection["method"]
                
                print(f"  Track {track_num}: {current} → {detected} (confidence: {confidence:.2f}, method: {method})")
            
            if lang_results["changes_planned"]:
                print(f"[yellow]Planned changes:[/yellow] {len(lang_results['changes_planned'])} tracks")
                for change in lang_results["changes_planned"]:
                    print(f"  Track {change['track']}: → {change['language']} ({change['reason']})")
            
            if execute and lang_results["changes_applied"]:
                print(f"[green]Applied changes:[/green] {len(lang_results['changes_applied'])} tracks")
                for change in lang_results["changes_applied"]:
                    print(f"  {change}")
            elif not execute:
                print("[yellow]Dry-run mode:[/yellow] Use --execute to apply language tag changes")
            
            if lang_results["skipped"]:
                print(f"[dim]Skipped {len(lang_results['skipped'])} tracks[/dim]")
            
            # Re-probe the file if we made changes to get updated metadata
            if execute and lang_results["changes_applied"]:
                mi = ffprobe(video_path)
            
        except Exception as e:
            print(f"[red]Language detection failed:[/red] {e}")
            if not execute:
                print("[yellow]Note:[/yellow] This error might not occur in actual execution")
    
    # Main processing step
    print(f"[cyan]Step {'2' if detect_languages else '1'}:[/cyan] Keep only JA/EN streams, remux losslessly; set JA audio default.")
    out_path = remux_keep_ja_en_set_ja_default(mi, execute=cfg.execute, in_place=cfg.in_place)
    if execute:
        print(f"[green]Wrote:[/green] {out_path}")
    else:
        print(f"[yellow]Dry-run. Would write:[/yellow] {out_path}")


@app.command()
def detect_lang(
    video_path: Path = typer.Argument(..., exists=True, readable=True, help="Video file"),
    execute: bool = typer.Option(False, "--execute", help="Actually apply language tags (otherwise just show detection)"),
    force: bool = typer.Option(False, "--force", help="Force detection even for tracks that already have language tags"),
    confidence: float = typer.Option(0.5, "--confidence", help="Minimum confidence threshold (0.0-1.0)"),
    json_out: bool = typer.Option(False, "--json", help="Output results as JSON"),
):
    """Detect and optionally fix language tags for audio and subtitle tracks."""
    mi = ffprobe(video_path)
    
    try:
        results = detect_and_fix_language_tags(
            mi, 
            execute=execute,
            force_detection=force, 
            confidence_threshold=confidence
        )
        
        if json_out:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print(f"[bold]Language Detection Results for:[/bold] {video_path.name}")
            print()
            
            # Show detection results
            print("[bold]Detection Results:[/bold]")
            for track_idx, detection in results["detections"].items():
                track_num = track_idx + 1
                stream = mi.streams[track_idx]
                current = detection["current_language"] or "none"
                detected = detection["detected_language"] or "none"
                confidence = detection["confidence"]
                method = detection["method"]
                
                print(f"  Track {track_num} ({stream.codec_type}):")
                print(f"    Current: {current}")
                print(f"    Detected: {detected}")
                print(f"    Confidence: {confidence:.2f}")
                print(f"    Method: {method}")
                print(f"    Details: {detection['details']}")
                print()
            
            # Show planned/applied changes
            if results["changes_planned"]:
                print(f"[yellow]{'Applied Changes' if execute else 'Planned Changes'}:[/yellow]")
                changes = results["changes_applied"] if execute else results["changes_planned"]
                
                if execute:
                    for change in changes:
                        print(f"  ✓ {change}")
                else:
                    for change in results["changes_planned"]:
                        print(f"  • Track {change['track']}: → {change['language']} ({change['reason']})")
                print()
            
            # Show skipped tracks
            if results["skipped"]:
                print("[dim]Skipped Tracks:[/dim]")
                for skip in results["skipped"]:
                    print(f"  Track {skip['track']}: {skip['reason']}")
                print()
            
            # Show summary
            total_tracks = len([s for s in mi.streams if s.codec_type in ('audio', 'subtitle')])
            detected_count = len([d for d in results["detections"].values() if d["detected_language"]])
            applied_count = len(results["changes_applied"] if execute else results["changes_planned"])
            
            print(f"[bold]Summary:[/bold] {detected_count}/{total_tracks} languages detected, {applied_count} changes {'applied' if execute else 'planned'}")
            
            if not execute and results["changes_planned"]:
                print("[yellow]Use --execute to apply the planned changes[/yellow]")
        
    except Exception as e:
        print(f"[red]Language detection failed:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def detect_lang_enhanced(
    video_path: Path = typer.Argument(..., exists=True, readable=True, help="Video file"),
    execute: bool = typer.Option(False, "--execute", help="Actually apply language tags (otherwise just show detection)"),
    force: bool = typer.Option(False, "--force", help="Force detection even for tracks that already have language tags"),
    confidence: float = typer.Option(0.5, "--confidence", help="Minimum confidence threshold (0.0-1.0)"),
    json_out: bool = typer.Option(False, "--json", help="Output results as JSON"),
):
    """Enhanced production-ready language detection with improved accuracy and performance metrics."""
    mi = ffprobe(video_path)
    
    # Use the enhanced detector
    detector = EnhancedLanguageDetector()
    detector.confidence_threshold = confidence
    
    try:
        print(f"[bold]Enhanced Language Detection for:[/bold] {video_path.name}")
        print()
        
        # Detect languages for all tracks
        detections = detector.detect_all_languages(mi, force_detection=force)
        
        # Prepare results for display/JSON
        results = {
            "file": str(video_path),
            "detections": {},
            "changes_planned": [],
            "changes_applied": [],
            "skipped": [],
            "performance": {
                "total_detection_time_ms": sum(d.detection_time_ms for d in detections.values()),
                "average_detection_time_ms": sum(d.detection_time_ms for d in detections.values()) / len(detections) if detections else 0,
            }
        }
        
        # Process each detection
        for track_idx, detection in detections.items():
            stream = mi.streams[track_idx]
            track_num = track_idx + 1
            
            # Store detection info
            detection_info = {
                "current_language": stream.language,
                "detected_language": detection.language,
                "confidence": detection.confidence,
                "method": detection.method,
                "details": detection.details,
                "alternative_languages": detection.alternative_languages or [],
                "text_sample_size": detection.text_sample_size,
                "detection_time_ms": detection.detection_time_ms
            }
            results["detections"][track_idx] = detection_info
            
            # Determine if we should apply the change
            should_apply = False
            reason = ""
            
            if detection.language and detection.confidence >= confidence:
                current_lang = stream.language
                detected_lang = detection.language
                
                # Apply if no current language or different language detected
                if not current_lang or current_lang.lower() in ('und', 'unknown', '', 'null'):
                    should_apply = True
                    reason = f"No valid current language"
                elif force and current_lang.lower() != detected_lang.lower():
                    should_apply = True
                    reason = f"Forced update: {current_lang} → {detected_lang}"
                elif current_lang.lower() != detected_lang.lower():
                    if not force:
                        results["skipped"].append({
                            "track": track_num,
                            "reason": f"Current language '{current_lang}' differs from detected '{detected_lang}' (use --force to override)"
                        })
            else:
                if detection.language:
                    results["skipped"].append({
                        "track": track_num,
                        "reason": f"Low confidence: {detection.confidence:.3f} < {confidence:.3f}"
                    })
                else:
                    results["skipped"].append({
                        "track": track_num,
                        "reason": "No language detected"
                    })
            
            if should_apply:
                change = {
                    "track": track_num,
                    "language": detection.language,
                    "confidence": detection.confidence,
                    "method": detection.method,
                    "reason": reason
                }
                results["changes_planned"].append(change)
        
        # Apply changes if requested
        if execute and results["changes_planned"]:
            # Prepare detection dictionary for apply function
            apply_detections = {}
            for change in results["changes_planned"]:
                track_idx = change["track"] - 1
                apply_detections[track_idx] = detections[track_idx]
            
            changes_applied = enhanced_apply_language_tags(
                video_path, apply_detections, execute=True, confidence_threshold=confidence
            )
            results["changes_applied"] = changes_applied
        
        # Output results
        if json_out:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            # Show detection results
            print("[bold]Enhanced Detection Results:[/bold]")
            for track_idx, detection_info in results["detections"].items():
                track_num = track_idx + 1
                stream = mi.streams[track_idx]
                current = detection_info["current_language"] or "none"
                detected = detection_info["detected_language"] or "none"
                confidence = detection_info["confidence"]
                method = detection_info["method"]
                
                print(f"  Track {track_num} ({stream.codec_type}):")
                print(f"    Current: {current}")
                print(f"    Detected: {detected} (confidence: {confidence:.3f})")
                print(f"    Method: {method}")
                print(f"    Details: {detection_info['details']}")
                
                if detection_info["alternative_languages"]:
                    alts = ", ".join([f"{lang}({conf:.3f})" for lang, conf in detection_info["alternative_languages"][:3]])
                    print(f"    Alternatives: {alts}")
                
                if detection_info["text_sample_size"] > 0:
                    print(f"    Text sample: {detection_info['text_sample_size']} characters")
                
                print(f"    Detection time: {detection_info['detection_time_ms']:.1f}ms")
                print()
            
            # Show planned/applied changes
            if results["changes_planned"]:
                print(f"[yellow]{'Applied Changes' if execute else 'Planned Changes'}:[/yellow]")
                
                if execute:
                    for change in results["changes_applied"]:
                        print(f"  ✓ {change}")
                else:
                    for change in results["changes_planned"]:
                        print(f"  • Track {change['track']}: → {change['language']} "
                              f"(confidence: {change['confidence']:.3f}, method: {change['method']})")
                print()
            
            # Show skipped tracks
            if results["skipped"]:
                print("[dim]Skipped Tracks:[/dim]")
                for skip in results["skipped"]:
                    print(f"  Track {skip['track']}: {skip['reason']}")
                print()
            
            # Show performance metrics
            print("[bold]Performance Metrics:[/bold]")
            print(f"  Total detection time: {results['performance']['total_detection_time_ms']:.1f}ms")
            print(f"  Average per track: {results['performance']['average_detection_time_ms']:.1f}ms")
            print()
            
            # Show summary
            total_tracks = len([s for s in mi.streams if s.codec_type in ('audio', 'subtitle')])
            detected_count = len([d for d in results["detections"].values() if d["detected_language"]])
            applied_count = len(results["changes_applied"] if execute else results["changes_planned"])
            
            print(f"[bold]Summary:[/bold] {detected_count}/{total_tracks} languages detected, {applied_count} changes {'applied' if execute else 'planned'}")
            
            if not execute and results["changes_planned"]:
                print("[yellow]Use --execute to apply the planned changes[/yellow]")
        
    except Exception as e:
        print(f"[red]Enhanced language detection failed:[/red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
