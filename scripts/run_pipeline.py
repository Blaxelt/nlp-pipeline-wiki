#!/usr/bin/env python3

from __future__ import annotations

import urllib.request
import argparse
import logging
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Sequence


PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = PROJECT_ROOT / "data"
LOGS_DIR: Path = PROJECT_ROOT / "logs"

_DATE_RE = re.compile(r"eswiki-(\d{8})-pages-articles-ns0-no-redirects-clean\.json")


@dataclass
class Step:
    """A single subprocess invocation within a pipeline stage."""

    name: str
    script: str
    args: list[str] = field(default_factory=list)
    outputs: list[Path] = field(default_factory=list)


@dataclass
class Stage:
    """A group of steps that can run in parallel."""

    name: str
    steps: list[Step]
    parallel: bool = True


def _setup_logging(new_date: str) -> logging.Logger:
    """Configure dual logging: console (INFO) + file (DEBUG)."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOGS_DIR / f"pipeline_{new_date}_{timestamp}.log"

    logger = logging.getLogger("pipeline")
    logger.setLevel(logging.DEBUG)

    # File handler — captures everything
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(
        logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    # Console handler — INFO and above
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.INFO)
    ch.setFormatter(
        logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
    )

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("Log file: %s", log_path)
    return logger



def detect_dump_dates() -> list[str]:
    """Scan data/outputs/filtered_dumps/ for eswiki-YYYYMMDD-pages-articles-ns0-no-redirects-clean.json files."""
    dates: list[str] = []
    search_dir = DATA_DIR / "outputs" / "filtered_dumps"
    if not search_dir.is_dir():
        return dates
    for entry in search_dir.iterdir():
        m = _DATE_RE.match(entry.name)
        if m:
            dates.append(m.group(1))
    dates.sort()
    return dates


def build_pipeline(
    new: str,
    old: str,
    *,
    processes: int | None = None,
) -> list[Stage]:
    """Build the ordered list of stages for the given dump dates."""
    proc_args: list[str] = ["--processes", str(processes)] if processes else []

    stage1 = Stage(
        name="Extract Synonyms/Redirects Mapping",
        steps=[
            Step(
                name="extract_redirects",
                script="scripts/extraction/extract_redirects.py",
                args=[
                    "--date", new,
                    "--input", str(DATA_DIR / "outputs" / "filtered_dumps" / f"eswiki-{new}-pages-articles-clean.json"),
                    "--output", str(DATA_DIR / "outputs" / "redirects" / "redirects_map.json")
                ],
                outputs=[
                    DATA_DIR / "outputs" / "redirects" / "redirects_map.json",
                ],
            ),
        ],
    )

    stage2 = Stage(
        name="Token Frequency Extraction",
        steps=[
            Step(
                name="extract_all_tokens",
                script="scripts/analysis/extract_all_tokens.py",
                args=[
                    "--input", str(DATA_DIR / "outputs" / "filtered_dumps" / f"eswiki-{new}-pages-articles-ns0-no-redirects-clean.json"),
                    "--date", new, 
                    "--output", str(DATA_DIR / "outputs" / "token_frequencies" / f"eswiki_{new}_token_frequencies.txt"),
                    *proc_args
                ],
                outputs=[
                    DATA_DIR / "outputs" / "token_frequencies" / f"eswiki_{new}_token_frequencies.txt",
                ],
            ),
            Step(
                name="extract_all_phrasal_nouns",
                script="scripts/phrasal_nouns/extract_all_phrasal_nouns.py",
                args=[
                    "--input", str(DATA_DIR / "outputs" / "filtered_dumps" / f"eswiki-{new}-pages-articles-ns0-no-redirects-clean.json"),
                    "--date", new, 
                    "--output", str(DATA_DIR / "outputs" / "phrasal_nouns" / f"eswiki_{new}_phrasal_nouns_freq.txt"),
                    *proc_args
                ],
                outputs=[
                    DATA_DIR / "outputs" / "phrasal_nouns" / f"eswiki_{new}_phrasal_nouns_freq.txt",
                ],
            ),
            Step(
                name="extract_all_tokens_old",
                script="scripts/analysis/extract_all_tokens.py",
                args=[
                    "--input", str(DATA_DIR / "outputs" / "filtered_dumps" / f"eswiki-{old}-pages-articles-ns0-no-redirects-clean.json"),
                    "--date", old, 
                    "--output", str(DATA_DIR / "outputs" / "token_frequencies" / f"eswiki_{old}_token_frequencies.txt"),
                    *proc_args
                ],
                outputs=[
                    DATA_DIR / "outputs" / "token_frequencies" / f"eswiki_{old}_token_frequencies.txt",
                ],
            ),
            Step(
                name="extract_all_phrasal_nouns_old",
                script="scripts/phrasal_nouns/extract_all_phrasal_nouns.py",
                args=[
                    "--input", str(DATA_DIR / "outputs" / "filtered_dumps" / f"eswiki-{old}-pages-articles-ns0-no-redirects-clean.json"),
                    "--date", old, 
                    "--output", str(DATA_DIR / "outputs" / "phrasal_nouns" / f"eswiki_{old}_phrasal_nouns_freq.txt"),
                    *proc_args
                ],
                outputs=[
                    DATA_DIR / "outputs" / "phrasal_nouns" / f"eswiki_{old}_phrasal_nouns_freq.txt",
                ],
            ),
        ],
    )

    stage3 = Stage(
        name="Neologism Detection",
        steps=[
            Step(
                name="find_neologisms",
                script="scripts/neologisms/find_neologisms.py",
                args=[
                    "--input-new", str(DATA_DIR / "outputs" / "token_frequencies" / f"eswiki_{new}_token_frequencies.txt"),
                    "--input-old", str(DATA_DIR / "outputs" / "token_frequencies" / f"eswiki_{old}_token_frequencies.txt"),
                    "--date", new, 
                    "--old-date", old,
                    "--output", str(DATA_DIR / "outputs" / "neologisms" / f"eswiki_neologisms_{new}_{old}.txt")
                ],
                outputs=[
                    DATA_DIR / "outputs" / "neologisms" / f"eswiki_neologisms_{new}_{old}.txt",
                ],
            ),
            Step(
                name="find_neologistic_phrasal_nouns",
                script="scripts/phrasal_nouns/find_neologistic_phrasal_nouns.py",
                args=[
                    "--new", str(DATA_DIR / "outputs" / "phrasal_nouns" / f"eswiki_{new}_phrasal_nouns_freq.txt"),
                    "--old", str(DATA_DIR / "outputs" / "phrasal_nouns" / f"eswiki_{old}_phrasal_nouns_freq.txt"),
                    "--date", new, 
                    "--old-date", old,
                    "--output", str(DATA_DIR / "outputs" / "neologisms" / f"eswiki_neologisms_phrasal_nouns_{new}_{old}.txt")
                ],
                outputs=[
                    DATA_DIR / "outputs" / "neologisms" / f"eswiki_neologisms_phrasal_nouns_{new}_{old}.txt",
                ],
            ),
        ],
    )

    stage4 = Stage(
        name="Occurrence Mapping",
        steps=[
            Step(
                name="neologism_occurrences_spacy",
                script="scripts/neologisms/neologism_occurrences_spacy.py",
                args=[
                    "--input", str(DATA_DIR / "outputs" / "filtered_dumps" / f"eswiki-{new}-pages-articles-ns0-no-redirects-clean.json"),
                    "--input-neologisms", str(DATA_DIR / "outputs" / "neologisms" / f"eswiki_neologisms_{new}_{old}.txt"),
                    "--date", new, 
                    "--old-date", old, 
                    "--output", str(DATA_DIR / "outputs" / "neologisms" / f"eswiki_neologisms_occurrences_{new}_{old}_spacy.json"),
                    *proc_args
                ],
                outputs=[
                    DATA_DIR / "outputs" / "neologisms" / f"eswiki_neologisms_occurrences_{new}_{old}_spacy.json",
                ],
            ),
            Step(
                name="phrasal_noun_occurrences",
                script="scripts/phrasal_nouns/phrasal_noun_occurrences.py",
                args=[
                    "--input", str(DATA_DIR / "outputs" / "filtered_dumps" / f"eswiki-{new}-pages-articles-ns0-no-redirects-clean.json"),
                    "--input-neologisms", str(DATA_DIR / "outputs" / "neologisms" / f"eswiki_neologisms_phrasal_nouns_{new}_{old}.txt"),
                    "--date", new, 
                    "--old-date", old, 
                    "--output", str(DATA_DIR / "outputs" / "neologisms" / f"eswiki_neologisms_phrasal_nouns_occurrences_{new}_{old}.json"),
                    *proc_args
                ],
                outputs=[
                    DATA_DIR / "outputs" / "neologisms" / f"eswiki_neologisms_phrasal_nouns_occurrences_{new}_{old}.json",
                ],
            ),
        ],
    )

    input_enrichment = (
        DATA_DIR
        / "outputs"
        / "neologisms"
        / f"eswiki_neologisms_occurrences_{new}_{old}_spacy.json"
    )
    output_enrichment = (
        DATA_DIR
        / "outputs"
        / "neologisms"
        / f"eswiki_neologisms_occurrences_{new}_{old}_spacy_enriched.json"
    )

    input_enrichment_pn = (
        DATA_DIR
        / "outputs"
        / "neologisms"
        / f"eswiki_neologisms_phrasal_nouns_occurrences_{new}_{old}.json"
    )
    output_enrichment_pn = (
        DATA_DIR
        / "outputs"
        / "neologisms"
        / f"eswiki_neologisms_phrasal_nouns_occurrences_{new}_{old}_enriched.json"
    )

    stage5 = Stage(
        name="Category Enrichment",
        steps=[
            Step(
                name="enrich_categories",
                script="scripts/neologisms/enrich_categories.py",
                args=[
                    "--input",
                    str(input_enrichment),
                    "--output",
                    str(output_enrichment),
                ],
                outputs=[output_enrichment],
            ),
            Step(
                name="enrich_categories_phrasal_nouns",
                script="scripts/neologisms/enrich_categories.py",
                args=[
                    "--input",
                    str(input_enrichment_pn),
                    "--output",
                    str(output_enrichment_pn),
                ],
                outputs=[output_enrichment_pn],
            ),
        ],
    )

    return [stage1, stage2, stage3, stage4, stage5]




def _fmt_elapsed(seconds: float) -> str:
    """Human-readable elapsed time."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    m = int(seconds // 60)
    s = seconds % 60
    if m < 60:
        return f"{m}m {s:.1f}s"
    h = m // 60
    m = m % 60
    return f"{h}h {m}m {s:.0f}s"


