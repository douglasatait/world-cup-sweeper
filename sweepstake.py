import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Sweepstake", layout="wide")

st.title("⚽ Sweepstake")

@st.cache_data
def load_data(file_path):
    return pd.read_csv(file_path)

def highlight_today(row):
    now = pd.Timestamp.now()

    match_time = row["Date (UK Kick-Off)"]

    if pd.isna(match_time):
        return [''] * len(row)

    diff = (match_time - now).total_seconds()

    # ✅ within next 24 hours
    if 0 <= diff <= 86400:
        return ['background-color: #ffd966; color: #666'] * len(row)

    # ✅ already started (past few hours)
    elif -7200 <= diff < 0:
        return ['background-color: #f4cccc; color: #666'] * len(row)
    
    elif diff < -7200:
        return ['background-color: #ffb5a6; color: #666'] * len(row)

    else:
        return [''] * len(row)
    
def compute_group_standings(fixtures):
    # Only use matches with scores
    results = fixtures.dropna(subset=["Score A", "Score B"]).copy()

    table = []

    for _, row in results.iterrows():
        team_a = row["team_a"]
        team_b = row["team_b"]
        goals_a = row["Score A"]
        goals_b = row["Score B"]
        group = row["group"]

        # Team A entry
        table.append({
            "Team": team_a,
            "Group": group,
            "P": 1,
            "W": int(goals_a > goals_b),
            "D": int(goals_a == goals_b),
            "L": int(goals_a < goals_b),
            "GF": goals_a,
            "GA": goals_b,
            "GD": goals_a - goals_b,
            "Pts": 3 if goals_a > goals_b else 1 if goals_a == goals_b else 0
        })

        # Team B entry
        table.append({
            "Team": team_b,
            "Group": group,
            "P": 1,
            "W": int(goals_b > goals_a),
            "D": int(goals_b == goals_a),
            "L": int(goals_b < goals_a),
            "GF": goals_b,
            "GA": goals_a,
            "GD": goals_b - goals_a,
            "Pts": 3 if goals_b > goals_a else 1 if goals_a == goals_b else 0
        })

    df = pd.DataFrame(table)

    standings = (
        df.groupby(["Group", "Team"])
        .sum(numeric_only=True)
        .reset_index()
    )

    standings = standings.sort_values(
        by=["Group", "Pts", "GD", "GF"],
        ascending=[True, False, False, False]
    )

    return standings

drop_cols = ["match_number", "date", "time_et", "time_local", "datetime_et", "country"]
keep_cols = ["Date (UK Kick-Off)", "Stage", "Group", "Team A", "Team B", "Venue", "City", "Score A", "Score B"]
draw = load_data("data/sweepstake.csv")
ranks = load_data("data/rankings.csv")
fixtures = load_data("data/world-cup-2026-schedule.csv").drop(columns=["status", "source"])
fixtures['Score A'] = fixtures['Score A'].astype('Int64')
fixtures['Score B'] = fixtures['Score B'].astype('Int64')
fixtures["datetime_et"] = pd.to_datetime(fixtures["date"] + " " + fixtures["time_et"])

mask_midnight = fixtures["time_et"] == "00:00"

fixtures.loc[mask_midnight, "datetime_et"] = (fixtures.loc[mask_midnight, "datetime_et"] + pd.Timedelta(days=1))
fixtures["datetime_london"] = fixtures["datetime_et"] + pd.Timedelta(hours=5)
fixtures["datetime_london"] = pd.to_datetime(fixtures["datetime_london"])
cols = ["datetime_london"] + [col for col in fixtures.columns if col != "datetime_london"]

fixtures = fixtures[cols]
fixtures = fixtures.drop(columns=drop_cols).sort_values("datetime_london")
fixtures.columns = keep_cols

draw_long = (
    draw.melt(
        id_vars="Name",
        value_vars=["Team 1", "Team 2", "Team 3"],
        value_name="Team"
    )
    .drop(columns=["variable"])
)

