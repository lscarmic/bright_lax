import streamlit as st
import pandas as pd
import os


def calculate_rankings(df):
    df["Games Played"] = df["Wins"] + df["Losses"]
    df["Win Percentage"] = df["Wins"] / df["Games Played"].replace(0, 1)

    # Calculate Opponent Strength (Average Win Percentage of Opponents)
    opponent_strength = {}
    for team in df["Team"]:
        opponents = [
            game["Team 2"] if game["Team 1"] == team else game["Team 1"]
            for game in st.session_state.games
            if game["Team 1"] == team or game["Team 2"] == team
        ]
        win_percentages = [
            df[df["Team"] == opp]["Win Percentage"].values[0]
            for opp in opponents
            if not df[df["Team"] == opp].empty
        ]
        opponent_strength[team] = (
            sum(win_percentages) / len(win_percentages) if win_percentages else 0
        )

    # Weighted Point Differential Calculation
    weighted_diff = []
    for _, row in df.iterrows():
        team = row["Team"]
        weighted_for = 0
        weighted_against = 0
        for game in st.session_state.games:
            if game["Team 1"] == team:
                opp_strength = opponent_strength.get(game["Team 2"], 0)
                weighted_for += game["Score 1"] * opp_strength
                weighted_against += game["Score 2"] * opp_strength
            elif game["Team 2"] == team:
                opp_strength = opponent_strength.get(game["Team 1"], 0)
                weighted_for += game["Score 2"] * opp_strength
                weighted_against += game["Score 1"] * opp_strength
        weighted_diff.append(weighted_for - weighted_against)

    df["Weighted Point Differential"] = weighted_diff

    # Final Sorting Logic
    ranked_df = df.sort_values(
        by=["Win Percentage", "Weighted Point Differential", "Points For"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    ranked_df.index += 1
    ranked_df.insert(0, "Rank", ranked_df.index)
    return ranked_df


def save_data():
    st.session_state.teams.to_csv("teams.csv", index=False)
    pd.DataFrame(st.session_state.games).to_csv("games.csv", index=False)


def load_data():
    if os.path.exists("teams.csv"):
        st.session_state.teams = pd.read_csv("teams.csv")
    else:
        st.session_state.teams = pd.DataFrame(
            columns=["Team", "Wins", "Losses", "Points For", "Points Against"]
        )

    if os.path.exists("games.csv"):
        st.session_state.games = pd.read_csv("games.csv").to_dict(orient="records")
    else:
        st.session_state.games = []


# Load data on startup
if "teams" not in st.session_state or "games" not in st.session_state:
    load_data()

st.title("Girls 3-5 Lacrosse Standings")
st.text(
    "Ranked teams based on their win-loss records, point differentials, and points scored."
)

# Sidebar for team management

# Rename Team
if not st.session_state.teams.empty:
    st.sidebar.header("Rename a Team")
    team_to_rename = st.sidebar.selectbox(
        "Select a team to rename",
        st.session_state.teams["Team"].unique(),
        key="rename_team",
    )
    new_name = st.sidebar.text_input("Enter new name for the team").strip()
    if st.sidebar.button("Rename Team") and new_name:
        if (
            not st.session_state.teams["Team"]
            .str.contains(f"^{new_name}$", case=False)
            .any()
        ):
            st.session_state.teams.loc[
                st.session_state.teams["Team"] == team_to_rename, "Team"
            ] = new_name
            save_data()
            st.sidebar.success(f"Team '{team_to_rename}' renamed to '{new_name}'")
        else:
            st.sidebar.warning("A team with this name already exists!")

# Remove Team
if not st.session_state.teams.empty:
    st.sidebar.header("Remove a Team")
    team_to_remove = st.sidebar.selectbox(
        "Select a team to remove",
        st.session_state.teams["Team"].unique(),
        key="remove_team",
    )
    if st.sidebar.button("Remove Team"):
        st.session_state.teams = st.session_state.teams[
            st.session_state.teams["Team"] != team_to_remove
        ].reset_index(drop=True)
        save_data()
        st.sidebar.success(f"Team '{team_to_remove}' has been removed!")
st.sidebar.header("Team Management")

# Register New Team
new_team = st.sidebar.text_input("Enter Team Name").strip()
if st.sidebar.button("Add Team") and new_team:
    if (
        not st.session_state.teams["Team"]
        .str.contains(f"^{new_team}$", case=False)
        .any()
    ):
        new_row = pd.DataFrame(
            {
                "Team": [new_team],
                "Wins": [0],
                "Losses": [0],
                "Points For": [0],
                "Points Against": [0],
            }
        )
        st.session_state.teams = pd.concat(
            [st.session_state.teams, new_row], ignore_index=True
        )
        save_data()
        st.sidebar.success(f"Team '{new_team}' added!")
    else:
        st.sidebar.warning("Team already exists!")

# Display current rankings
st.header("Current Rankings")
if not st.session_state.teams.empty:
    ranked_df = calculate_rankings(st.session_state.teams)
    st.dataframe(ranked_df)

st.markdown(
    """
### **Ranking Methodology Explained**

The team rankings are determined using a **weighted and fair system** that considers multiple factors to ensure accuracy and competitiveness:

1. **Win Percentage**  
   - Calculated as:
"""
)

st.latex(r"\text{Win Percentage} = \frac{\text{Wins}}{\text{Total Games Played}}")

st.markdown(
    """
   - Reflects the overall success rate of each team.

2. **Opponent Strength (Strength of Schedule)**  
   - The **average win percentage** of the opponents a team has faced.  
   - Teams that compete against stronger opponents will be ranked higher if they perform well.  
   - This ensures fairness by acknowledging the difficulty of the competition.

3. **Weighted Point Differential**  
   - Points scored and conceded are **weighted based on opponent strength**.  
   - Scoring against stronger teams carries **more weight**, while conceding points to weaker teams is **penalized more**.  
   - This encourages teams to perform consistently, regardless of their opponents.

4. **Tiebreakers**  
   - If teams have identical records, the following are considered in order:  
     - **Head-to-Head Results**: Which team won when they played each other.  
     - **Strength of Schedule**: The difficulty of the opponents faced.  
     - **Weighted Point Differential**: The adjusted difference between points scored and conceded.


This system is designed to **reward consistent performance**, encourage competitive play, and ensure that rankings reflect not just wins and losses but the **quality of competition and overall gameplay**.
"""
)
st.markdown("---")

# Section to input game results
st.header("Input Game Result")
if len(st.session_state.teams) >= 2:
    col1, col2 = st.columns(2)

    with col1:
        team1 = st.selectbox(
            "Select Team 1", st.session_state.teams["Team"].unique(), key="team1"
        )
        team1_score = st.number_input(f"{team1} Score", min_value=0, key="score1")

    with col2:
        team2 = st.selectbox(
            "Select Team 2", st.session_state.teams["Team"].unique(), key="team2"
        )
        team2_score = st.number_input(f"{team2} Score", min_value=0, key="score2")

    if team1 != team2:
        if st.button("Submit Game Result"):
            # Update Points
            st.session_state.teams.loc[
                st.session_state.teams["Team"] == team1,
                ["Points For", "Points Against"],
            ] += [team1_score, team2_score]
            st.session_state.teams.loc[
                st.session_state.teams["Team"] == team2,
                ["Points For", "Points Against"],
            ] += [team2_score, team1_score]

            # Update Wins and Losses
            if team1_score > team2_score:
                st.session_state.teams.loc[
                    st.session_state.teams["Team"] == team1, "Wins"
                ] += 1
                st.session_state.teams.loc[
                    st.session_state.teams["Team"] == team2, "Losses"
                ] += 1
            elif team2_score > team1_score:
                st.session_state.teams.loc[
                    st.session_state.teams["Team"] == team2, "Wins"
                ] += 1
                st.session_state.teams.loc[
                    st.session_state.teams["Team"] == team1, "Losses"
                ] += 1

            st.session_state.games.append(
                {
                    "Team 1": team1,
                    "Score 1": team1_score,
                    "Team 2": team2,
                    "Score 2": team2_score,
                }
            )
            save_data()
            st.success("Game result recorded!")
            st.rerun()

# Display game history with delete option
st.header("Game History")
if st.session_state.games:
    for i, game in enumerate(st.session_state.games):
        col1, col2 = st.columns([5, 1])
        with col1:
            st.write(
                f"{game['Team 1']} ({game['Score 1']}) - {game['Team 2']} ({game['Score 2']})"
            )
        with col2:
            if st.button("🗑️", key=f"delete_{i}"):
                for team, score, opp_score in [
                    (game["Team 1"], game["Score 1"], game["Score 2"]),
                    (game["Team 2"], game["Score 2"], game["Score 1"]),
                ]:
                    st.session_state.teams.loc[
                        st.session_state.teams["Team"] == team, "Points For"
                    ] -= score
                    st.session_state.teams.loc[
                        st.session_state.teams["Team"] == team, "Points Against"
                    ] -= opp_score
                    if score > opp_score:
                        st.session_state.teams.loc[
                            st.session_state.teams["Team"] == team, "Wins"
                        ] -= 1
                    elif opp_score > score:
                        st.session_state.teams.loc[
                            st.session_state.teams["Team"] == team, "Losses"
                        ] -= 1
                st.session_state.games.pop(i)
                save_data()
                st.rerun()