def _build_command(step: Step) -> list[str]:
    """Build the full command list for a pipeline step."""
    return [sys.executable, str(PROJECT_ROOT / step.script), *step.args]


def _outputs_exist(step: Step) -> bool:
    """Return True if **all** expected output files for *step* already exist."""
    return bool(step.outputs) and all(p.exists() for p in step.outputs)


def _run_step(step: Step, logger: logging.Logger) -> None:
    """Execute a single pipeline step as a subprocess."""
    cmd = _build_command(step)
    cmd_str = " ".join(cmd)

    logger.info("[%s] Running: %s", step.name, cmd_str)
    t0 = time.monotonic()

    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )

    elapsed = time.monotonic() - t0

    # Log stdout (at DEBUG so it goes to the log file, not spamming console)
    if result.stdout:
        for line in result.stdout.splitlines():
            logger.debug("[%s] stdout: %s", step.name, line)

    # Log stderr
    if result.stderr:
        for line in result.stderr.splitlines():
            logger.debug("[%s] stderr: %s", step.name, line)

    if result.returncode != 0:
        logger.error(
            "[%s] FAILED (exit code %d) after %s",
            step.name,
            result.returncode,
            _fmt_elapsed(elapsed),
        )
        # Log last lines of stderr at ERROR level for console visibility
        if result.stderr:
            for line in result.stderr.strip().splitlines()[-20:]:
                logger.error("[%s] stderr: %s", step.name, line)
        result.check_returncode()  # raises CalledProcessError
    else:
        logger.info(
            "[%s] Completed successfully in %s",
            step.name,
            _fmt_elapsed(elapsed),
        )


