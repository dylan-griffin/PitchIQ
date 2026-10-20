"""
Clean historical Statcast pitch data for model training.
"""

import argparse
import logging
from pathlib import Path
import re
import sys
import pandas as pd

logger = logging.getLogger(__name__)

KEEP_COLUMNS = [
    "pitcher",
    "pitcher_name",
    "game_pk",
    "game_date",
    "game_year",
    "game_type",
    "home_team",
    "away_team",
    "inning",
    "inning_topbot",
    "at_bat_number",
    "pitch_number",
    "balls",
    "strikes",
    "outs_when_up",
    "p_throws",
    "stand",
    "pitch_type",
    "pitch_name",
    "release_speed",
    "effective_speed",
    "release_spin_rate",
    "spin_axis",
    "release_pos_x",
    "release_pos_y",
    "release_pos_z",
    "release_extension",
    "pfx_x",
    "pfx_z",
    "plate_x",
    "plate_z",
    "zone",
    "description",
    "events",
    "n_thruorder_pitcher",
    "pitcher_days_since_prev_game",
    "arm_angle",
]

REQUIRED_COLUMNS = [
    "pitcher",
    "game_pk",
    "game_date",
    "at_bat_number",
    "pitch_number",
    "pitch_type",
    "release_speed",
]


def clean_pitches(df):
    """Clean raw Statcast pitch data by filtering, normalizing types, and deduplicating."""
    df = df.copy()

    if "player_name" in df.columns and "pitcher_name" not in df.columns:
        df = df.rename(columns={"player_name": "pitcher_name"})

    missing_req = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_req:
        raise ValueError(f"Missing required columns: {missing_req}")

    for c in KEEP_COLUMNS:
        if c not in df.columns:
            df[c] = pd.NA

    # Filter regular season
    if "game_type" in df.columns:
        before = len(df)
        df = df[df["game_type"] == "R"]
        dropped = before - len(df)
        if dropped > 0:
            logger.info("Dropped %d rows: non-regular season (game_type != 'R')", dropped)

    # Filter null pitch_type
    before = len(df)
    df = df[df["pitch_type"].notna()]
    dropped = before - len(df)
    if dropped > 0:
        logger.info("Dropped %d rows: null pitch_type", dropped)

    # Filter non-pitch pitch_types
    non_pitch_types = {"PO", "IN", "AB", "UN"}
    before = len(df)
    df = df[~df["pitch_type"].astype(str).str.upper().isin(non_pitch_types)]
    dropped = before - len(df)
    if dropped > 0:
        logger.info("Dropped %d rows: non-pitch pitch_type (PO, IN, AB, UN)", dropped)

    # Filter non-pitch descriptions
    non_pitch_desc = {"pickoff_1b", "pickoff_2b", "pickoff_3b", "automatic_ball", "automatic_strike"}
    if "description" in df.columns:
        before = len(df)
        df = df[~df["description"].isin(non_pitch_desc)]
        dropped = before - len(df)
        if dropped > 0:
            logger.info("Dropped %d rows: non-pitch description", dropped)

    # Filter nulls in required columns
    before = len(df)
    df = df.dropna(subset=REQUIRED_COLUMNS)
    dropped = before - len(df)
    if dropped > 0:
        logger.info("Dropped %d rows: null values in required columns", dropped)

    # Range checks
    rs = pd.to_numeric(df["release_speed"], errors="coerce")
    before = len(df)
    valid_rs = (rs >= 30) & (rs <= 110)
    df = df[valid_rs]
    dropped = before - len(df)
    if dropped > 0:
        logger.info("Dropped %d rows: release_speed outside 30-110 mph", dropped)

    if "release_spin_rate" in df.columns:
        spin = pd.to_numeric(df["release_spin_rate"], errors="coerce")
        before = len(df)
        valid_spin = spin.isna() | ((spin >= 0) & (spin <= 4000))
        df = df[valid_spin]
        dropped = before - len(df)
        if dropped > 0:
            logger.info("Dropped %d rows: release_spin_rate outside 0-4000", dropped)

    if "balls" in df.columns:
        b = pd.to_numeric(df["balls"], errors="coerce")
        before = len(df)
        valid_b = b.isna() | ((b >= 0) & (b <= 3))
        df = df[valid_b]
        dropped = before - len(df)
        if dropped > 0:
            logger.info("Dropped %d rows: balls outside 0-3", dropped)

    if "strikes" in df.columns:
        s = pd.to_numeric(df["strikes"], errors="coerce")
        before = len(df)
        valid_s = s.isna() | ((s >= 0) & (s <= 2))
        df = df[valid_s]
        dropped = before - len(df)
        if dropped > 0:
            logger.info("Dropped %d rows: strikes outside 0-2", dropped)

    if "pitch_number" in df.columns:
        pn = pd.to_numeric(df["pitch_number"], errors="coerce")
        before = len(df)
        valid_pn = pn.isna() | (pn >= 1)
        df = df[valid_pn]
        dropped = before - len(df)
        if dropped > 0:
            logger.info("Dropped %d rows: pitch_number < 1", dropped)

    # Normalize types
    df["game_date"] = pd.to_datetime(df["game_date"]).dt.normalize()

    int_cols = ["pitcher", "game_pk", "game_year", "at_bat_number", "pitch_number", "balls", "strikes", "outs_when_up", "inning", "zone"]
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    float_cols = ["release_speed", "effective_speed", "release_spin_rate", "spin_axis", "release_pos_x", "release_pos_y", "release_pos_z", "release_extension", "pfx_x", "pfx_z", "plate_x", "plate_z", "arm_angle", "n_thruorder_pitcher", "pitcher_days_since_prev_game"]
    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")

    for col in df.columns:
        if col not in int_cols and col not in float_cols and col != "game_date":
            df[col] = df[col].astype("string").str.strip()

    if "pitch_type" in df.columns:
        df["pitch_type"] = df["pitch_type"].str.upper()

    # Deduplicate
    df = df.drop_duplicates(subset=["game_pk", "at_bat_number", "pitch_number"], keep="first")

    # Sort
    df = df.sort_values(["game_date", "game_pk", "at_bat_number", "pitch_number"]).reset_index(drop=True)

    # Keep only KEEP_COLUMNS in correct order
    cols_to_keep = [c for c in KEEP_COLUMNS if c in df.columns]
    df = df[cols_to_keep]

    return df


