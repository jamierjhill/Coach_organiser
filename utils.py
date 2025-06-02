# utils.py - Tennis Match Organization Algorithm
import random
from collections import defaultdict

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
        # Filter available players based on constraints
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