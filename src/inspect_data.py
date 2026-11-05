
import gzip
import json
from collections import Counter
from pathlib import Path

GAME_ID = 114243

GAME_DIR = (
    Path("data/source/skillcorner/data/matches")
    / str(GAME_ID)
)

EVENTS_PATH = GAME_DIR / f"{GAME_ID}_dynamic_events.json"
TRACKING_PATH = GAME_DIR / f"{GAME_ID}_tracking_data.jsonl.gz"


def main():
    if not EVENTS_PATH.exists() or not TRACKING_PATH.exists():
        raise FileNotFoundError(
            "Missing data files. Check the SkillCorner download."
        )

    # Load labeled events
    with EVENTS_PATH.open("r", encoding="utf-8") as file:
        events = json.load(file)

    picks = events.get("picks", [])
    shots = events.get("shots", [])

    print("BEYOND THE SCREEN ASSIST | DATA INSPECTION")
    print("=" * 55)
    print(f"Game ID: {GAME_ID}")
    print(f"On-ball screens: {len(picks):,}")
    print(f"Shot events: {len(shots):,}")

    coverage_counts = Counter(
        pick.get("bhrDefType", "unknown")
        for pick in picks
    )

    print("\nDEFENSIVE COVERAGES")
    print("-" * 55)

    for coverage, count in coverage_counts.most_common():
        print(f"{str(coverage):15} {count:>5}")

    # Select five screens with valid frame indices
    sample_picks = sorted(
        (
            pick for pick in picks
            if isinstance(pick.get("frame"), int)
        ),
        key=lambda pick: pick["frame"]
    )[:5]

    target_frames = {pick["frame"] for pick in sample_picks}
    matched_frames = {}

    # Stream compressed tracking data to avoid
    # loading the entire game into memory.
    with gzip.open(TRACKING_PATH, "rt", encoding="utf-8") as file:
        for line in file:
            frame = json.loads(line)
            frame_idx = frame.get("frameIdx")

            if frame_idx in target_frames:
                matched_frames[frame_idx] = frame

            if len(matched_frames) == len(target_frames):
                break

    print("\nSCREEN / TRACKING ALIGNMENT")
    print("-" * 55)

    participant_fields = [
        "ballhandlerId",
        "screenerId",
        "ballhandlerDefId",
        "screenerDefId",
    ]

    for pick in sample_picks:
        frame_idx = pick["frame"]
        tracking = matched_frames.get(frame_idx)

        if tracking is None:
            print(f"Frame {frame_idx}: NOT FOUND")
            continue

        players = {
            player["playerId"]: player
            for player in (
                tracking.get("homePlayers", [])
                + tracking.get("awayPlayers", [])
            )
        }

        participant_ids = [
            pick.get(field) for field in participant_fields
        ]

        present_count = sum(
            player_id in players
            for player_id in participant_ids
        )

        detected_count = sum(
            players[player_id].get("isDetected") == 1
            for player_id in participant_ids
            if player_id in players
        )

        print(
            f"Frame {frame_idx}: "
            f"{present_count}/4 participants present | "
            f"{detected_count}/4 directly detected | "
            f"coverage={pick.get('bhrDefType')}"
        )

    print("\nInspection complete.")


if __name__ == "__main__":
    main()
