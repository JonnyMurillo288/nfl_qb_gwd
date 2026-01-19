import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="NFL Game Winning Drives",
    page_icon="🏈",
    layout="wide"
)

# Column rename mapping for intuitive names
COLUMN_RENAMES = {
    'passer_player_name': 'Quarterback',
    'total_gwd_attempts': 'Total GWD Attempts',
    'successful_gwd_attempts': 'Successful GWDs',
    'pct_successful_gwd': 'GWD Success %',
    'games_with_gwd_attempt': 'Games w/ GWD Attempt',
    'games_won_with_gwd_attempt': 'Games Won (w/ Attempt)',
    'pct_won_when_gwd_attempt': 'Win % (w/ Attempt)',
    'games_with_successful_gwd': 'Games w/ Successful GWD',
    'games_won_after_successful_gwd': 'Games Won (After Success)',
    'pct_won_after_successful_gwd': 'Win % (After Success)'
}


@st.cache_data
def load_data():
    """Load and process the CSV files."""
    gwd_regular = pd.read_csv('./game_winning_drives/game_winning_drives_1999_2025_regular_season_qbs.csv')
    gwd_playoffs = pd.read_csv('./game_winning_drives/game_winning_drives_1999_2025_post_season_qbs.csv')

    # Add season type column
    gwd_regular['Season Type'] = 'Regular Season'
    gwd_playoffs['Season Type'] = 'Playoffs'

    # Rename columns
    gwd_regular = gwd_regular.rename(columns=COLUMN_RENAMES)
    gwd_playoffs = gwd_playoffs.rename(columns=COLUMN_RENAMES)

    # Combine datasets
    combined = pd.concat([gwd_regular, gwd_playoffs], ignore_index=True)

    # Get all unique quarterbacks
    all_qbs = sorted(combined['Quarterback'].dropna().unique().tolist())

    return gwd_regular, gwd_playoffs, combined, all_qbs


def format_percentage(df, pct_columns):
    """Format percentage columns as percentages."""
    df = df.copy()
    for col in pct_columns:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f"{x*100:.1f}%" if pd.notna(x) and x != '' else '')
    return df


def filter_by_players(df, selected_players):
    """Filter dataframe by selected players."""
    if selected_players:
        return df[df['Quarterback'].isin(selected_players)]
    return df


def display_table(df, pct_columns, sort_key, order_key, default_sort_col='Total GWD Attempts'):
    """Display a formatted dataframe with sort options."""
    if df.empty:
        st.info("No data to display with current filters.")
        return

    sort_col = st.selectbox(
        "Sort by",
        options=df.columns.tolist(),
        index=df.columns.tolist().index(default_sort_col) if default_sort_col in df.columns.tolist() else 0,
        key=sort_key
    )
    sort_order = st.radio("Order", ["Descending", "Ascending"], key=order_key, horizontal=True)

    df_sorted = df.sort_values(sort_col, ascending=(sort_order == "Ascending"))

    st.dataframe(
        format_percentage(df_sorted, pct_columns),
        use_container_width=True,
        hide_index=True
    )
    st.caption(f"Showing {len(df_sorted)} rows")


