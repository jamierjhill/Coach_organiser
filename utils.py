# utils.py
import os
import json
import time
import random
import requests
from collections import defaultdict
from datetime import datetime

# Cache directory for weather data
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def organize_matches(players, courts, match_type, num_matches):
    """
    Organize tennis matches based on player grades with support for limited-round players.
    
    Args:
        players: List of player dictionaries with 'name' and 'grade' keys
        courts: Number of available courts
        match_type: "singles" or "doubles"
        num_matches: Number of matches each player should play
        
    Returns:
        tuple: (matchups, match_counts, opponent_averages, opponent_diff)
    """
    matchups = [[] for _ in range(courts)]
    match_counts = {p['name']: 0 for p in players}
    played_matches = {p['name']: set() for p in players}
    opponent_grades = {p['name']: [] for p in players}
    seen_doubles_matchups = set()
    last_court_groups = {}

    def grade_distance(g1, g2):
        return abs(g1 - g2)

    def find_best_partner(player, candidates, round_num):
        grade_targets = opponent_grades[player['name']] or [player['grade']]
        sorted_candidates = sorted(
            candidates,
            key=lambda p: min(grade_distance(p['grade'], gt) for gt in grade_targets)
        )
        for candidate in sorted_candidates:
            if candidate['name'] != player['name'] and candidate['name'] not in played_matches[player['name']]:
                if candidate['name'] not in last_court_groups.get(player['name'], set()):
                    return candidate
        for candidate in sorted_candidates:
            if candidate['name'] != player['name']:
                return candidate
        return None

    def find_best_doubles_group(available, seen_matchups, last_court_groups):
        best_group = None
        best_diff = float('inf')
        best_match_key = None

        for i in range(len(available)):
            for j in range(i+1, len(available)):
                for k in range(len(available)):
                    for l in range(k+1, len(available)):
                        group = [available[i], available[j], available[k], available[l]]
                        names = [p['name'] for p in group]
                        if len(set(names)) < 4:
                            continue

                        team1 = [group[0], group[1]]
                        team2 = [group[2], group[3]]
                        team1_names = frozenset(p['name'] for p in team1)
                        team2_names = frozenset(p['name'] for p in team2)
                        match_key = frozenset([team1_names, team2_names])
                        full_group = frozenset(names)

                        if match_key in seen_matchups or any(full_group == last_court_groups.get(p['name'], frozenset()) for p in group):
                            continue

                        team1_avg = sum(p['grade'] for p in team1) / 2
                        team2_avg = sum(p['grade'] for p in team2) / 2
                        diff = abs(team1_avg - team2_avg)

                        if diff < best_diff:
                            best_diff = diff
                            best_group = team1 + team2
                            best_match_key = match_key

        return (best_group, best_match_key) if best_group else (None, None)

    # Process rounds in order (1 to num_matches)
    for round_num in range(1, num_matches + 1):
        # Filter and sort available players based on constraints
        available_players = [
            p for p in players 
            if match_counts[p['name']] < p.get('max_rounds', num_matches) and
               round_num <= p.get('max_rounds', num_matches)
        ]
        
        # Sort by priority criteria
        available_players.sort(key=lambda p: (
            p.get('max_rounds', num_matches) >= num_matches,
            p.get('max_rounds', num_matches) - round_num + 1,
            match_counts[p['name']]
        ))
        
        # Create priority groups and shuffle within each group
        priority_groups = {}
        for player in available_players:
            priority_key = (
                player.get('max_rounds', num_matches) >= num_matches,
                player.get('max_rounds', num_matches) - round_num + 1,
                match_counts[player['name']]
            )
            if priority_key not in priority_groups:
                priority_groups[priority_key] = []
            priority_groups[priority_key].append(player)
        
        # Shuffle each priority group
        for group in priority_groups.values():
            random.shuffle(group)
        
        # Reconstruct the player list maintaining priority order
        available_players = []
        for key in sorted(priority_groups.keys()):
            available_players.extend(priority_groups[key])
        
        used_names = set()
        new_round_groups = {p['name']: set() for p in players}

        for court_index in range(courts):
            needed_players = 4 if match_type == "doubles" else 2
            if len(available_players) - len(used_names) < needed_players:
                continue

            candidates = [p for p in available_players if p['name'] not in used_names]

            if match_type == "doubles":
                group, match_key = find_best_doubles_group(
                    candidates, seen_doubles_matchups, last_court_groups
                )
                if not group:
                    continue

                seen_doubles_matchups.add(match_key)
                used_names.update(p['name'] for p in group)
                group_set = frozenset(p['name'] for p in group)

                for p in group:
                    last_court_groups[p['name']] = group_set
                    new_round_groups[p['name']].update(mate['name'] for mate in group if mate['name'] != p['name'])

                # Track partner pairings
                previous_partners = {p['name']: set() for p in players}
                for i in range(0, len(group), 2):
                    if i+1 < len(group):
                        previous_partners[group[i]['name']].add(group[i+1]['name'])
                        previous_partners[group[i+1]['name']].add(group[i]['name'])

                pair = group
            else:
                p1 = candidates.pop(0)
                p2 = find_best_partner(p1, candidates, round_num)
                if not p2:
                    continue
                used_names.update({p1['name'], p2['name']})
                pair = [p1, p2]
                new_round_groups[p1['name']].add(p2['name'])
                new_round_groups[p2['name']].add(p1['name'])

            # Update match counts and opponent history
            for p in pair:
                match_counts[p['name']] += 1
                for opp in pair:
                    if opp['name'] != p['name']:
                        played_matches[p['name']].add(opp['name'])
                        opponent_grades[p['name']].append(opp['grade'])

            matchups[court_index].append((pair, round_num))

    # Calculate opponent statistics
    opponent_averages = {
        name: round(sum(grades) / len(grades), 2) if grades else 0
        for name, grades in opponent_grades.items()
    }

    opponent_diff = {
        name: round(abs(opponent_averages[name] - next(p['grade'] for p in players if p['name'] == name)), 2)
        for name in opponent_averages
    }

    return matchups, match_counts, opponent_averages, opponent_diff