draw_long = draw_long.merge(
    ranks[["Team", "FIFA Rank"]],
    on="Team",
    how="left"
)

with st.sidebar:
    st.header("Filters")

    view_draw = st.checkbox("Show full draw")
    view_fixtures = st.checkbox("Show full fixture list")
    
    selected_players =st.multiselect(
        "Select player(s)",
        sorted(draw_long["Name"].unique()),
        default=["Doug"]
    )

    teams = sorted(draw_long["Team"].unique())
    selected_team = st.selectbox("Select a team", teams)



col1, col2 = st.columns(2)

with col1:
    st.subheader(f"Owner of {selected_team} :man_technologist:")
    team_view = draw_long[draw_long["Team"] == selected_team]
    st.dataframe(team_view, hide_index=True, use_container_width=True)

with col2:
    st.subheader("Selected Players :triumph:")
    player_view = draw[draw["Name"].isin(selected_players)]
    st.dataframe(player_view, hide_index=True, use_container_width=True)

if view_draw:
    st.subheader("Full Draw")
    
    search = st.text_input("Search team or player")

    filtered_draw = draw[
        draw["Team 1"].str.contains(search, case=False, na=False) |
        draw["Team 2"].str.contains(search, case=False, na=False) |
        draw["Team 3"].str.contains(search, case=False, na=False) |
        draw["Name"].str.contains(search, case=False, na=False) 
    ]

    st.dataframe(filtered_draw, hide_index=True, use_container_width=True)

st.subheader("📅 Fixture List")

if view_fixtures:
    
    show_upcoming = st.checkbox("Show only upcoming matches", value=True)
    search_fixtures_team = st.text_input("Search team")

    if show_upcoming:
        fixtures = fixtures[
        fixtures["Team A"].str.contains(search_fixtures_team, case=False, na=False) |
        fixtures["Team B"].str.contains(search_fixtures_team, case=False, na=False)
        ]
        fixtures = fixtures[fixtures["Date (UK Kick-Off)"] >= pd.Timestamp.now()]
        styled_fixtures = fixtures.style.apply(highlight_today, axis=1)
        st.dataframe(styled_fixtures, hide_index=True, use_container_width=True)    
    else:
        fixtures = fixtures[
        fixtures["Team A"].str.contains(search_fixtures_team, case=False, na=False) |
        fixtures["Team B"].str.contains(search_fixtures_team, case=False, na=False)
        ]
        styled_fixtures = fixtures.style.apply(highlight_today, axis=1)
        st.dataframe(styled_fixtures, hide_index=True, use_container_width=True)

else:
    # Get teams
    player_teams = draw_long[
        draw_long["Name"].isin(selected_players)
    ]["Team"].unique()

    # Filter fixtures
    player_fixtures = fixtures[
        fixtures["Team A"].isin(player_teams) |
        fixtures["Team B"].isin(player_teams)
    ].copy()

    if player_fixtures.empty:
        st.warning("No fixtures found for selected players")
        st.stop()

    st.write(f"Teams: {', '.join(sorted(player_teams))}")

    st.dataframe(
        player_fixtures.sort_values(by="Date (UK Kick-Off)"),
        hide_index=True,
        use_container_width=True
    )


st.subheader("🏆 Group Standings")

fixtures_standings = load_data("data/world-cup-2026-schedule.csv").drop(columns=["status", "source"])
standings = compute_group_standings(fixtures_standings)
groups = sorted(standings["Group"].unique())
NUM_COLS = 4  
for i in range(0, len(groups), NUM_COLS):
    cols = st.columns(NUM_COLS)

    for j, group in enumerate(groups[i:i+NUM_COLS]):
        with cols[j]:
            st.markdown(f"### Group {group}")

            group_df = standings[standings["Group"] == group].copy()
            group_df = group_df.reset_index(drop=True)

            st.dataframe(
                group_df,
                use_container_width=True,
                hide_index=True
            )