# utils.py

import pandas as pd
from geopy.distance import geodesic
import requests
import os
from dotenv import load_dotenv

def get_team_info():
    from nba_api.stats.static import teams
    nba_teams = teams.get_teams()
    teams_df = pd.DataFrame(nba_teams)
    # Ensure the columns are correctly named
    teams_df.rename(columns={'id': 'id', 'full_name': 'full_name', 'abbreviation': 'abbreviation'}, inplace=True)
    return teams_df

def calculate_travel_distance(team1, team2, teams_info):
    team_locations = {
        'Atlanta Hawks': (33.748995, -84.387982),
        'Boston Celtics': (42.366212, -71.062193),
        'Brooklyn Nets': (40.678178, -73.944158),
        'Charlotte Hornets': (35.227085, -80.843124),
        'Chicago Bulls': (41.881832, -87.623177),
        'Cleveland Cavaliers': (41.4957, -81.6903),
        'Dallas Mavericks': (32.776665, -96.796989),
        'Denver Nuggets': (39.739236, -104.990251),
        'Detroit Pistons': (42.331429, -83.045753),
        'Golden State Warriors': (37.774929, -122.419416),
        'Houston Rockets': (29.760427, -95.369803),
        'Indiana Pacers': (39.768403, -86.158068),
        'Los Angeles Clippers': (34.0430, -118.2673),
        'Los Angeles Lakers': (34.0430, -118.2673),
        'Memphis Grizzlies': (35.1382, -90.0505),
        'Miami Heat': (25.7814, -80.1870),
        'Milwaukee Bucks': (43.0436, -87.9172),
        'Minnesota Timberwolves': (44.9795, -93.2762),
        'New Orleans Pelicans': (29.9511, -90.0821),
        'New York Knicks': (40.7505, -73.9934),
        'Oklahoma City Thunder': (35.4634, -97.5151),
        'Orlando Magic': (28.5392, -81.3839),
        'Philadelphia 76ers': (39.9012, -75.1720),
        'Phoenix Suns': (33.4457, -112.0712),
        'Portland Trail Blazers': (45.5316, -122.6668),
        'Sacramento Kings': (38.5802, -121.4997),
        'San Antonio Spurs': (29.4271, -98.4375),
        'Toronto Raptors': (43.6435, -79.3791),
        'Utah Jazz': (40.7683, -111.9011),
        'Washington Wizards': (38.9072, -77.0369)
    }
    loc1 = team_locations.get(team1)
    loc2 = team_locations.get(team2)
    
    if loc1 and loc2:
        return geodesic(loc1, loc2).miles
    else:
        return 0

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
        print(f"Error fetching odds: {response.status_code}")
        return None