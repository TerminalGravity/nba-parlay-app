from nba_api.stats.endpoints import scoreboardv2, leaguegamefinder
from nba_api.stats.static import teams
import pandas as pd
from datetime import datetime, timedelta
import schedule
import time
import os

def get_today_games():
    today = datetime.today().strftime('%Y-%m-%d')
    scoreboard = scoreboardv2.ScoreboardV2(game_date=today, league_id='00')
    games = scoreboard.get_data_frames()[0]
    return games

def get_team_info():
    nba_teams = teams.get_teams()
    return pd.DataFrame(nba_teams)

def get_historical_games(days=30):
    # Get games from last X days for model training
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days)
    gamefinder = leaguegamefinder.LeagueGameFinder(
        date_from_nullable=start_date.strftime('%m/%d/%Y'),
        date_to_nullable=end_date.strftime('%m/%d/%Y')
    )
    historical_games = gamefinder.get_data_frames()[0]
    historical_games.to_csv('data/historical_games.csv', index=False)
    return historical_games

def ensure_data_dir():
    if not os.path.exists('data'):
        os.makedirs('data')

def fetch_and_save_data():
    ensure_data_dir()
    
    # Fetch current data
    today_games = get_today_games()
    teams_info = get_team_info()
    historical_games = get_historical_games()
    
    # Save to CSV files
    today_games.to_csv('data/today_games.csv', index=False)
    teams_info.to_csv('data/teams_info.csv', index=False)
    historical_games.to_csv('data/historical_games.csv', index=False)
    
    print(f"Data fetched and saved at {datetime.now()}")
    print(f"Today's games: {len(today_games)} games")
    print(f"Historical games: {len(historical_games)} games")

# Schedule data fetching
schedule.every().day.at("00:01").do(fetch_and_save_data)  # Run after midnight
schedule.every().day.at("10:00").do(fetch_and_save_data)  # Mid-morning update
schedule.every().day.at("16:00").do(fetch_and_save_data)  # Pre-game update

if __name__ == "__main__":
    fetch_and_save_data()  # Initial run
    
    # Start the scheduling loop to run pending tasks
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except Exception as e:
            print(f"Error occurred: {e}")
            time.sleep(300)  # Wait 5 minutes on error before retrying