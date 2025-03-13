import streamlit as st
import pandas as pd
import os


def calculate_rankings(df):
    df["Point Differential"] = df["Points For"] - df["Points Against"]
    ranked_df = df.sort_values(
        by=["Wins", "Point Differential", "Points For"], ascending=[False, False, False]
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

# Display current rankings
st.header("Current Rankings")
if not st.session_state.teams.empty:
    ranked_df = calculate_rankings(st.session_state.teams)
    st.dataframe(ranked_df)

# Display game history with delete option
st.header("Game History")
if st.session_state.games:
    for i, game in enumerate(st.session_state.games):
        col1, col2 = st.columns([5, 1])
        with col1:
            st.write(
                f"{game['Team 1']} ({game['Score 1']}) vs {game['Team 2']} ({game['Score 2']})"
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

# Reset option in the sidebar
if st.sidebar.button("Reset All Data"):
    st.session_state.teams = pd.DataFrame(
        columns=["Team", "Wins", "Losses", "Points For", "Points Against"]
    )
    st.session_state.games = []
    save_data()
    st.sidebar.success("All data has been reset.")