def validate_pitches(df):
    """Validate cleaned pitch data against schema and business rules."""
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' is missing.")
        if df[col].isna().any():
            raise ValueError(f"Required column '{col}' contains null values.")

    if df.duplicated(subset=["game_pk", "at_bat_number", "pitch_number"]).any():
        raise ValueError("Duplicate keys found for (game_pk, at_bat_number, pitch_number).")

    if "release_speed" in df.columns:
        rs = pd.to_numeric(df["release_speed"], errors="coerce")
        if ((rs < 30) | (rs > 110)).any():
            raise ValueError("release_speed outside valid range [30, 110].")

    if "release_spin_rate" in df.columns:
        spin = pd.to_numeric(df["release_spin_rate"], errors="coerce")
        valid = spin.isna() | ((spin >= 0) & (spin <= 4000))
        if not valid.all():
            raise ValueError("release_spin_rate outside valid range [0, 4000].")

    if "balls" in df.columns:
        b = pd.to_numeric(df["balls"], errors="coerce")
        valid_b = b.isna() | ((b >= 0) & (b <= 3))
        if not valid_b.all():
            raise ValueError("balls outside valid range [0, 3].")

    if "strikes" in df.columns:
        s = pd.to_numeric(df["strikes"], errors="coerce")
        valid_s = s.isna() | ((s >= 0) & (s <= 2))
        if not valid_s.all():
            raise ValueError("strikes outside valid range [0, 2].")

    if "pitch_number" in df.columns:
        pn = pd.to_numeric(df["pitch_number"], errors="coerce")
        if (pn < 1).any():
            raise ValueError("pitch_number must be >= 1.")


def aggregate_outings(df):
    """Aggregate pitch-level data into pitcher game outings."""
    outings = []
    for (pitcher, game_pk), group in df.groupby(["pitcher", "game_pk"]):
        game_date = group["game_date"].iloc[0]
        game_year = group["game_year"].iloc[0] if "game_year" in group.columns and pd.notna(group["game_year"].iloc[0]) else (game_date.year if pd.notna(game_date) else pd.NA)
        pitcher_name = group["pitcher_name"].iloc[0] if "pitcher_name" in group.columns else pd.NA
        p_throws = group["p_throws"].iloc[0] if "p_throws" in group.columns else pd.NA

        pitch_count = len(group)
        batters_faced = group["at_bat_number"].nunique()
        innings_pitched_approx = group["inning"].nunique()

        rs = group["release_speed"].dropna()
        avg_velo = rs.mean() if len(rs) > 0 else float("nan")
        max_velo = rs.max() if len(rs) > 0 else float("nan")
        min_velo = rs.min() if len(rs) > 0 else float("nan")
        velo_std = rs.std() if len(rs) > 1 else (0.0 if len(rs) == 1 else float("nan"))

        spin = group["release_spin_rate"].dropna() if "release_spin_rate" in group.columns else pd.Series(dtype=float)
        avg_spin = spin.mean() if len(spin) > 0 else float("nan")
        max_spin = spin.max() if len(spin) > 0 else float("nan")

        ext = group["release_extension"].dropna() if "release_extension" in group.columns else pd.Series(dtype=float)
        avg_extension = ext.mean() if len(ext) > 0 else float("nan")

        rpx = group["release_pos_x"].dropna() if "release_pos_x" in group.columns else pd.Series(dtype=float)
        avg_release_pos_x = rpx.mean() if len(rpx) > 0 else float("nan")

        rpz = group["release_pos_z"].dropna() if "release_pos_z" in group.columns else pd.Series(dtype=float)
        avg_release_pos_z = rpz.mean() if len(rpz) > 0 else float("nan")

        pt = group["pitch_type"] if "pitch_type" in group.columns else pd.Series(dtype=str)
        fb_mask = pt.isin(["FF", "SI", "FC"])
        fb_count = fb_mask.sum()
        fastball_pct = fb_count / pitch_count if pitch_count > 0 else 0.0

        fb_rs = group.loc[fb_mask, "release_speed"].dropna()
        avg_fastball_velo = fb_rs.mean() if len(fb_rs) > 0 else float("nan")
        max_fastball_velo = fb_rs.max() if len(fb_rs) > 0 else float("nan")

        outings.append({
            "pitcher": pitcher,
            "pitcher_name": pitcher_name,
            "game_pk": game_pk,
            "game_date": game_date,
            "game_year": game_year,
            "p_throws": p_throws,
            "pitch_count": pitch_count,
            "batters_faced": batters_faced,
            "innings_pitched_approx": innings_pitched_approx,
            "avg_velo": avg_velo,
            "max_velo": max_velo,
            "min_velo": min_velo,
            "velo_std": velo_std,
            "avg_spin": avg_spin,
            "max_spin": max_spin,
            "avg_extension": avg_extension,
            "avg_release_pos_x": avg_release_pos_x,
            "avg_release_pos_z": avg_release_pos_z,
            "fastball_pct": fastball_pct,
            "avg_fastball_velo": avg_fastball_velo,
            "max_fastball_velo": max_fastball_velo,
        })

    cols = [
        "pitcher", "pitcher_name", "game_pk", "game_date", "game_year", "p_throws",
        "pitch_count", "batters_faced", "innings_pitched_approx", "avg_velo", "max_velo",
        "min_velo", "velo_std", "avg_spin", "max_spin", "avg_extension", "avg_release_pos_x",
        "avg_release_pos_z", "fastball_pct", "avg_fastball_velo", "max_fastball_velo", "days_rest"
    ]

    outings_df = pd.DataFrame(outings)
    if outings_df.empty:
        return pd.DataFrame(columns=cols)

    outings_df = outings_df.sort_values(["pitcher", "game_date"]).reset_index(drop=True)

    outings_df["days_rest"] = outings_df.groupby("pitcher")["game_date"].diff().dt.days.astype("float64")

    outings_df = outings_df.sort_values(["pitcher", "game_date"]).reset_index(drop=True)
    return outings_df[cols]