def main():
    st.title("NFL Quarterback Game Winning Drives (1999-2025)")
    # st.markdown("Interactive data tables for quarterback game-winning drive statistics")
    st.markdown("What QBs are the most clutch? Find out here!")

    # A game winning drive attempt is a drive within the last 3 minutes of the 4th quarter that a team is down by less than 7 points
    # If at the end of the drive the team ties the game up or takes the lead, success
    # If they fail to do so, fail

    # Edge cases
    # - If the team takes the lead and then proceeds to lose it: 
    #   - Will calculate this differently
    # - If the team takes the lead, loses it, and then comes back again:
    #   - Do not duplicate

    # I think for the purpose of the stat and "being clutch", it should be cumulative, since the offense can't control a defense blowing it.

    with st.expander("Game-Winning Drive (GWD) Definition"):
        st.markdown("""
        A **Game-Winning Drive (GWD) attempt** is defined as an offensive drive that meets **all** of the following criteria:

        - Occurs in the **final 3 minutes of the 4th quarter**
        - The offense is **trailing**
        - The deficit is **one score or fewer (8 points)**

        A GWD attempt is considered:

        - **Successful** if the offense **scores to tie or take the lead**
        - **Unsuccessful** if the offense **fails to do so**
        - If the score starts tied, it is **not successful unless the offense takes the lead**

        A QB can get a successful GWD even if the team ultimately loses the game, as long as they took the lead in the drive that ended within the last 3 minutes.

        Use the **sidebar filters** to customize the data displayed below.
        """)

    # Load data
    gwd_regular, gwd_playoffs, combined, all_qbs = load_data()

    pct_columns = ['GWD Success %', 'Win % (w/ Attempt)', 'Win % (After Success)']

    # Sidebar filters
    st.sidebar.header("Filters")
    st.sidebar.markdown("Use the filters below to customize the data displayed.")
    st.sidebar.markdown("Leave player selection empty to include all quarterbacks. Select multiple QBs to compare.")
    
    # Season type selection
    st.sidebar.subheader("Season Type")
    season_choice = st.sidebar.radio(
        "Select data to view",
        options=["Both", "Regular Season Only", "Playoffs Only"],
        key='season_choice'
    )

    # Player selection
    st.sidebar.subheader("Player Filter")
    selected_players = st.sidebar.multiselect(
        "Select quarterbacks to view",
        options=all_qbs,
        default=[],
        placeholder="All quarterbacks (leave empty)",
        key='player_select'
    )

    # Minimum attempts filter
    st.sidebar.subheader("Minimum Attempts")
    min_attempts = st.sidebar.slider(
        "Minimum GWD Attempts",
        min_value=0,
        max_value=int(combined['Total GWD Attempts'].max()),
        value=0,
        key='min_attempts'
    )

    # Apply filters based on season choice
    if season_choice == "Both":
        # Show all three tables: Combined, Regular Season, Playoffs
        tab1, tab2, tab3 = st.tabs(["Combined", "Regular Season", "Playoffs"])

        with tab1:
            st.header("Combined: Regular Season + Playoffs")

            filtered = combined[combined['Total GWD Attempts'] >= min_attempts].copy()
            filtered = filter_by_players(filtered, selected_players)

            # Reorder columns to put Season Type after Quarterback
            cols = filtered.columns.tolist()
            cols.remove('Season Type')
            cols.insert(1, 'Season Type')
            filtered = filtered[cols]

            display_table(filtered, pct_columns, 'sort_combined', 'order_combined')

        with tab2:
            st.header("Regular Season")

            filtered = gwd_regular[gwd_regular['Total GWD Attempts'] >= min_attempts].copy()
            filtered = filter_by_players(filtered, selected_players)
            filtered = filtered.drop(columns=['Season Type'])

            display_table(filtered, pct_columns, 'sort_reg', 'order_reg')

        with tab3:
            st.header("Playoffs")

            filtered = gwd_playoffs[gwd_playoffs['Total GWD Attempts'] >= min_attempts].copy()
            filtered = filter_by_players(filtered, selected_players)
            filtered = filtered.drop(columns=['Season Type'])

            display_table(filtered, pct_columns, 'sort_post', 'order_post')

    elif season_choice == "Regular Season Only":
        st.header("Regular Season Game Winning Drives")

        filtered = gwd_regular[gwd_regular['Total GWD Attempts'] >= min_attempts].copy()
        filtered = filter_by_players(filtered, selected_players)
        filtered = filtered.drop(columns=['Season Type'])

        display_table(filtered, pct_columns, 'sort_reg_only', 'order_reg_only')

    else:  # Playoffs Only
        st.header("Playoffs Game Winning Drives")

        filtered = gwd_playoffs[gwd_playoffs['Total GWD Attempts'] >= min_attempts].copy()
        filtered = filter_by_players(filtered, selected_players)
        filtered = filtered.drop(columns=['Season Type'])

        display_table(filtered, pct_columns, 'sort_post_only', 'order_post_only')

    st.markdown("""
                ---
                ### Statistics Included

                The data below includes:
                - Total GWD attempts
                - Successful GWDs
                - Win percentage in games with a GWD attempt
                - Win percentage after a successful GWD

                Statistics are separated into **Regular Season** and **Playoffs**, with an option to view **combined results**.

                """)

    # Footer
    st.markdown("---")
    st.markdown("Data: `nfl_data_py` Game Winning Drives 1999-2025")


if __name__ == "__main__":
    main()
