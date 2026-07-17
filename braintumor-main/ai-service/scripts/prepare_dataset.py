#!/usr/bin/env python
"""
scripts/prepare_dataset.py — CLI for dataset preparation and inspection.

Commands
--------
prepare     Run the full pipeline (validate → split → stats → metadata).
validate    Validate a raw dataset directory without splitting.
stats       Print statistics for a raw or processed dataset directory.
info        Print the saved dataset_info.json for a processed directory.

Run from ai-service/ with the venv active:
    python scripts/prepare_dataset.py prepare --raw-dir dataset/raw
    python scripts/prepare_dataset.py validate --raw-dir dataset/raw
    python scripts/prepare_dataset.py stats    --dir dataset/raw --full
    python scripts/prepare_dataset.py info     --dir dataset/processed
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure the ai-service root is on sys.path when called directly
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# ─── Colour helpers (no third-party dep) ─────────────────────────────────────
def _c(text: str, code: str) -> str:
    """Wrap *text* in ANSI *code* if stdout is a TTY."""
    if sys.stdout.isatty():
        return f"\033[{code}m{text}\033[0m"
    return text

ok   = lambda t: _c(t, "0;32")   # green
warn = lambda t: _c(t, "1;33")   # yellow
err  = lambda t: _c(t, "0;31")   # red
cyan = lambda t: _c(t, "0;36")   # cyan


def _pp(data: dict, indent: int = 2) -> str:
    return json.dumps(data, indent=indent, default=str)


# ─── Command handlers ─────────────────────────────────────────────────────────

def cmd_prepare(args: argparse.Namespace) -> int:
    from app.dataset import prepare_dataset

    print(cyan(f"\n→ Preparing dataset: {args.raw_dir}"))
    print(f"  Output   : {args.output_dir or 'settings.dataset_processed_dir'}")
    print(f"  Split    : train={args.train} / val={args.val} / test={args.test}")
    print(f"  Seed     : {args.seed}")
    print(f"  Overwrite: {args.overwrite}")
    print(f"  Full stats: {args.full_stats}\n")

    try:
        result = prepare_dataset(
            raw_dir=args.raw_dir,
            output_dir=args.output_dir or None,
            train_ratio=args.train,
            val_ratio=args.val,
            test_ratio=args.test,
            seed=args.seed,
            overwrite=args.overwrite,
            full_stats=args.full_stats,
        )
    except (ValueError, FileExistsError) as exc:
        print(err(f"\n✗ Preparation failed: {exc}"))
        return 1
    except Exception as exc:
        print(err(f"\n✗ Unexpected error: {exc}"))
        raise

    v = result["validation"]
    print(ok("✓ Validation passed"))
    print(f"  Classes   : {v['classes_found']}")
    print(f"  Total raw : {v['total_images']}")
    for cls, cnt in v["class_counts"].items():
        print(f"    {cls:20s}: {cnt}")

    sp = result["split"]
    print(ok("\n✓ Split complete"))
    for split_name, total in result["split"]["total_per_split"].items():
        print(f"  {split_name:6s}: {total}")

    print(ok(f"\n✓ Metadata saved → {result['metadata_path']}"))
    print(f"  Duration  : {result['duration_s']}s\n")

    if args.verbose:
        print(cyan("Full result:"))
        print(_pp(result))

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    from app.dataset import validate_dataset

    print(cyan(f"\n→ Validating: {args.raw_dir}\n"))

    result = validate_dataset(
        args.raw_dir,
        min_images_per_class=args.min_images,
    )

    status = ok("✓ VALID") if result.is_valid else err("✗ INVALID")
    print(f"  Status  : {status}")
    print(f"  Classes : {result.classes_found}")
    print(f"  Total   : {result.total_images}")
    print("")

    for cls, cnt in result.class_counts.items():
        print(f"  {cls:20s}: {cnt} images")

    if result.errors:
        print(err("\nErrors:"))
        for e in result.errors:
            print(err(f"  ✗ {e}"))

    if result.warnings:
        print(warn("\nWarnings:"))
        for w in result.warnings:
            print(warn(f"  ⚠ {w}"))

    print()
    return 0 if result.is_valid else 1


def cmd_stats(args: argparse.Namespace) -> int:
    from app.dataset.stats import compute_dataset_stats, compute_split_stats

    target = Path(args.dir)

    # If the directory contains train/val/test sub-dirs, show split stats too
    has_splits = all((target / s).is_dir() for s in ("train", "val", "test"))

    print(cyan(f"\n→ Statistics for: {target}"))
    print(f"  Full pixel stats: {args.full}\n")

    # Raw / flat directory stats
    stats = compute_dataset_stats(
        target,
        full=args.full,
        pixel_sample_size=args.pixel_samples,
        seed=args.seed,
    )

    print(f"  Total images : {stats['total_images']}")
    print(f"  Classes      : {stats['classes']}")
    print(f"  Balanced     : {ok('yes') if stats['is_balanced'] else warn('no')}")
    print(f"  Imbalance    : {stats['imbalance_ratio']:.2f}x\n")
    print("  Class distribution:")
    for cls in stats["classes"]:
        cnt  = stats["class_counts"].get(cls, 0)
        pct  = stats["class_distribution"].get(cls, 0) * 100
        bar  = "█" * int(pct / 2)
        print(f"    {cls:20s}: {cnt:5d}  ({pct:5.1f}%)  {bar}")

    if "pixel_stats" in stats:
        ps = stats["pixel_stats"]
        print(f"\n  Channel mean (RGB) : {ps['mean_rgb']}")
        print(f"  Channel std  (RGB) : {ps['std_rgb']}")
        print(f"  Pixel samples used : {ps['samples_used']}")

    if "dimension_stats" in stats:
        ds = stats["dimension_stats"]
        print(f"\n  Height  min/mean/max : {ds['height_min']} / {ds['height_mean']} / {ds['height_max']}")
        print(f"  Width   min/mean/max : {ds['width_min']} / {ds['width_mean']} / {ds['width_max']}")
        print(f"  All same size        : {ds['all_same_size']}")

    if has_splits:
        split_stats = compute_split_stats(target)
        print(cyan("\n  Split counts:"))
        for split_name in ("train", "val", "test"):
            counts = split_stats["splits"][split_name]
            total  = split_stats["totals"][split_name]
            detail = "  ".join(f"{c}:{n}" for c, n in counts.items())
            print(f"    {split_name:6s}: {total:5d}  [{detail}]")
        print(f"    {'grand total':6s}: {split_stats['grand_total']}")

    print()
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    from app.dataset.metadata import load_dataset_info

    info = load_dataset_info(args.dir)
    if info is None:
        print(err(f"\n✗ No dataset_info.json found in: {args.dir}"))
        return 1

    if args.json:
        print(_pp(info))
        return 0

    print(cyan(f"\n→ Dataset info: {args.dir}\n"))
    print(f"  Schema version : {info.get('schema_version')}")
    print(f"  Created        : {info.get('created_at')}")
    print(f"  Updated        : {info.get('updated_at')}")
    print(f"  Raw dir        : {info.get('raw_dir')}")
    print(f"  Processed dir  : {info.get('processed_dir')}")
    print(f"  Classes        : {info.get('classes')}")
    print(f"  Class→index    : {info.get('class_to_index')}")
    print(f"  Image size     : {info.get('image_size')}×{info.get('image_size')}")
    print(f"  Seed           : {info.get('seed')}")
    print(f"  Balanced       : {info.get('is_balanced')}  "
          f"(imbalance {info.get('imbalance_ratio'):.2f}x)")

    sp = info.get("total_per_split", {})
    print(f"\n  Split totals:")
    for split_name in ("train", "val", "test"):
        print(f"    {split_name:6s}: {sp.get(split_name, 'n/a')}")
    print(f"    {'total':6s}: {info.get('total_images', 'n/a')}")

    ratios = info.get("split_ratios", {})
    print(f"\n  Split ratios   : "
          f"train={ratios.get('train')}  "
          f"val={ratios.get('val')}  "
          f"test={ratios.get('test')}")

    ps = info.get("pixel_stats")
    if ps:
        print(f"\n  Pixel mean (RGB): {ps.get('mean_rgb')}")
        print(f"  Pixel std  (RGB): {ps.get('std_rgb')}")

    print()
    return 0


# ─── Argument parser ──────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prepare_dataset",
        description="Brain Tumour Detection — dataset preparation CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── prepare ───────────────────────────────────────────────────────────────
    p_prep = sub.add_parser("prepare", help="Full pipeline: validate → split → stats → metadata")
    p_prep.add_argument("--raw-dir",    default=None, help="Raw dataset root (default: settings)")
    p_prep.add_argument("--output-dir", default=None, help="Processed output root (default: settings)")
    p_prep.add_argument("--train",      type=float, default=0.70,  metavar="RATIO")
    p_prep.add_argument("--val",        type=float, default=0.15,  metavar="RATIO")
    p_prep.add_argument("--test",       type=float, default=0.15,  metavar="RATIO")
    p_prep.add_argument("--seed",       type=int,   default=42)
    p_prep.add_argument("--overwrite",  action="store_true", help="Wipe output dir if it exists")
    p_prep.add_argument("--full-stats", action="store_true", help="Compute pixel mean/std (slower)")
    p_prep.add_argument("--verbose",    action="store_true", help="Print full JSON result")

    # ── validate ──────────────────────────────────────────────────────────────
    p_val = sub.add_parser("validate", help="Validate raw dataset structure")
    p_val.add_argument("--raw-dir",    required=True,  help="Raw dataset root")
    p_val.add_argument("--min-images", type=int, default=10, help="Min images per class")

    # ── stats ─────────────────────────────────────────────────────────────────
    p_stats = sub.add_parser("stats", help="Print dataset statistics")
    p_stats.add_argument("--dir",           required=True, help="Dataset directory to analyse")
    p_stats.add_argument("--full",          action="store_true", help="Include pixel stats (reads images)")
    p_stats.add_argument("--pixel-samples", type=int, default=500, metavar="N")
    p_stats.add_argument("--seed",          type=int, default=42)

    # ── info ──────────────────────────────────────────────────────────────────
    p_info = sub.add_parser("info", help="Print saved dataset_info.json")
    p_info.add_argument("--dir",  required=True, help="Processed dataset directory")
    p_info.add_argument("--json", action="store_true", help="Emit raw JSON (machine-readable)")

    return parser


def main() -> int:
    parser  = _build_parser()
    args    = parser.parse_args()
    handler = {
        "prepare":  cmd_prepare,
        "validate": cmd_validate,
        "stats":    cmd_stats,
        "info":     cmd_info,
    }
    return handler[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
