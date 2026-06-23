import math
import random

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

team_aliases = {
    "United States": "USA",
}

def canonicalize_team_name(name):
    if not isinstance(name, str):
        return name
    normalized = name.strip()
    return team_aliases.get(normalized, normalized)

team_columns = ["Team 1", "Team 2", "Team 3"]
for col in team_columns:
    if col in draw.columns:
        draw[col] = draw[col].apply(canonicalize_team_name)

ranks["FIFA Rank"] = pd.to_numeric(ranks["FIFA Rank"], errors="coerce")
ranks["rank_pct"] = ranks["FIFA Rank"].rank(pct=True, method="max")
ranks["FIFA Rank"] = ranks["FIFA Rank"].astype("Int64")
rank_pct_map = ranks.set_index("Team")["rank_pct"].to_dict()
rank_int_map = ranks.set_index("Team")["FIFA Rank"].to_dict()
fixtures = load_data("data/world-cup-2026-schedule.csv").drop(columns=["status", "source"])
fixtures['Score A'] = fixtures['Score A'].astype('Int64')
fixtures['Score B'] = fixtures['Score B'].astype('Int64')
fixtures["datetime_et"] = pd.to_datetime(fixtures["date"] + " " + fixtures["time_et"])

for col in ["team_a", "team_b"]:
    if col in fixtures.columns:
        fixtures[col] = fixtures[col].apply(canonicalize_team_name)

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

    rank = rank_pct_map.get(team_name)
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


def _team_rating(team: str) -> float:
    pct = rank_pct_map.get(team)
    if pd.isna(pct):
        return 0.5
    return 1.0 - float(pct)


def _match_outcome_probs(home_team: str, away_team: str) -> tuple[float, float, float]:
    rating_home = _team_rating(home_team)
    rating_away = _team_rating(away_team)
    diff = rating_home - rating_away
    win_prob = 1 / (1 + math.exp(-diff * 4))
    draw_prob = 0.2
    return win_prob * (1 - draw_prob), draw_prob, (1 - win_prob) * (1 - draw_prob)


def _sample_match_outcome(home_team: str, away_team: str) -> str:
    home_win_prob, draw_prob, away_win_prob = _match_outcome_probs(home_team, away_team)
    wager = random.random()
    if wager < home_win_prob:
        return "home"
    if wager < home_win_prob + draw_prob:
        return "draw"
    return "away"


def _sample_goals(outcome: str) -> tuple[int, int]:
    if outcome == "home":
        home_goals = random.randint(1, 3)
        away_goals = random.randint(0, max(home_goals - 1, 0))
    elif outcome == "away":
        away_goals = random.randint(1, 3)
        home_goals = random.randint(0, max(away_goals - 1, 0))
    else:
        goals = random.randint(0, 2)
        home_goals = away_goals = goals
    return home_goals, away_goals


def _add_match_result(stats: pd.DataFrame, group: str, team: str, goals_for: int, goals_against: int, points: int):
    idx = (group, team)
    if idx not in stats.index:
        return
    stats.at[idx, "Played"] += 1
    stats.at[idx, "GF"] += goals_for
    stats.at[idx, "GA"] += goals_against
    stats.at[idx, "GD"] += goals_for - goals_against
    stats.at[idx, "Points"] += points


def _build_group_stats(fixtures_df: pd.DataFrame) -> pd.DataFrame:
    group_stage = fixtures_df[fixtures_df["Stage"] == "Group Stage"].copy()
    index = []
    for group in sorted(group_stage["Group"].dropna().unique()):
        teams = set(group_stage[group_stage["Group"] == group]["Team A"]) | set(
            group_stage[group_stage["Group"] == group]["Team B"]
        )
        for team in sorted(team for team in teams if isinstance(team, str) and team.strip()):
            index.append((group, team))

    stats = pd.DataFrame(
        0,
        index=pd.MultiIndex.from_tuples(index, names=["Group", "Team"]),
        columns=["Points", "GF", "GA", "GD", "Played"],
    )
    completed = group_stage.dropna(subset=["Score A", "Score B"])
    for _, row in completed.iterrows():
        group = row["Group"]
        if pd.isna(group):
            continue
        team_a = row["Team A"]
        team_b = row["Team B"]
        score_a = int(row["Score A"])
        score_b = int(row["Score B"])
        if score_a > score_b:
            points_a, points_b = 3, 0
        elif score_a < score_b:
            points_a, points_b = 0, 3
        else:
            points_a = points_b = 1

        _add_match_result(stats, group, team_a, score_a, score_b, points_a)
        _add_match_result(stats, group, team_b, score_b, score_a, points_b)

    return stats


def _pending_group_matches(fixtures_df: pd.DataFrame) -> list[dict]:
    group_stage = fixtures_df[fixtures_df["Stage"] == "Group Stage"].copy()
    pending = group_stage[group_stage["Score A"].isna() & group_stage["Score B"].isna()]
    return pending[["Group", "Team A", "Team B"]].to_dict("records")


