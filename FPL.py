import requests
import pulp

# ---------------------------------------------------------------
# Step 1: download the data
# ---------------------------------------------------------------
data = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/").json()
fixtures = requests.get("https://fantasy.premierleague.com/api/fixtures/?future=1").json()

players = data["elements"]
print(f"Total players: {len(players)}")

# ---------------------------------------------------------------
# Step 2: keep only what we need, for available players
# ---------------------------------------------------------------
clean = []
for p in players:
    if p["status"] != "a":                 # skip injured or suspended players
        continue
    clean.append({
        "name": p["web_name"],
        "team": p["team"],                 # club number 1-20
        "position": p["element_type"],     # 1 GK, 2 DEF, 3 MID, 4 FWD
        "cost": p["now_cost"] / 10,        # 55 -> £5.5m
        "exp_points": float(p["ep_next"] or 0),
        "form": float(p["form"] or 0),
        "ppg": float(p["points_per_game"] or 0),
    })

print(f"Available players: {len(clean)}")

# ---------------------------------------------------------------
# Step 3: my own expected points model
# ---------------------------------------------------------------
next_gw = next(e["id"] for e in data["events"] if e["is_next"])

# Each team's fixture difficulty next gameweek (a list, to handle 0 or 2 games)
team_games = {}
for f in fixtures:
    if f["event"] == next_gw:
        team_games.setdefault(f["team_h"], []).append(f["team_h_difficulty"])
        team_games.setdefault(f["team_a"], []).append(f["team_a_difficulty"])

# My judgement calls: blend weights and fixture multipliers
FORM_WEIGHT = 0.6
PPG_WEIGHT = 0.4
multiplier = {1: 1.2, 2: 1.1, 3: 1.0, 4: 0.9, 5: 0.8}

for p in clean:
    baseline = FORM_WEIGHT * p["form"] + PPG_WEIGHT * p["ppg"]
    games = team_games.get(p["team"], [])        # [] means no game this week
    p["my_points"] = sum(baseline * multiplier[d] for d in games)

# ---------------------------------------------------------------
# Step 4: pick the best squad with integer linear programming
# ---------------------------------------------------------------
def pick_squad(players, key, budget=100):
    prob = pulp.LpProblem("FPL_Squad", pulp.LpMaximize)

    # One yes/no variable per player: 1 = picked, 0 = not picked
    x = {i: pulp.LpVariable(f"pick_{i}", cat="Binary") for i in range(len(players))}

    # Objective: maximise total expected points
    prob += pulp.lpSum(players[i][key] * x[i] for i in x)

    # Constraint 1: budget
    prob += pulp.lpSum(players[i]["cost"] * x[i] for i in x) <= budget

    # Constraint 2: positions (2 GK, 5 DEF, 5 MID, 3 FWD)
    for pos, count in {1: 2, 2: 5, 3: 5, 4: 3}.items():
        prob += pulp.lpSum(x[i] for i in x if players[i]["position"] == pos) == count

    # Constraint 3: max 3 players per club
    for team in set(p["team"] for p in players):
        prob += pulp.lpSum(x[i] for i in x if players[i]["team"] == team) <= 3

    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    return [players[i] for i in x if x[i].value() == 1]

# ---------------------------------------------------------------
# Step 5: run both models and compare
# ---------------------------------------------------------------
NAMES = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}

def show(title, squad, key):
    print(f"\n=== {title} ===")
    for p in sorted(squad, key=lambda p: (p["position"], -p[key])):
        print(f'{NAMES[p["position"]]:4} {p["name"]:18} £{p["cost"]:.1f}m  {p[key]:.1f} pts')
    print(f'Total cost £{sum(p["cost"] for p in squad):.1f}m')
    print(f'Expected points {sum(p[key] for p in squad):.1f}')

fpl_squad = pick_squad(clean, "exp_points")
my_squad = pick_squad(clean, "my_points")

show("Squad using FPL's forecast", fpl_squad, "exp_points")
show("Squad using my model", my_squad, "my_points")

fpl_names = {p["name"] for p in fpl_squad}
my_names = {p["name"] for p in my_squad}
print("\n=== Differences ===")
print("Only in my squad:  ", ", ".join(sorted(my_names - fpl_names)) or "none")
print("Only in FPL squad: ", ", ".join(sorted(fpl_names - my_names)) or "none")
print(f"Players in common: {len(my_names & fpl_names)} of 15")