def run_stage(
    stage: Stage,
    *,
    logger: logging.Logger,
    skip_existing: bool,
) -> None:
    """Execute all steps in a pipeline stage."""
    logger.info("━" * 72)
    logger.info("▸ %s", stage.name)
    logger.info("━" * 72)

    steps_to_run: list[Step] = []
    for step in stage.steps:
        if skip_existing and _outputs_exist(step):
            logger.info(
                "[%s] Skipped — output(s) already exist: %s",
                step.name,
                ", ".join(str(p) for p in step.outputs),
            )
            continue
        steps_to_run.append(step)

    if not steps_to_run:
        logger.info("(all steps skipped)")
        return

    t_stage = time.monotonic()

    if stage.parallel and len(steps_to_run) > 1:
        _run_parallel(steps_to_run, logger)
    else:
        for step in steps_to_run:
            _run_step(step, logger)

    logger.info(
        "%s finished in %s",
        stage.name,
        _fmt_elapsed(time.monotonic() - t_stage),
    )


def _run_parallel(steps: Sequence[Step], logger: logging.Logger) -> None:
    """Run steps concurrently using threads."""
    errors: list[tuple[Step, BaseException]] = []

    with ThreadPoolExecutor(max_workers=len(steps)) as pool:
        future_to_step = {
            pool.submit(_run_step, step, logger): step for step in steps
        }
        for future in as_completed(future_to_step):
            step = future_to_step[future]
            exc = future.exception()
            if exc is not None:
                errors.append((step, exc))

    if errors:
        # Report all failures, then raise the first one to halt the pipeline
        for step, exc in errors:
            logger.error("[%s] Step failed: %s", step.name, exc)
        first_step, first_exc = errors[0]
        raise RuntimeError(
            f"Step '{first_step.name}' failed: {first_exc}"
        ) from first_exc




