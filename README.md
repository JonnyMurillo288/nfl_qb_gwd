# NFL Quarterback Game Winning Drives (1999-2025)

Interactive Streamlit app displaying quarterback game-winning drive statistics.

https://nfl-qb-gwd.streamlit.app/

## Data Source

Data sourced from [`nfl_data_py`](https://github.com/nflverse/nfl_data_py), which provides play-by-play data from the NFL.

## How the Data is Generated

The `combine_data.sql` script processes raw play-by-play data to calculate GWD statistics:

1. **Identifies eligible drives** - Filters for drives in the final 3 minutes (180 seconds) of the 4th quarter where the offense is trailing by 8 points or fewer
2. **Assigns QB to each drive** - Uses the passer with the most pass attempts on that drive
3. **Labels success/failure** - A GWD is successful if the offense scores to tie or take the lead
4. **Aggregates by QB** - Calculates totals, success rates, and win percentages at both drive-level and game-level

## Running the App

```bash
cd interactive_tables
pip install -r requirements.txt
streamlit run app.py
```

## Known Issues / Limitations

- **No year breakdown** - Statistics are aggregated across all seasons (1999-2025) without the ability to filter or view by individual year
- **No team breakdown** - Data is QB-centric only; cannot filter or group by team
- **Legacy playoff format issues** - The `week >= 19` filter used to identify playoff games does not account for changes in NFL scheduling over the years (e.g., addition of Wild Card weekend, 17-game season shift). This may misclassify some games in earlier seasons.
