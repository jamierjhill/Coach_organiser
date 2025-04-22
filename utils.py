# utils.py
import requests, os, random
from collections import defaultdict
from datetime import datetime, timedelta

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

    for round_num in range(num_matches):
        available_players = sorted(players, key=lambda p: match_counts[p['name']])
        random.shuffle(available_players)
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

            matchups[court_index].append((pair, round_num + 1))

    opponent_averages = {
        name: round(sum(grades) / len(grades), 2) if grades else 0
        for name, grades in opponent_grades.items()
    }

    opponent_diff = {
        name: round(abs(opponent_averages[name] - next(p['grade'] for p in players if p['name'] == name)), 2)
        for name in opponent_averages
    }

    return matchups, match_counts, opponent_averages, opponent_diff



from collections import defaultdict
from datetime import datetime
import os
import requests

def get_weather(location_input):
    API_KEY = os.getenv("OPENWEATHER_API_KEY")
    if not API_KEY:
        return {"error": "Missing API key"}

    # Help the API resolve vague UK location inputs
    if len(location_input.strip()) <= 5:  # e.g. "SW6", "W4"
        query = f"{location_input}, London, UK"
    else:
        query = location_input

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

    return {
        "location": location,
        "forecast": forecast[:5]
    }