def _group_ranking_df(stats_df: pd.DataFrame) -> pd.DataFrame:
    ranking = (
        stats_df.reset_index()
        .assign(RankPriority=lambda frame: frame["Team"].map(lambda t: 1.0 - rank_pct_map.get(t, 1.0)))
        .sort_values(
            by=["Group", "Points", "GD", "GF", "RankPriority"],
            ascending=[True, False, False, False, False]
        )
    )
    ranking["GroupRank"] = ranking.groupby("Group").cumcount() + 1
    return ranking


def _deterministic_qualifiers(stats_df: pd.DataFrame) -> tuple[set[str], pd.DataFrame]:
    ranking = _group_ranking_df(stats_df)
    qualifier_set = set(ranking[ranking["GroupRank"] <= 2]["Team"].tolist())
    third_place = ranking[ranking["GroupRank"] == 3].copy()
    best_thirds = (
        third_place
        .sort_values(
            by=["Points", "GD", "GF", "RankPriority"],
            ascending=[False, False, False, False]
        )
        .head(8)["Team"].tolist()
    )
    qualifier_set.update(best_thirds)
    return qualifier_set, ranking


def compute_advancement_predictions(fixtures_df: pd.DataFrame, simulations: int = 1200, base_stats: pd.DataFrame | None = None) -> pd.DataFrame:
    if base_stats is None:
        base_stats = _build_group_stats(fixtures_df)
    pending_matches = _pending_group_matches(fixtures_df)
    teams = sorted(base_stats.index.get_level_values("Team").unique())

    advance_counts = {team: 0 for team in teams}
    total_samples = 1
    if pending_matches:
        total_samples = simulations
        random.seed(42)
        for _ in range(total_samples):
            snapshot = base_stats.copy()
            for match in pending_matches:
                outcome = _sample_match_outcome(match["Team A"], match["Team B"])
                home_goals, away_goals = _sample_goals(outcome)
                if outcome == "home":
                    points_home, points_away = 3, 0
                elif outcome == "away":
                    points_home, points_away = 0, 3
                else:
                    points_home = points_away = 1
                _add_match_result(snapshot, match["Group"], match["Team A"], home_goals, away_goals, points_home)
                _add_match_result(snapshot, match["Group"], match["Team B"], away_goals, home_goals, points_away)
            qualifiers, _ = _deterministic_qualifiers(snapshot)
            for team in qualifiers:
                advance_counts[team] += 1
    else:
        qualifiers, _ = _deterministic_qualifiers(base_stats)
        for team in qualifiers:
            advance_counts[team] += 1

    folded = base_stats.reset_index()
    folded["FIFA Rank"] = folded["Team"].map(lambda team: rank_int_map.get(team, pd.NA))
    folded["Advance %"] = folded["Team"].map(lambda team: (advance_counts.get(team, 0) / max(1, total_samples)) * 100)
    def _status_label(chance: float) -> str:
        if chance >= 99.5:
            return "Qualified"
        if chance <= 0.5:
            return "Eliminated"
        return "In play"
    folded["Status"] = folded["Advance %"].apply(_status_label)
    folded["Advance %"] = folded["Advance %"].round(1)
    return folded.sort_values(by=["Group", "Advance %"], ascending=[True, False])


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
group_stats = _build_group_stats(fixtures)
predictions_df = compute_advancement_predictions(fixtures, simulations=1200, base_stats=group_stats)
current_ranking = _group_ranking_df(group_stats)
third_place_df = current_ranking[current_ranking["GroupRank"] == 3].copy()
third_place_df = third_place_df.merge(
    predictions_df[["Team", "Advance %", "Status", "FIFA Rank"]],
    on="Team",
    how="left",
    suffixes=("", "")
)
third_place_df = third_place_df.sort_values(by="Advance %", ascending=False)
third_place_display = third_place_df.copy()
third_place_display["Advance %"] = third_place_display["Advance %"].apply(lambda x: f"{x:,.1f}%")

tabs = st.tabs([
    "Highlights",
    "Fixture Explorer",
    "Sweepstake Draw",
    "Group Standings",
    "Predictions"
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

with tabs[4]:
    st.subheader("Advancement Predictions")
    st.markdown("Simulation-based chances combine the current group standings with projected outcomes for the remaining matches.")
    if predictions_df.empty:
        st.info("No prediction data available yet.")
    else:
        predictions_display = predictions_df.copy()
        predictions_display["Advance %"] = predictions_display["Advance %"].apply(lambda x: f"{x:,.1f}%")
        st.dataframe(
            predictions_display[["Group", "Team", "FIFA Rank", "Points", "GD", "GF", "Advance %", "Status"]],
            use_container_width=True,
            hide_index=True
        )
        st.markdown("### Current third-placed teams")
        if third_place_display.empty:
            st.info("No third-place data available yet.")
        else:
            st.dataframe(
                third_place_display[["Group", "Team", "Points", "GD", "GF", "Advance %", "Status"]],
                use_container_width=True,
                hide_index=True
            )
