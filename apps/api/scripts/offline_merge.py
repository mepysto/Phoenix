"""
Offline merge job for batch deduplication of existing events.

Usage:
    python -m scripts.offline_merge --dry-run              # Preview without changes
    python -m scripts.offline_merge --chunk-size 500       # Run with custom chunk size
    python -m scripts.offline_merge --since 2025-12-01     # Process events since date
    python -m scripts.offline_merge --scope active         # Only active events
    python -m scripts.offline_merge --types earthquake,flood  # Specific event types
"""

import argparse
import asyncio
import sys
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(__file__).rsplit("/scripts", 1)[0])

from src.core.config import settings
from src.models.event import EventType
from src.services.dedup.offline_merge_service import (
    OfflineMergeConfig,
    OfflineMergeService,
    OfflineMergeStats,
)


def get_database_url() -> str:
    return settings.database_url.replace("postgresql://", "postgresql+asyncpg://")


def parse_event_types(types_str: str | None) -> list[EventType] | None:
    if not types_str:
        return None
    types = []
    for t in types_str.split(","):
        t = t.strip().lower()
        try:
            types.append(EventType(t))
        except ValueError:
            print(f"[WARNING] Unknown event type: {t}")
    return types if types else None


def parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        print(f"[ERROR] Invalid date format: {date_str}. Use ISO format (YYYY-MM-DD)")
        sys.exit(1)


def print_stats(stats: OfflineMergeStats, dry_run: bool) -> None:
    prefix = "[DRY-RUN] " if dry_run else ""

    print()
    print("=" * 60)
    print(f"{prefix}Offline Merge Results")
    print("=" * 60)
    print(f"  Groups found:       {stats.groups_found}")
    print(f"  Events scanned:     {stats.scanned}")
    print(f"  Merges applied:     {stats.merges_applied}")
    print(f"  Sources relinked:   {stats.sources_relinked}")
    print(f"  Duplicates marked:  {stats.duplicates_marked}")
    print(f"  Groups skipped:     {stats.skipped}")
    print()

    if stats.errors:
        print(f"[WARNING] {len(stats.errors)} error(s) occurred:")
        for error in stats.errors[:10]:
            print(f"  - {error}")
        if len(stats.errors) > 10:
            print(f"  ... and {len(stats.errors) - 10} more")
        print()

    if dry_run:
        print("[INFO] This was a dry run. No changes were made.")
        print("[INFO] Remove --dry-run to apply changes.")
    else:
        if stats.merges_applied > 0:
            print("[SUCCESS] Merge job completed successfully!")
        else:
            print("[INFO] No duplicates found to merge.")


async def run_merge(
    dry_run: bool = True,
    chunk_size: int = 1000,
    scope: str = "all",
    since: datetime | None = None,
    event_types: list[EventType] | None = None,
    radius_meters: int = 50_000,
    window_hours: int = 48,
    max_group_size: int = 200,
    progress_log_every: int = 100,
) -> OfflineMergeStats:
    database_url = get_database_url()
    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("=" * 60)
    print("Phoenix Offline Merge Job")
    print("=" * 60)
    print(f"Database: {database_url.split('@')[1] if '@' in database_url else 'local'}")
    print(f"Mode:     {'DRY-RUN (preview only)' if dry_run else 'LIVE (will modify data)'}")
    print(f"Scope:    {scope}")
    if since:
        print(f"Since:    {since.isoformat()}")
    if event_types:
        print(f"Types:    {', '.join(t.value for t in event_types)}")
    print()

    config = OfflineMergeConfig(
        chunk_size=chunk_size,
        fuzzy_radius_meters=radius_meters,
        fuzzy_window_hours=window_hours,
        max_group_size=max_group_size,
        progress_log_every=progress_log_every,
        dry_run=dry_run,
    )

    async with async_session() as session:
        service = OfflineMergeService(session, config)
        print("[INFO] Starting offline merge job...")
        stats = await service.run(
            scope=scope,  # type: ignore[arg-type]
            since=since,
            event_types=event_types,
        )

    await engine.dispose()
    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Offline merge job for batch deduplication of existing events",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m scripts.offline_merge --dry-run
  python -m scripts.offline_merge --chunk-size 500
  python -m scripts.offline_merge --since 2025-12-01
  python -m scripts.offline_merge --scope active --types earthquake,flood
        """,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview changes without modifying data (default: False)",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Number of events to process per batch (default: 1000)",
    )

    parser.add_argument(
        "--scope",
        choices=["all", "active", "inactive"],
        default="all",
        help="Scope of events to process (default: all)",
    )

    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Process only events created after this date (ISO format: YYYY-MM-DD)",
    )

    parser.add_argument(
        "--types",
        type=str,
        default=None,
        help="Comma-separated list of event types to process (e.g., earthquake,flood)",
    )

    parser.add_argument(
        "--radius",
        type=int,
        default=50_000,
        help="Fuzzy matching radius in meters (default: 50000)",
    )

    parser.add_argument(
        "--window",
        type=int,
        default=48,
        help="Fuzzy matching time window in hours (default: 48)",
    )

    parser.add_argument(
        "--max-group-size",
        type=int,
        default=200,
        help="Maximum group size before skipping (default: 200)",
    )

    parser.add_argument(
        "--progress-every",
        type=int,
        default=100,
        help="Log progress every N groups (default: 100)",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    since = parse_date(args.since)
    event_types = parse_event_types(args.types)

    stats = asyncio.run(
        run_merge(
            dry_run=args.dry_run,
            chunk_size=args.chunk_size,
            scope=args.scope,
            since=since,
            event_types=event_types,
            radius_meters=args.radius,
            window_hours=args.window,
            max_group_size=args.max_group_size,
            progress_log_every=args.progress_every,
        )
    )

    print_stats(stats, args.dry_run)


if __name__ == "__main__":
    main()
