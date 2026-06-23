import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Sweepstake", layout="wide")

st.title("⚽ Sweepstake")
st.markdown("Use the tabs to jump between the next fixtures, the full schedule, the draw colours, and the group standings.")

@st.cache_data
def load_data(file_path):
    return pd.read_csv(file_path)

def convert_seconds(seconds):
    seconds = int(max(seconds, 0)) 
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"

def highlight_today(row):
    now = pd.Timestamp.now(tz="Europe/London").tz_localize(None)

    match_time = row["Date (UK Kick-Off)"]

    if pd.isna(match_time):
        return [''] * len(row)

    diff = (match_time - now).total_seconds()

    if 0 <= diff <= 86400:
        return ['background-color: #ffd966; color: #666'] * len(row)

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

def get_upcoming_fixtures_with_players(fixtures, draw_long):
    now = pd.Timestamp.now(tz="Europe/London").tz_localize(None)

    fixtures = fixtures.copy()
    fixtures["Date (UK Kick-Off)"] = pd.to_datetime(fixtures["Date (UK Kick-Off)"])

    upcoming = fixtures[
        (fixtures["Date (UK Kick-Off)"] >= now) &
        (fixtures["Date (UK Kick-Off)"] <= now + pd.Timedelta(hours=24))
    ].copy()

    if upcoming.empty:
        return upcoming

    team_to_players = (
        draw_long.groupby("Team")["Name"]
        .apply(lambda x: sorted(x.unique()))
        .to_dict()
    )

    def get_players(row):
        players_a = team_to_players.get(row["Team A"], [])
        players_b = team_to_players.get(row["Team B"], [])

        all_players = sorted(set(players_a + players_b))
        return ", ".join(all_players)

    upcoming["Players"] = upcoming.apply(get_players, axis=1)

    return upcoming

drop_cols = ["match_number", "date", "time_et", "time_local", "datetime_et", "country"]
keep_cols = ["Date (UK Kick-Off)", "Stage", "Group", "Team A", "Team B", "Venue", "City", "Score A", "Score B"]
draw = load_data("data/sweepstake.csv")
ranks = load_data("data/rankings.csv")

ranks["FIFA Rank"] = pd.to_numeric(ranks["FIFA Rank"], errors="coerce")
rank_values = ranks["FIFA Rank"]
ranks["rank_pct"] = ranks["FIFA Rank"].rank(pct=True, method="max")
ranks["FIFA Rank"] = rank_values.astype("Int64")
team_rank_map = ranks.set_index("Team")["rank_pct"].to_dict()
fixtures = load_data("data/world-cup-2026-schedule.csv").drop(columns=["status", "source"])
fixtures['Score A'] = fixtures['Score A'].astype('Int64')
fixtures['Score B'] = fixtures['Score B'].astype('Int64')
fixtures["datetime_et"] = pd.to_datetime(fixtures["date"] + " " + fixtures["time_et"])

mask_midnight = fixtures["time_et"] == "00:00"

fixtures.loc[mask_midnight, "datetime_et"] = (fixtures.loc[mask_midnight, "datetime_et"] + pd.Timedelta(days=1))
fixtures["datetime_et"] = pd.to_datetime(
    fixtures["date"] + " " + fixtures["time_et"]
)

fixtures["datetime_et"] = fixtures["datetime_et"].dt.tz_localize("US/Eastern")

fixtures["datetime_london"] = (
    fixtures["datetime_et"]
    .dt.tz_convert("Europe/London")
    .dt.tz_localize(None)
)

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
draw_long["FIFA Rank"] = draw_long["FIFA Rank"].astype("Int64")

def _get_contrast_color(hex_color: str) -> str:
    red = int(hex_color[1:3], 16)
    green = int(hex_color[3:5], 16)
    blue = int(hex_color[5:7], 16)
    brightness = (red * 299 + green * 587 + blue * 114) / 1000
    return "#000000" if brightness > 160 else "#ffffff"

def _team_rank_color(team_name: str) -> str:
    if not isinstance(team_name, str):
        return ""

    rank = team_rank_map.get(team_name)
    if pd.isna(rank):
        return ""

    try:
        rank_value = float(rank)
    except (TypeError, ValueError):
        return ""

    normalized = 1.0 - rank_value
    normalized = max(0.0, min(1.0, normalized))
    rgba = plt.cm.RdYlGn(normalized)
    hex_color = mcolors.to_hex(rgba)
    contrast = _get_contrast_color(hex_color)
    return f"background-color: {hex_color}; color: {contrast}"