def load_raw(raw_dir):
    """Load all raw Statcast chunk files from a directory.

    Combined files (statcast_<year>.parquet and *_combined.parquet) are skipped
    because they repeat the rows already in the chunk files.
    """
    raw_dir = Path(raw_dir)
    if not raw_dir.exists():
        return pd.DataFrame()

    chunk_files = [
        f for f in sorted(raw_dir.glob("statcast_*.parquet"))
        if "_combined" not in f.name and not re.match(r"statcast_\d{4}\.parquet$", f.name)
    ]

    if not chunk_files:
        logger.warning("No raw Statcast chunk files found in %s", raw_dir)
        return pd.DataFrame()

    logger.info("Loading %d raw chunk files from %s", len(chunk_files), raw_dir)
    dfs = [pd.read_parquet(f) for f in chunk_files]
    return pd.concat(dfs, ignore_index=True)


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Clean historical Statcast pitch data.")
    parser.add_argument("--input", nargs="+", help="Input files (Parquet or CSV)")
    parser.add_argument("--data-dir", type=str, default=str(Path(__file__).parent / "data"), help="Data directory")
    parser.add_argument("--format", choices=["parquet", "csv"], default="parquet", help="Output format")

    args = parser.parse_args(argv)
    data_dir = Path(args.data_dir)
    raw_dir = data_dir / "raw"
    clean_dir = data_dir / "clean"
    clean_dir.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame()
    if args.input:
        dfs = []
        for path_str in args.input:
            p = Path(path_str)
            if not p.exists():
                logger.error("Input file not found: %s", p)
                sys.exit(1)
            if p.suffix == ".csv":
                dfs.append(pd.read_csv(p))
            else:
                try:
                    dfs.append(pd.read_parquet(p))
                except Exception:
                    dfs.append(pd.read_csv(p))
        if dfs:
            df = pd.concat(dfs, ignore_index=True)
    else:
        df = load_raw(raw_dir)

    if df.empty:
        logger.error("No input data found to clean.")
        sys.exit(1)

    logger.info("Loaded raw data with %d rows", len(df))
    cleaned_df = clean_pitches(df)
    validate_pitches(cleaned_df)
    logger.info("Cleaned pitches: %d rows", len(cleaned_df))

    pitcher_games_df = aggregate_outings(cleaned_df)
    logger.info("Aggregated pitcher games: %d rows", len(pitcher_games_df))

    ext = "parquet" if args.format == "parquet" else "csv"
    pitches_path = clean_dir / f"pitches.{ext}"
    outings_path = clean_dir / f"pitcher_games.{ext}"

    if ext == "parquet":
        cleaned_df.to_parquet(pitches_path, index=False)
        pitcher_games_df.to_parquet(outings_path, index=False)
    else:
        cleaned_df.to_csv(pitches_path, index=False)
        pitcher_games_df.to_csv(outings_path, index=False)

    logger.info("Wrote cleaned pitches to %s and pitcher games to %s", pitches_path, outings_path)


if __name__ == "__main__":
    main()
