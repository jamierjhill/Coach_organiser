# utils.py
import requests, os, random
from collections import defaultdict
from datetime import datetime, timedelta

# Modified organize_matches function for utils.py with prioritization for limited-round players
def organize_matches(players, courts, match_type, num_matches):
    matchups = [[] for _ in range(courts)]
    match_counts = {p['name']: 0 for p in players}
    played_matches = {p['name']: set() for p in players}
    opponent_grades = {p['name']: [] for p in players}
    seen_doubles_matchups = set()
    previous_partners = {p['name']: set() for p in players}
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

                        if match_key in seen_matchups:
                            continue

                        if any(full_group == last_court_groups.get(p['name'], frozenset()) for p in group):
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
        # Filter players based on their max_rounds constraint
        # Only include players who haven't reached their match limit
        # AND whose max_rounds is >= the current round number
        available_players = [
            p for p in players 
            if match_counts[p['name']] < p.get('max_rounds', num_matches) and
               round_num <= p.get('max_rounds', num_matches)
        ]
        
        # Sort available players by:
        # 1. Limited players first (players with max_rounds < num_matches)
        # 2. Players with fewer remaining rounds
        # 3. Players who have played fewer matches so far
        available_players.sort(key=lambda p: (
            # Primary: Unlimited players last (False sorts before True)
            p.get('max_rounds', num_matches) >= num_matches,
            # Secondary: Sort by remaining rounds (fewer remaining rounds first)
            p.get('max_rounds', num_matches) - round_num + 1,
            # Tertiary: Sort by matches played so far (fewer played first)
            match_counts[p['name']]
        ))
        
        # Add some randomness within each priority group
        # We'll identify groups with the same priority and shuffle within each group
        priority_groups = {}
        for player in available_players:
            # Create a priority key based on our sorting criteria
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
            import random
            random.shuffle(group)
        
        # Reconstruct the available_players list maintaining the priority order
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

                previous_partners[group[0]['name']].add(group[1]['name'])
                previous_partners[group[1]['name']].add(group[0]['name'])
                previous_partners[group[2]['name']].add(group[3]['name'])
                previous_partners[group[3]['name']].add(group[2]['name'])

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

            for p in pair:
                match_counts[p['name']] += 1
                for opp in pair:
                    if opp['name'] != p['name']:
                        played_matches[p['name']].add(opp['name'])
                        opponent_grades[p['name']].append(opp['grade'])

            matchups[court_index].append((pair, round_num))

    opponent_averages = {
        name: round(sum(grades) / len(grades), 2) if grades else 0
        for name, grades in opponent_grades.items()
    }

    opponent_diff = {
        name: round(abs(opponent_averages[name] - next(p['grade'] for p in players if p['name'] == name)), 2)
        for name in opponent_averages
    }

    return matchups, match_counts, opponent_averages, opponent_diff

import os
import json
import time
from datetime import datetime, timedelta
import requests

# Define a cache directory
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def get_weather(location_input):
    API_KEY = os.getenv("OPENWEATHER_API_KEY")
    if not API_KEY:
        return {"error": "Missing API key"}
    
    # Create a cache key based on the location
    # Normalize the location to avoid case sensitivity
    cache_key = location_input.strip().lower().replace(" ", "_")
    cache_file = os.path.join(CACHE_DIR, f"weather_{cache_key}.json")
    
    # Check if we have a valid cache
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                cached_data = json.load(f)
            
            # Check if the cache is still valid (less than 1 hour old)
            cache_time = cached_data.get("cache_timestamp", 0)
            if time.time() - cache_time < 3600:  # 1 hour in seconds
                print(f"✅ Using cached weather data for {location_input}")
                return cached_data
        except Exception as e:
            print(f"❌ Cache read error for {location_input}: {e}")
    
    # Cache miss or invalid - fetch new data
    print(f"🔄 Fetching fresh weather data for {location_input}")
    
    # Help the API resolve vague UK location inputs
    if len(location_input.strip()) <= 5:  # e.g. "SW6", "W4"
        query = f"{location_input}, London, UK"
    else:
        query = location_input

    try:
        geo = requests.get("http://api.openweathermap.org/geo/1.0/direct", params={
            "q": query,
            "limit": 1,
            "appid": API_KEY
        }).json()

        if not geo:
            return {"error": "Location not found"}

        lat, lon = geo[0]["lat"], geo[0]["lon"]
        location = f"{geo[0]['name']}, {geo[0]['country']}"

        res = requests.get("https://api.openweathermap.org/data/2.5/forecast", params={
            "lat": lat,
            "lon": lon,
            "units": "metric",
            "appid": API_KEY
        })
        data = res.json()

        if "list" not in data:
            return {"error": "No forecast data"}

        # Process the weather data as before
        # [Your existing code for processing weather data]
        day_blocks = defaultdict(list)

        for entry in data["list"]:
            dt = datetime.fromtimestamp(entry["dt"])
            day = dt.strftime("%A")
            block = {
                "time": dt.strftime("%H:%M"),
                "temp": entry["main"]["temp"],
                "desc": entry["weather"][0]["description"].title(),
                "icon": entry["weather"][0]["icon"],
                "wind": entry["wind"]["speed"],
                "clouds": entry["clouds"]["all"],
                "rain": entry.get("rain", {}).get("3h", 0)
            }
            day_blocks[day].append(block)

        forecast = []
        for day, hourly_list in day_blocks.items():
            score = sum([b["clouds"] + b["rain"]*20 + b["wind"]*2 for b in hourly_list])
            avg_score = score / max(len(hourly_list), 1)
            good_for_tennis = avg_score < 100
            forecast.append({
                "day": day,
                "hourly": hourly_list,
                "good_for_tennis": good_for_tennis
            })

        # Prepare the response with cache timestamp
        response = {
            "location": location,
            "forecast": forecast[:5],
            "cache_timestamp": time.time()
        }
        
        # Save to cache
        try:
            with open(cache_file, "w") as f:
                json.dump(response, f)
        except Exception as e:
            print(f"❌ Cache write error for {location_input}: {e}")
        
        return response
        
    except Exception as e:
        print(f"❌ Weather API error for {location_input}: {e}")
        return {"error": f"API error: {str(e)}"}