def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Neologism detection pipeline orchestrator.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--date",
        "--new-date",
        dest="new_date",
        default=None,
        help=(
            "New dump date (YYYYMMDD). "
            "If omitted, auto-detected as the latest dump in data/."
        ),
    )
    parser.add_argument(
        "--old-date",
        default=None,
        help=(
            "Old dump date (YYYYMMDD). "
            "If omitted, auto-detected as the second-latest dump in data/."
        ),
    )

    skip_group = parser.add_mutually_exclusive_group()
    skip_group.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip stages whose output files already exist (default).",
    )
    skip_group.add_argument(
        "--no-skip-existing",
        action="store_false",
        dest="skip_existing",
        help="Do not skip stages even if output files exist.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-run all stages (alias for --no-skip-existing).",
    )

    parser.add_argument(
        "--processes",
        type=int,
        default=None,
        help="Number of worker processes for spaCy scripts (passed through).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of Namespace 0 (article) pages processed during extraction.",
    )

    return parser.parse_args()




def main() -> int:
    args = parse_args()

    # Resolve --force as an alias
    skip_existing: bool = args.skip_existing and not args.force

    new_date: str | None = args.new_date
    old_date: str | None = args.old_date
    local_dates = detect_dump_dates()

    if new_date is None or old_date is None:
        print("Checking MediaWiki for new dumps...")
        remote_dates = []
        try:
            req = urllib.request.Request("https://dumps.wikimedia.org/eswiki/", headers={"User-Agent": "esdbpedia/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8")
            remote_dates = sorted(set(re.findall(r'href="(\d{8})/"', html)))
        except Exception as e:
            print(f"Warning: Could not fetch remote dumps: {e}")

        latest_remote = remote_dates[-1] if remote_dates else None
        latest_local = local_dates[-1] if local_dates else None

        if new_date is None:
            if latest_remote and (not latest_local or latest_remote > latest_local):
                new_date = latest_remote
                print(f"Found new remote dump: {new_date}")
            else:
                print("No new remote dump found. Exiting.")
                return 0

        if old_date is None:
            candidates = [d for d in local_dates if d < new_date]
            if candidates:
                old_date = candidates[-1]
            else:
                # Use the second latest from remote (remote_candidates is filtered to be older than new_date)
                remote_candidates = [d for d in remote_dates if d < new_date]
                if remote_candidates:
                    old_date = remote_candidates[-1]
                    print(f"No local old dump found. Using second latest from remote: {old_date}")
                else:
                    print(
                        "ERROR: Cannot determine --old-date. "
                        "Not enough previous local or remote dumps.",
                        file=sys.stderr,
                    )
                    return 1

    dates_to_download = []
    if new_date not in local_dates:
        dates_to_download.append(new_date)
    if old_date not in local_dates:
        if old_date not in dates_to_download:
            dates_to_download.append(old_date)

    logger = _setup_logging(new_date)

    logger.info("=" * 72)
    logger.info("CORPUS AND DATASETS PIPELINE")
    logger.info("=" * 72)
    logger.info("  New dump date : %s", new_date)
    logger.info("  Old dump date : %s", old_date)
    logger.info("  Skip existing : %s", skip_existing)
    logger.info("  Processes     : %s", args.processes or "(default)")
    logger.info("  Project root  : %s", PROJECT_ROOT)
    logger.info("=" * 72)


    if dates_to_download:
        try:
            sys.path.insert(0, str(PROJECT_ROOT / "backend"))
            from app.process_files.load_bz2 import _download_bz2, _get_plain_text, _preprocess_wikitext
            import bz2
            import xml.etree.ElementTree as ET
            import json
            import wikitextparser as wtp
            import re

            def _get_plain_text_with_tables(revision, ns):
                text_el = revision.find(f"{ns}text")
                if text_el is None or text_el.text is None:
                    return None
                
                preprocessed = _preprocess_wikitext(text_el.text)
                parsed = wtp.parse(preprocessed)
                
                for ref in parsed.get_tags("ref"):
                    try:
                        ref.contents = ""
                    except AttributeError:
                        pass
                
                for tpl in parsed.templates:
                    try:
                        tpl.string = ""
                    except Exception:
                        pass
                        
                try:
                    return parsed.plain_text().strip()
                except AttributeError:
                    return re.sub(r"\{\{[^}]*\}\}", "", preprocessed).strip()

            for target_date in dates_to_download:
                logger.info("━" * 72)
                logger.info("▸ Stage 0 — Download & Extract Datasets (%s)", target_date)
                logger.info("━" * 72)
                
                bz2_path = _download_bz2(target_date)
                
                out_pages = DATA_DIR / "outputs" / "filtered_dumps" / f"eswiki-{target_date}-pages-articles.json"
                out_clean = DATA_DIR / "outputs" / "filtered_dumps" / f"eswiki-{target_date}-pages-articles-clean.json"
                out_no_redir = DATA_DIR / "outputs" / "filtered_dumps" / f"eswiki-{target_date}-pages-articles-no-redirects-clean.json"
                out_ns0_no_redir = DATA_DIR / "outputs" / "filtered_dumps" / f"eswiki-{target_date}-pages-articles-ns0-no-redirects-clean.json"
                
                out_pages.parent.mkdir(parents=True, exist_ok=True)
                
                total = 0
                ns0_count = 0
                limit = args.limit
                with bz2.open(bz2_path, "rb") as stream:
                    context = iter(ET.iterparse(stream, events=("start", "end")))
                    _, root = next(context)
                    ns = root.tag.split("}")[0] + "}"
                    
                    with open(out_pages, "w", encoding="utf-8") as f_pages, \
                         open(out_clean, "w", encoding="utf-8") as f_clean, \
                         open(out_no_redir, "w", encoding="utf-8") as f_no_redir, \
                         open(out_ns0_no_redir, "w", encoding="utf-8") as f_ns0_no_redir:
                         
                        for event, elem in context:
                            if event == "end" and elem.tag == f"{ns}page":
                                ns_el = elem.find(f"{ns}ns")
                                namespace = int(ns_el.text) if ns_el is not None else -1
                                
                                redirect_el = elem.find(f"{ns}redirect")
                                is_redirect = redirect_el is not None
                                
                                title_el = elem.find(f"{ns}title")
                                title = title_el.text if title_el is not None else None
                                
                                revision = elem.find(f"{ns}revision")
                                if revision is not None:
                                    rev_id_el = revision.find(f"{ns}id")
                                    rev_id = rev_id_el.text if rev_id_el is not None else None
                                    
                                    # pages-articles.json (Cleaned, but keeping tables and maths)
                                    clean_with_tables = _get_plain_text_with_tables(revision, ns)
                                    if clean_with_tables is not None:
                                        raw_record = json.dumps({
                                            "revision_id": rev_id,
                                            "title": title,
                                            "text": clean_with_tables
                                        }, ensure_ascii=False)
                                        f_pages.write(raw_record + "\n")
                                    
                                    # pages-articles-clean.json (Strictly cleaned, no tables/maths)
                                    clean_text = _get_plain_text(revision, ns)
                                    if clean_text is not None:
                                        clean_record = json.dumps({
                                            "revision_id": rev_id,
                                            "title": title,
                                            "text": clean_text
                                        }, ensure_ascii=False)
                                        f_clean.write(clean_record + "\n")
                                        
                                        # pages-no-redirects-clean.json
                                        if not is_redirect:
                                            f_no_redir.write(clean_record + "\n")
                                            
                                        # pages-ns0-no-redirects-clean.json
                                        if namespace == 0 and not is_redirect:
                                            f_ns0_no_redir.write(clean_record + "\n")
                                            ns0_count += 1
                                            if limit is not None and ns0_count >= limit:
                                                logger.info("  Reached limit of %d Namespace 0 articles. Stopping extraction.", limit)
                                                break
                                
                                elem.clear()
                                root.clear()
                                total += 1
                                if total % 1000 == 0:
                                    logger.info("  Extracted %d pages...", total)

                logger.info("Stage 0 finished: generated 4 dataset variants for %s", target_date)
        except Exception as e:
            logger.error("Failed to download or extract datasets: %s", e)
            return 1


    pipeline = build_pipeline(new_date, old_date, processes=args.processes)

    t_total = time.monotonic()

    for stage in pipeline:
        try:
            run_stage(
                stage,
                logger=logger,
                skip_existing=skip_existing,
            )
        except (subprocess.CalledProcessError, RuntimeError) as exc:
            logger.error("Pipeline aborted: %s", exc)
            logger.error(
                "Total elapsed before failure: %s",
                _fmt_elapsed(time.monotonic() - t_total),
            )
            return 1


    total_elapsed = _fmt_elapsed(time.monotonic() - t_total)
    logger.info("=" * 72)
    logger.info("Pipeline completed successfully in %s", total_elapsed)
    logger.info("=" * 72)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
