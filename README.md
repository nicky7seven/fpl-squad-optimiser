# fpl-squad-optimiser

FPL Squad Optimiser

A Python tool that picks the Fantasy Premier League squad with the highest expected points for the next gameweek, while obeying every FPL rule. It pulls live player and fixture data, scores each player with my own expected points model, and then uses integer linear programming to find the best possible 15-player squad.

It also runs the same optimisation using FPL's official forecast, so the two models can be compared side by side.

Why I built it

Choosing an FPL squad is a constrained allocation problem. You have a fixed budget, strict position and club limits, and you have to judge whether each player's expected return justifies his price. That is structurally similar to building an investment portfolio under capital and concentration limits, which is what got me interested in solving it properly rather than by instinct.

How it works
1. Data

All data comes from FPL's free public API.

bootstrap-static gives every player's price, position, club, recent form, season average and FPL's own forecast
fixtures gives upcoming matches and FPL's difficulty rating for each team (1 is easiest, 5 is hardest)

Players who are injured, suspended or otherwise unavailable are filtered out.

2. My expected points model

Each player's expected points for the next gameweek are estimated in three steps.

Baseline. A blend of recent form (60%) and season points per game (40%). Form reacts quickly to who is playing well now, while the season average is more stable, so blending the two balances momentum against consistency.
Fixture adjustment. The baseline is scaled by the difficulty of the opponent, from ×1.2 for the easiest fixtures down to ×0.8 for the hardest.
Number of games. Players whose team has no match score zero, and players with two matches in the gameweek (a double gameweek) have both added together.

The weights and multipliers are judgement calls, set as constants near the top of the model section so they are easy to change and test.

3. Optimisation

The squad is chosen by integer linear programming using PuLP with the CBC solver. Each player gets a binary decision variable, 1 if picked and 0 if not.

Objective. Maximise the total expected points of the chosen players.

Constraints.

Total cost of at most £100.0m
Exactly 2 goalkeepers, 5 defenders, 5 midfielders and 3 forwards
No more than 3 players from any one club

There are billions of possible squads, so checking each one is not feasible. The solver uses branch and bound to rule out large groups of squads that provably cannot beat the best one found so far, and returns the optimal squad in under a second. Unlike a greedy approach of picking the top scorers until the money runs out, this guarantees the best squad that satisfies every rule at once.

How to run it

Requires Python 3.

python -m pip install -r requirements.txt
python fpl_optimiser.py

The script prints three things.

The best squad using FPL's own forecast
The best squad using my model
The players that differ between the two
Findings

[Add your results here after running it on live data. For example, how many players the two squads share, which types of player your model favours that FPL's forecast doesn't (cheaper in-form defenders, players with easy fixtures), and one or two specific players that explain the difference.]

Limitations and next steps
Expected points ignore risk. Two squads with the same expected total can have very different spreads of outcomes. A next step is penalising players whose scores vary a lot week to week.
One week at a time. The model only looks at the next gameweek. A multi-week version would plan transfers ahead, including FPL's 4-point cost for extra transfers.
Starting eleven and captain. Only 11 players score each week and the captain scores double. Choosing the starters and captain inside the optimisation would make the picks more realistic.
Backtesting. Running the model on past gameweeks would show whether it actually beats FPL's forecast, rather than just disagreeing with it.
