# PitchIQ

---

## Database
### Setup
Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
docker compose up -d
```

### Running
```bash
# start
docker compose up -d

# stop
docker compose stop

# stop and remove
docker compose down
```

### After changes
Re-run `docker compose up -d` if you edit `docker-compose.yml`.

---

## Backend
API: http://127.0.0.1:8000

### Setup
Database must already be running.

```bash
cd backend
py -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
```

Note: If using Mac instead of Windows, use:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
```

### Running
```bash
cd backend
.venv/Scripts/activate
python manage.py runserver
```

For Mac:
```bash
cd backend
source .venv/bin/activate
python manage.py runserver
```

### After changes
| What changed | Commands |
|--------------|----------|
| `requirements.txt` | `pip install -r requirements.txt` |
| `api/models.py` (or other models) | `python manage.py makemigrations` then `python manage.py migrate` |
| Existing migration files only | `python manage.py migrate` |

---

## Statcast data (ML)

### Overview
Collects historical Statcast pitch data (2021-2025 regular seasons) from Baseball Savant using `pybaseball`, saving raw chunks as Parquet files under `backend/ml/data/` (which is gitignored), then cleans them into model-ready tables.

### Quick start
From the `backend/` directory, with the backend requirements installed:

```bash
cd backend
python -m ml.collect_statcast --seasons 2024 --combine && python -m ml.clean_statcast
```

Each season takes about 20 seconds to download when Baseball Savant is responsive (it can be slower at busy times). One season is about 710k pitches and 20k pitcher games. Disk use for all 5 seasons is about 500 MB of raw chunks (about 1 GB with `--combine`, which also writes one file per season), plus about 120 MB of cleaned pitches and 6 MB of pitcher games. Cleaning reads one chunk at a time and only the columns it needs: all 5 seasons clean in about 15 seconds and peak around 4 GB of RAM, and the download step peaks around 3 GB while combining a season.

Collection is resumable: chunks that are already downloaded are skipped, and empty chunks write `.empty` marker files so they are not requested again.

### Running Data Collection
Run from the `backend/` directory:

```bash
cd backend
python -m ml.collect_statcast --combine
```

### Example Commands
```bash
# Pull single season
python -m ml.collect_statcast --seasons 2024 --combine

# Pull small explicit date range (test pull)
python -m ml.collect_statcast --start 2024-04-01 --end 2024-04-02 --combine

# Force re-download of existing cache
python -m ml.collect_statcast --start 2024-04-01 --end 2024-04-02 --force
```

### Running Tests
```bash
cd backend
python -m pytest ml
```

### Cleaning
Clean raw Statcast pitch data for model training. Run from the `backend/` directory:

```bash
cd backend
python -m ml.clean_statcast
```

#### Example Cleaning Commands
```bash
# Clean and export as CSV
python -m ml.clean_statcast --format csv

# Clean specific input files
python -m ml.clean_statcast --input ml/data/raw/statcast_2024-04-01_2024-04-02.parquet
```

#### Cleaning Rules
- **Regular Season Only**: Filters `game_type == "R"`.
- **Non-Pitch Rows Dropped**: Removes rows with null `pitch_type`, non-pitch types (`PO`, `IN`, `AB`, `UN`), pickoff/automatic descriptions, and missing `release_speed`.
- **Deduplication**: Deduplicates on `(game_pk, at_bat_number, pitch_number)` keeping the first occurrence.
- **Range Checks**: Drops measurements outside valid bounds (release speed 30-110 mph, spin rate 0-4000 rpm, balls 0-3, strikes 0-2, pitch number >= 1).

### Cleaned data schema

#### `clean/pitches`
Pitch-level cleaned Statcast records.