def style_team_columns(df: pd.DataFrame, team_columns: list[str]):
    existing_columns = [col for col in team_columns if col in df.columns]
    if not existing_columns:
        return df

    def _style_column(column: pd.Series) -> pd.Series:
        if column.name in existing_columns:
            return column.map(_team_rank_color)
        return pd.Series([""] * len(column), index=column.index)

    return df.style.apply(_style_column, axis=0)


with st.sidebar:
    st.header("Filters & context")
    st.caption("Highlight the players and teams you care about.")
    selected_players = st.multiselect(
        "Player(s)",
        sorted(draw_long["Name"].unique()),
        default=["Doug"],
        help="Show fixtures and draw entries for these players.",
        label_visibility="visible"
    )

    teams = sorted(draw_long["Team"].unique())
    selected_team = st.selectbox(
        "Inspect a team", 
        teams,
        help="See who owns this country in the sweepstake along with their ranking.",
        label_visibility="visible"
    )

player_teams = draw_long[draw_long["Name"].isin(selected_players)]["Team"].unique()
player_fixtures = fixtures[
    fixtures["Team A"].isin(player_teams) | fixtures["Team B"].isin(player_teams)
].copy()
player_fixtures = player_fixtures.sort_values(by="Date (UK Kick-Off)")

team_view = draw_long[draw_long["Team"] == selected_team]
player_view = draw[draw["Name"].isin(selected_players)]
today_matches = get_upcoming_fixtures_with_players(fixtures, draw_long)

tabs = st.tabs([
    "Highlights",
    "Fixture Explorer",
    "Sweepstake Draw",
    "Group Standings"
])

with tabs[0]:
    st.subheader("Next 24 Hours Fixtures")
    st.markdown("Fixtures are grouped by the UK kickoff time so you can track the busiest window.")
    if today_matches.empty:
        st.info("No matches in the next 24 hours. Check back later!")
    else:
        now = pd.Timestamp.now(tz="Europe/London").tz_localize(None)
        upcoming_display = today_matches.copy()
        upcoming_display["KO Countdown"] = ((upcoming_display["Date (UK Kick-Off)"] - now).dt.total_seconds().apply(convert_seconds))
        st.dataframe(
            upcoming_display[[
                "Date (UK Kick-Off)", "KO Countdown", "Team A", "Team B", "Players"
            ]],
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    st.subheader("Player & Team Snapshot")
    if len(player_teams):
        st.caption(f"Selected players own: {', '.join(sorted(player_teams))}")
    else:
        st.caption("No teams assigned to the selected players yet.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"### {selected_team} ownership")
        st.dataframe(
            style_team_columns(team_view, ["Team"]),
            hide_index=True,
            use_container_width=True
        )
    with col2:
        st.markdown("### Selected Players")
        st.dataframe(
            style_team_columns(player_view, ["Team 1", "Team 2", "Team 3"]),
            hide_index=True,
            use_container_width=True
        )

with tabs[1]:
    st.subheader("Fixture Explorer")
    st.markdown("Search across the master fixture list, then toggle between upcoming or all fixtures.")
    search_fixtures_team = st.text_input("Filter fixtures by team", key="fixture_search")
    show_upcoming = st.checkbox("Show only upcoming fixtures", value=True, key="fixture_upcoming")

    fixture_view = fixtures[
        fixtures["Team A"].str.contains(search_fixtures_team, case=False, na=False) |
        fixtures["Team B"].str.contains(search_fixtures_team, case=False, na=False)
    ]
    if show_upcoming:
        now = pd.Timestamp.now(tz="Europe/London").tz_localize(None)
        fixture_view = fixture_view[fixture_view["Date (UK Kick-Off)"] >= now]

    if fixture_view.empty:
        st.warning("No fixtures matched your filters.")
    else:
        styled_fixtures = fixture_view.style.apply(highlight_today, axis=1)
        st.dataframe(styled_fixtures, hide_index=True, use_container_width=True)

with tabs[2]:
    st.subheader("Sweepstake Draw")
    st.markdown("Colour coding reflects FIFA ranking percentile — greener teams are ranked higher.")
    search_draw = st.text_input("Search team or player", key="draw_search")
    filtered_draw = draw[
        draw["Team 1"].str.contains(search_draw, case=False, na=False) |
        draw["Team 2"].str.contains(search_draw, case=False, na=False) |
        draw["Team 3"].str.contains(search_draw, case=False, na=False) |
        draw["Name"].str.contains(search_draw, case=False, na=False)
    ]
    styled_draw = style_team_columns(filtered_draw, ["Team 1", "Team 2", "Team 3"])
    st.dataframe(styled_draw, hide_index=True, use_container_width=True)

with tabs[3]:
    st.subheader("Group Standings")
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
