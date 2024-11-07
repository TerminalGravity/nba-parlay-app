import pandas as pd
from utils import get_team_info, calculate_travel_distance, get_live_odds
import os
from dotenv import load_dotenv

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
    
    # Merge with teams_info to get team IDs or other info if needed
    # For simplicity, we assume team names match
    return bets_df

def add_travel_distance(bets_df, teams_info):
    # Create a mapping from game_id to away team
    game_to_away = {}
    today_games = pd.read_csv('data/today_games.csv')
    
    available_columns = today_games.columns.tolist()
    print("Available columns in today_games:", available_columns)
    
    # Use VISITOR_TEAM_ID to get team name
    if 'VISITOR_TEAM_ID' in today_games.columns:
        visitor_team_id_col = 'VISITOR_TEAM_ID'
    else:
        raise KeyError("No valid visitor team ID column found in today_games DataFrame.")
    
    print(f"Using '{visitor_team_id_col}' as the visitor team ID column.")
    
    # Create a mapping from team_id to full_name
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
    # You'll need to adjust based on your actual data structure
    
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
        print("Warning: 'HOME_TEAM_SCORE' or 'VISITOR_TEAM_SCORE' columns not found. Creating dummy 'winning' column.")
        # **Create Dummy Winning Column for Testing**
        bets_df['winning'] = (bets_df['price'] > 1.5).astype(int)  # Example dummy rule
    
    return bets_df

# Example usage
if __name__ == "__main__":
    load_dotenv()  # Load environment variables from .env file
    API_KEY = os.getenv('ODDS_API_KEY')  # Replace with your actual API key variable name
    
    if not API_KEY:
        print("Error: The Odds API key is not set in the .env file.")
        exit(1)
    
    today_games = pd.read_csv('data/today_games.csv')
    print("Today's games columns:", today_games.columns)  # Debugging line
    
    # Fetch live odds
    live_odds = get_live_odds(API_KEY)
    if live_odds is None:
        print("Failed to fetch live odds.")
        exit(1)
    
    teams_info = get_team_info()
    
    # Prepare bets data
    bets_df = prepare_bets_data(live_odds, teams_info)
    print("Bets data prepared.")
    
    # Add Travel Distance and Winning
    bets_df = add_travel_distance(bets_df, teams_info)
    print("Travel distance and winning added.")
    
    bets_df.to_csv('data/prepared_bets.csv', index=False)
    print("Data preprocessing completed successfully.")