| Field | Type | Description |
|-------|------|-------------|
| pitcher | int | Pitcher ID (MLBAM) |
| pitcher_name | string | Pitcher name |
| game_pk | int | Game ID |
| game_date | date | Game date |
| game_year | int | Season year |
| game_type | string | Game type |
| home_team | string | Home team |
| away_team | string | Away team |
| inning | int | Inning number |
| inning_topbot | string | Top or bottom of inning |
| at_bat_number | int | At-bat number in game |
| pitch_number | int | Pitch number in at-bat |
| balls | int | Balls count |
| strikes | int | Strikes count |
| outs_when_up | int | Outs when up |
| p_throws | string | Pitcher throwing hand (R/L) |
| stand | string | Batter stance (R/L) |
| pitch_type | string | Pitch type code |
| pitch_name | string | Pitch type name |
| release_speed | float | Pitch velocity (mph) |
| effective_speed | float | Effective velocity (mph) |
| release_spin_rate | float | Spin rate (rpm) |
| spin_axis | float | Spin axis angle |
| release_pos_x | float | Horizontal release position |
| release_pos_y | float | Y release position |
| release_pos_z | float | Vertical release position |
| release_extension | float | Release extension (feet) |
| pfx_x | float | Horizontal movement |
| pfx_z | float | Vertical movement |
| plate_x | float | Horizontal plate location |
| plate_z | float | Vertical plate location |
| zone | int | Zone number |
| description | string | Pitch description |
| events | string | Plate appearance event |
| n_thruorder_pitcher | float | Times through batting order |
| pitcher_days_since_prev_game | float | Days since previous game |
| arm_angle | float | Arm angle (degrees) |

#### `clean/pitcher_games`
Aggregated pitcher game outings.

| Field | Type | Description |
|-------|------|-------------|
| pitcher | int | Pitcher ID (MLBAM) |
| pitcher_name | string | Pitcher name |
| game_pk | int | Game ID |
| game_date | date | Game date |
| game_year | int | Season year |
| p_throws | string | Pitcher throwing hand |
| pitch_count | int | Total pitches thrown |
| batters_faced | int | Batters faced (distinct ABs) |
| innings_pitched_approx | int | Innings pitched (distinct innings) |
| avg_velo | float | Average release speed (mph) |
| max_velo | float | Maximum release speed (mph) |
| min_velo | float | Minimum release speed (mph) |
| velo_std | float | Release speed standard deviation |
| avg_spin | float | Average spin rate (rpm) |
| max_spin | float | Maximum spin rate (rpm) |
| avg_extension | float | Average release extension |
| avg_release_pos_x | float | Average horizontal release position |
| avg_release_pos_z | float | Average vertical release position |
| fastball_pct | float | Fastball share (FF, SI, FC) |
| avg_fastball_velo | float | Average fastball velocity (mph) |
| max_fastball_velo | float | Maximum fastball velocity (mph) |
| days_rest | float | Days since the pitcher's previous outing in the same season (NaN for the first outing of each season) |

### Using the data in a model
`ml.datasets` loads the cleaned files as pandas DataFrames with plain numeric dtypes (text columns become `category`):

```python
from ml.datasets import load_pitcher_games, load_pitches, PITCHER_GAME_FEATURES

games = load_pitcher_games()               # one row per pitcher per game
X = games[PITCHER_GAME_FEATURES]           # numeric features, ready for scikit-learn
pitches = load_pitches(seasons=[2024], columns=["pitcher", "game_pk", "pitch_type", "release_speed"])
```

- `PITCHER_GAME_FEATURES` contains only numeric columns. Some have NaNs (`avg_spin`, fastball velo for pitchers who threw no fastballs, and `days_rest` for the first outing of a season), so use an imputer or a model that handles NaN, such as `HistGradientBoostingClassifier`.
- The ID columns (`pitcher`, `pitcher_name`, `game_pk`, `game_date`, `game_year`) are for joins and splits, not features. Split train and test by season or date, not randomly, so the same pitcher's later games don't leak into training.
- Each row describes the game it came from. To predict something about a future game, build features from earlier rows (for example `games.groupby("pitcher").shift(1)` or rolling windows).
- Very low velocity outings (`avg_velo` under about 75 mph, about 0.5% of rows) are mostly position players pitching; filter them if they matter for your target.
- `load_pitcher_games(sample=True)` loads a small committed sample (500 pitcher games from 2024, `backend/ml/sample/`) so code can be tried without downloading anything.

---

## Frontend

App: http://localhost:5173

### Setup (once)

```bash
cd frontend
npm install
```

### Running

```bash
cd frontend
npm run dev
```

### After changes
| What changed | Commands |
|--------------|----------|
| `package.json` | `npm install` |


### Login/Authentication Info
## Admin Login
To create an admin account:
```bash
cd backend
python manage.py createsuperuser
```
Then fill in info for username, email, and password.
Admin API: http://127.0.0.1:8000/admin

## Pitcher Login/Signup
Pitcher account signup and login can be done through the frontend app