def make_api_request(url, params=None, timeout=5, max_retries=2):
    """
    Make an API request with retry logic.
    
    Args:
        url: API endpoint URL
        params: Dictionary of query parameters
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        
    Returns:
        dict: JSON response or error information
    """
    retry_count = 0
    while retry_count <= max_retries:
        try:
            response = requests.get(url, params=params, timeout=timeout)
            
            if response.status_code == 200:
                return response.json()
            
            if retry_count < max_retries:
                retry_count += 1
                time.sleep(1)  # Wait before retry
                continue
            
            return {"error": f"API error: {response.status_code}"}
            
        except requests.exceptions.Timeout:
            if retry_count < max_retries:
                retry_count += 1
                time.sleep(1)
                continue
            return {"error": "Request timed out"}
            
        except requests.exceptions.ConnectionError:
            if retry_count < max_retries:
                retry_count += 1
                time.sleep(1)
                continue
            return {"error": "Connection error"}
            
        except Exception as e:
            return {"error": f"Request error: {str(e)}"}

def get_weather(location_input):
    """
    Get weather data from OpenWeatherMap API with caching.
    
    Args:
        location_input: Location string (postcode, city name, etc.)
        
    Returns:
        dict: Weather data or error information
    """
    API_KEY = os.getenv("OPENWEATHER_API_KEY")
    if not API_KEY:
        return {"error": "Missing API key", "location": location_input}
    
    # Handle empty input
    if not location_input.strip():
        return {"error": "No location provided", "location": "Unknown"}
    
    # Create a cache key based on the location
    cache_key = location_input.strip().lower().replace(" ", "_")
    cache_file = os.path.join(CACHE_DIR, f"weather_{cache_key}.json")
    
    # Check for valid cache
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                cached_data = json.load(f)
            
            # Check if cache is still valid (less than 1 hour old)
            cache_time = cached_data.get("cache_timestamp", 0)
            if time.time() - cache_time < 3600:  # 1 hour in seconds
                return cached_data
        except Exception:
            # Cache error - continue to fetch fresh data
            pass
    
    # Format location query for UK postcodes
    query = location_input
    if len(location_input.strip()) <= 5:  # e.g. "SW6", "W4"
        query = f"{location_input}, London, UK"

    # Get coordinates first
    geo_data = make_api_request(
        "http://api.openweathermap.org/geo/1.0/direct",
        params={"q": query, "limit": 1, "appid": API_KEY}
    )
    
    if "error" in geo_data or not geo_data:
        # Try a more generic search if specific search fails
        if "," in query:
            parts = query.split(",")
            return get_weather(parts[0].strip())  # Recursive call with simpler query
        return {"error": "Location not found", "location": location_input}

    # Get weather data using coordinates
    lat, lon = geo_data[0]["lat"], geo_data[0]["lon"]
    location = f"{geo_data[0].get('name', '')}, {geo_data[0].get('country', '')}"
    
    weather_data = make_api_request(
        "https://api.openweathermap.org/data/2.5/forecast",
        params={"lat": lat, "lon": lon, "units": "metric", "appid": API_KEY}
    )
    
    if "error" in weather_data or "list" not in weather_data:
        return {"error": weather_data.get("error", "No forecast data"), "location": location}

    # Process weather data
    day_blocks = defaultdict(list)
    for entry in weather_data["list"]:
        dt = datetime.fromtimestamp(entry["dt"])
        day = dt.strftime("%A")
        
        # Extract weather data with safe defaults
        block = {
            "time": dt.strftime("%H:%M"),
            "temp": entry.get("main", {}).get("temp", 0),
            "desc": entry.get("weather", [{}])[0].get("description", "Unknown").title(),
            "icon": entry.get("weather", [{}])[0].get("icon", "01d"),
            "wind": entry.get("wind", {}).get("speed", 0),
            "clouds": entry.get("clouds", {}).get("all", 0),
            "rain": entry.get("rain", {}).get("3h", 0)
        }
        day_blocks[day].append(block)

    # Generate forecast data
    forecast = []
    for day, hourly_list in day_blocks.items():
        # Calculate tennis playability score
        score = sum([b["clouds"] + b["rain"]*20 + b["wind"]*2 for b in hourly_list])
        avg_score = score / max(len(hourly_list), 1)
        good_for_tennis = avg_score < 100
        
        # Find forecast entry closest to noon
        noon_forecast = find_noon_forecast(hourly_list)
        
        forecast.append({
            "day": day,
            "hourly": hourly_list,
            "noon": noon_forecast,  # Add noon forecast
            "good_for_tennis": good_for_tennis
        })

    # Prepare response
    response = {
        "location": location,
        "forecast": forecast[:5],
        "cache_timestamp": time.time()
    }
    
    # Save to cache
    try:
        with open(cache_file, "w") as f:
            json.dump(response, f)
    except Exception:
        # Cache write error - continue without caching
        pass
    
    return response


def find_noon_forecast(hourly_list):
    """Find the forecast entry closest to 12:00 (noon)."""
    target_time = "11:00"
    noon_entry = None
    min_time_diff = float('inf')
    
    for entry in hourly_list:
        time_str = entry["time"]
        # Convert time string to minutes for comparison
        h, m = map(int, time_str.split(':'))
        entry_minutes = h * 60 + m
        
        # Convert target time to minutes
        target_h, target_m = map(int, target_time.split(':'))
        target_minutes = target_h * 60 + target_m
        
        # Calculate time difference
        time_diff = abs(entry_minutes - target_minutes)
        
        if time_diff < min_time_diff:
            min_time_diff = time_diff
            noon_entry = entry
    
    return noon_entry if noon_entry else hourly_list[0]  # Fallback to first entry