# nba_parlay_app.py

import streamlit as st
import pandas as pd
import numpy as np
import joblib
from itertools import combinations
from nba_api.stats.endpoints import scoreboardv2
from nba_api.stats.static import teams
import requests
from datetime import datetime
from geopy.distance import geodesic
from utils import get_team_info, calculate_travel_distance, get_live_odds
import os

# Suppress warnings from nba_api
import warnings
warnings.filterwarnings("ignore")

# Function Definitions

def get_today_games():
    today = datetime.today().strftime('%Y-%m-%d')
    try:
        scoreboard = scoreboardv2.ScoreboardV2(game_date=today, league_id='00')
        games = scoreboard.get_data_frames()[0]
        return games
    except Exception as e:
        st.error(f"Error fetching today's games: {e}")
        return pd.DataFrame()

def get_live_odds(api_key, sport='basketball_nba', region='us', markets='h2h,spreads,totals'):
    url = f'https://api.the-odds-api.com/v4/sports/{sport}/odds/'
    params = {
        'apiKey': api_key,
        'regions': region,
        'markets': markets,
        'oddsFormat': 'decimal',
        'dateFormat': 'iso'
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        odds_data = response.json()
        return odds_data
    else:
        st.error(f"Error fetching odds: {response.status_code}")
        return None

def prepare_bets_data(live_odds, teams_info):
    if not live_odds:
        return pd.DataFrame()
    
    # Initialize list to store bet entries
    bets = []
    
    for game in live_odds:
        game_id = game.get('id')
        sport_key = game.get('sport_key')
        home_team = game.get('home_team')
        away_team = game.get('away_team')
        bookmakers = game.get('bookmakers', [])
        
        # For each bookmaker, extract odds
        for bookmaker in bookmakers:
            title = bookmaker.get('title')
            markets = bookmaker.get('markets', [])
            
            for market in markets:
                market_key = market.get('key')
                outcomes = market.get('outcomes', [])
                
                for outcome in outcomes:
                    team = outcome.get('name')
                    price = outcome.get('price')
                    point = outcome.get('point', 0)  # For spreads/totals
                    
                    # Determine if it's home or away
                    if team == home_team:
                        bet_side = 'Home'
                    elif team == away_team:
                        bet_side = 'Away'
                    else:
                        bet_side = 'Other'
                    
                    if bet_side in ['Home', 'Away']:
                        bets.append({
                            'game_id': game_id,
                            'sport': sport_key,
                            'bookmaker': title,
                            'team': team,
                            'bet_type': market_key,
                            'price': price,
                            'point': point
                        })
    
    bets_df = pd.DataFrame(bets)
    
    # Add Travel Distance
    game_to_away = {}
    today_games = get_today_games()
    
    if 'VISITOR_TEAM_ID' in today_games.columns:
        visitor_team_id_col = 'VISITOR_TEAM_ID'
    else:
        st.error("No valid visitor team ID column found in today_games DataFrame.")
        return pd.DataFrame()
    
    team_id_to_full = teams_info.set_index('id')['full_name'].to_dict()
    
    for _, row in today_games.iterrows():
        visitor_team_id = row.get(visitor_team_id_col)
        if pd.isna(visitor_team_id):
            print(f"Missing visitor team ID for GAME_ID: {row.get('GAME_ID')}")
            continue
        visitor_full = team_id_to_full.get(visitor_team_id, visitor_team_id)
        game_to_away[row['GAME_ID']] = visitor_full
    
    bets_df['away_team'] = bets_df['game_id'].map(game_to_away)
    bets_df['travel_distance'] = bets_df.apply(
        lambda row: calculate_travel_distance(row['team'], row['away_team'], teams_info) 
        if row['bet_type'] == 'h2h' and row['team'] else 0, axis=1
    )
    
    # **Add Winning Column Based on Actual Outcomes**
    # Assuming you have a 'HOME_TEAM_SCORE' and 'VISITOR_TEAM_SCORE' in today_games.csv
    if 'HOME_TEAM_SCORE' in today_games.columns and 'VISITOR_TEAM_SCORE' in today_games.columns:
        score_mapping = today_games.set_index('GAME_ID')[['HOME_TEAM_SCORE', 'VISITOR_TEAM_SCORE']].to_dict('index')
        def determine_winner(row):
            scores = score_mapping.get(row['game_id'], {})
            home_score = scores.get('HOME_TEAM_SCORE', 0)
            visitor_score = scores.get('VISITOR_TEAM_SCORE', 0)
            if row['team'] == team_id_to_full.get(row.get('HOME_TEAM_ID')):
                return 1 if home_score > visitor_score else 0
            elif row['team'] == team_id_to_full.get(row.get('VISITOR_TEAM_ID')):
                return 1 if visitor_score > home_score else 0
            else:
                return 0  # Default to loss if team not found
        
        bets_df['winning'] = bets_df.apply(determine_winner, axis=1)
    else:
        st.warning("'HOME_TEAM_SCORE' or 'VISITOR_TEAM_SCORE' columns not found. Creating dummy 'winning' column.")
        # **Create Dummy Winning Column for Testing**
        bets_df['winning'] = (bets_df['price'] > 1.5).astype(int)  # Example dummy rule
    
    return bets_df

def load_model(model_path='models/nba_bet_model.pkl'):
    try:
        model = joblib.load(model_path)
        return model
    except Exception as e:
        st.error(f"Error loading model: {e}")
        return None

def kelly_criterion(prob, odds, bankroll):
    b = odds - 1
    return ((prob * b - (1 - prob)) / b) * bankroll if b != 0 else 0

# Streamlit Application

# Title and Description
st.title("🏀 NBA Parlay Betting Model - Real-Time")
st.write("""
This application leverages real-time NBA game data and live betting odds to suggest profitable parlays with up to **3 legs** and cumulative odds around **+100**.
""")

# Sidebar for API Key Input
st.sidebar.header("API Configuration")
API_KEY = st.sidebar.text_input("Enter your **The Odds API** Key:", type='password')

if not API_KEY:
    st.warning("Please enter your **The Odds API** key to fetch live betting odds.")
    st.stop()

# Load Data
teams_info = get_team_info()
live_odds = get_live_odds(API_KEY)

if live_odds is None:
    st.error("Failed to fetch live odds. Please check your API key and try again.")
    st.stop()

bets_df = prepare_bets_data(live_odds, teams_info)

if bets_df.empty:
    st.write("No available bets for today.")
    st.stop()

# Add Travel Distance and Winning
# (Already handled in prepare_bets_data)
# bets_df = add_travel_distance(bets_df, teams_info)

# Display Available Bets
st.header("📊 Available Bets")
st.write("Below are the available NBA bets with predicted probabilities:")

# Load Model
model = load_model()
if model is None:
    st.stop()

# Feature Engineering for Predictions
# Ensure features match those used during model training
bets_df['price_log'] = bets_df['price'].apply(lambda x: np.log(x) if x > 0 else 0)
bets_df['is_home'] = bets_df['bet_type'].apply(lambda x: 1 if x == 'h2h' else 0)

required_features = ['price_log', 'point', 'travel_distance', 'is_home']
for feature in required_features:
    if feature not in bets_df.columns:
        bets_df[feature] = 0  # Fill missing features with default value

X = bets_df[required_features].fillna(0)
try:
    bets_df['predicted_prob'] = model.predict_proba(X)[:,1]
except Exception as e:
    st.error(f"Error during prediction: {e}")
    st.stop()

# Display Bets with Predictions
st.dataframe(
    bets_df[['game_id', 'team', 'bookmaker', 'bet_type', 'price', 'point', 'travel_distance', 'predicted_prob']]
)

# User Selection of Bets
st.header("🎯 Select Your Bets for Parlay")

# Allow users to select up to 3 bets
selected_indices = st.multiselect(
    "Choose up to 3 bets for your parlay:",
    options=bets_df.index.tolist(),
    format_func=lambda x: f"Game {bets_df.loc[x, 'game_id']}: {bets_df.loc[x, 'team']} @ {bets_df.loc[x, 'bookmaker']} | Odds: {bets_df.loc[x, 'price']} | Predicted Prob: {bets_df.loc[x, 'predicted_prob']:.2f}"
)

# Limit selection to 3
if len(selected_indices) > 3:
    st.error("You can select up to 3 bets only.")
    selected_indices = selected_indices[:3]

# Display Selected Bets
if selected_indices:
    st.subheader("🔍 Selected Bets Predictions")
    selected_bets = bets_df.loc[selected_indices].copy()
    st.table(selected_bets[['game_id', 'team', 'bookmaker', 'bet_type', 'price', 'point', 'travel_distance', 'predicted_prob']])

    # Generate Parlays
    st.subheader("💡 Generated Parlays")
    max_legs = 3
    target_odds = 2.00  # Decimal odds for +100
    margin = 0.10  # Allow ±10% variation

    def generate_parlays(bets, max_legs=3, target_odds=2.00, margin=0.10):
        parlays = []
        for r in range(1, max_legs+1):
            for parlay in combinations(bets.itertuples(index=False), r):
                cumulative_odds = np.prod([bet.price for bet in parlay])
                if target_odds * (1 - margin) <= cumulative_odds <= target_odds * (1 + margin):
                    # Calculate cumulative probability (assuming independence)
                    cumulative_prob = np.prod([bet.predicted_prob for bet in parlay])
                    parlays.append({
                        'parlay': ', '.join([f"{bet.team} @ {bet.bookmaker}" for bet in parlay]),
                        'legs': r,
                        'cumulative_odds': round(cumulative_odds, 2),
                        'cumulative_prob': round(cumulative_prob, 4)
                    })
        return parlays

    parlays = generate_parlays(selected_bets, max_legs, target_odds, margin)

    if parlays:
        parlays_df = pd.DataFrame(parlays)
        st.table(parlays_df)
    else:
        st.write("No parlays generated within the specified odds range.")

    # Simulate Betting
    st.subheader("💸 Simulate Betting on Parlays")
    stake = st.number_input("Enter your stake for each parlay (e.g., $10):", min_value=1, value=10)

    if st.button("Calculate Potential Returns"):
        if parlays:
            parlays_df['potential_return'] = parlays_df['cumulative_odds'] * stake
            st.table(parlays_df[['parlay', 'legs', 'cumulative_odds', 'cumulative_prob', 'potential_return']])
        else:
            st.write("No parlays available to simulate.")

    # Risk Management: Kelly Criterion
    st.subheader("🔒 Risk Management: Kelly Criterion")
    bankroll = st.number_input("Enter your current bankroll (e.g., $1000):", min_value=1, value=1000)

    if st.button("Calculate Kelly Bet Sizes"):
        if parlays:
            parlays_df['kelly_bet_size'] = parlays_df.apply(
                lambda row: kelly_criterion(row['cumulative_prob'], row['cumulative_odds'], bankroll) 
                if row['cumulative_prob'] > (1 / row['cumulative_odds']) else 0, axis=1
            )
            st.table(parlays_df[['parlay', 'legs', 'cumulative_odds', 'cumulative_prob', 'kelly_bet_size']])
        else:
            st.write("No parlays available for Kelly Criterion calculation.")

# Footer
st.markdown("""
---
*This is a **proof-of-concept** application for demonstrating an NBA parlay betting model using real-time data. For real-world usage, integrate comprehensive data sources, enhance the model with more features, and implement robust risk management strategies.*
""")
