Project Plan: Weekend Football Match Ranker
Step 1: Project setup

Create a new Python project with a virtual environment
Install dependencies: langchain, langchain-anthropic, requests, python-dotenv, pydantic
Create a .env file for FOOTBALL_DATA_API_KEY and ANTHROPIC_API_KEY
I have an API key for football-data.org. Make an empty env file, and I will put it there myself.
Basic folder structure: main.py, tools.py, prompts.py, models.py, .env, requirements.txt

Step 2: Define data models (Pydantic)

Match: home team, away team, kickoff datetime, competition, matchday
TeamStanding: position, team name, points, played, goal difference
RankedMatch: the match plus an excitement_score (1–10), category (title/CL/relegation/rivalry/other), and reasoning string

Step 3: Build the fixture fetcher tool

Function get_weekend_fixtures(league_code: str) -> list[Match]
Hits football-data.org /competitions/{code}/matches endpoint
Filter by date range: upcoming Friday 00:00 UTC through Monday 00:00 UTC
League codes: PL, PD, BL1, SA, FL1
Wrap with @tool decorator
Auth via X-Auth-Token header
Respect the 10 req/min rate limit (add a small sleep between calls)

Step 4: Build the standings fetcher tool

Function get_standings(league_code: str) -> list[TeamStanding]
Hits /competitions/{code}/standings
Return the full table so the LLM can reason about point gaps
Also @tool decorated

Step 5: Aggregate weekend data

Helper that loops through all 5 leagues and assembles {league: {"fixtures": [...], "standings": [...]}}
Skip leagues with no fixtures (international breaks)

Step 6: Write the ranking prompt
Here's a starting version. Put this in prompts.py:
pythonfrom langchain_core.prompts import ChatPromptTemplate

RANKING_SYSTEM_PROMPT = """You are a football analyst who ranks weekend \
fixtures by how consequential they are for the league table. Your job is \
to identify matches with real stakes, NOT matches between famous clubs.

A match is exciting if and only if the RESULT meaningfully affects one of:

1. TITLE RACE: At least one team is in the top 3 AND within 6 points of 1st place.
2. CHAMPIONS LEAGUE RACE: At least one team is in positions 3-7 AND within 5 points
   of the Champions League cutoff for that league:
   - Premier League (PL): top 4 → 5th qualifies for Europa
   - La Liga (PD): top 4
   - Bundesliga (BL1): top 4
   - Serie A (SA): top 4
   - Ligue 1 (FL1): top 3
3. RELEGATION BATTLE: At least one team is in the bottom 6 AND within 5 points of
   the relegation zone (bottom 3 in all these leagues, except Bundesliga where
   it's bottom 2 + a playoff spot).
4. DIRECT SIX-POINTER: Both teams are competing for the same thing (both in title
   race, both fighting relegation, etc.). These are the most exciting of all.

CRITICAL RULES:
- Matchday context matters. Early season (matchday < 10), gaps are less meaningful —
  downweight accordingly. Late season (matchday > 28), gaps are nearly decisive —
  upweight accordingly.
- A match between two famous clubs with nothing to play for is NOT exciting.
  Liverpool vs Chelsea in 8th vs 11th is a 3/10, not a 9/10.
- A match between two unknown clubs fighting relegation on the final matchday IS
  exciting. That's a 9/10.
- Be harsh. Most weekend matches should score 3-5. Reserve 8+ for genuine stakes.

For each fixture provided, return:
- excitement_score: integer 1-10
- category: one of "title", "champions_league", "relegation", "six_pointer", "other"
- reasoning: ONE sentence explaining the specific stakes, citing positions and \
point gaps from the standings

Return ALL fixtures ranked from highest to lowest excitement_score."""

RANKING_USER_PROMPT = """Here is the weekend's data across the top 5 European leagues.

{league_data}

Rank every fixture by excitement score using the criteria above."""

ranking_prompt = ChatPromptTemplate.from_messages([
    ("system", RANKING_SYSTEM_PROMPT),
    ("user", RANKING_USER_PROMPT),
])
You'll need a small formatter that turns the aggregated dict from Step 5 into a readable string for {league_data} — standings as a compact table, then the weekend's fixtures listed below. Don't dump raw JSON; the LLM reasons better on readable text.
Step 7: Build the LCEL pipeline

Chain: fetch_all_leagues_data → format_for_prompt → ranking_prompt → llm.with_structured_output(RankedMatchList) → sort_and_return
Wrap the list in a parent model (RankedMatchList(matches: list[RankedMatch])) — with_structured_output handles single Pydantic models more reliably than bare lists
Use ChatAnthropic(model="claude-sonnet-4-5")

Step 8: Format and display the output

Pretty-print top 5–10 matches to the terminal
Group by day (Saturday / Sunday)
For each: kickoff time, teams, league, category badge, score, one-line reasoning

Step 9: Wire it all together in main.py

Load env vars, fetch data, run pipeline, print results

Step 10: Test and iterate on the prompt

The prompt is a starting point — expect to tune it
Common failure: over-weighting famous clubs. If you see that, add a concrete negative example to the prompt
Another common failure: ignoring matchday context. If it keeps scoring matchday-3 fixtures as title deciders, strengthen that rule

Step 11: Turn it into a weekly webapp
Architecture: since the rankings only change once a week, you do not want to run the LangChain pipeline on every page load. That's slow and burns API credits for no reason. Instead: generate the rankings once a week, cache the result, serve the cache.
Concrete plan:
a. Split the pipeline into a standalone job. Refactor main.py so the pipeline function returns a RankedMatchList object. Add a script generate_weekly.py that runs the pipeline and writes the output to data/weekend_YYYY-MM-DD.json (using the upcoming Friday's date as the key). Keep old files around so you have history.
b. Build a minimal FastAPI backend. One endpoint: GET /api/weekend reads the most recent JSON file from data/ and returns it. That's it — no LLM calls at request time. FastAPI is the right pick here because you're already in Python and it's trivial to set up. Add fastapi and uvicorn to requirements.
c. Frontend. Two reasonable paths depending on your taste: (1) server-rendered with Jinja2 templates — simpler, one repo, no JS build step, fine for a read-only weekly page; (2) a small React or Next.js frontend that fetches from the FastAPI endpoint — more work but nicer if you want to add filters, animations, or expand later. For a v1 I'd go with Jinja2. You can always swap in React when you add the conversational agent.
d. Styling. Tailwind via CDN is the fastest path to something that doesn't look like 2004. Group matches by day, show league badges, color-code the category (red for relegation, gold for title, blue for CL), and make the excitement score visually prominent.
e. Weekly scheduling. You need generate_weekly.py to run every Friday morning. Options, roughly in order of simplicity:

GitHub Actions cron — free, version-controlled, runs generate_weekly.py on a schedule and commits the JSON back to the repo. This is my recommendation. Your webapp just reads from the repo.
A cron job on a small VPS (Railway, Fly.io, a $5 DigitalOcean droplet) if you're hosting the FastAPI app there anyway.
Cloud scheduler (AWS EventBridge, GCP Cloud Scheduler) if you're already in one of those ecosystems — overkill for this.

f. Deployment. Railway or Fly.io will host the FastAPI app for free or near-free. Push the repo, point it at main.py, done. If you go the GitHub Actions route for generation, the flow is: Action runs Friday → commits new JSON → deployment auto-redeploys (or just reads the new file on next request if you mount the data dir).
g. Nice-to-haves for later. An RSS feed, email digest on Friday afternoon, a "last week's predictions vs what actually happened" section, and eventually the conversational agent as a chat widget on the same page — which is where your earlier investment in clean @tool functions pays off.

One flag on Step 11: if you go the GitHub Actions route, you'll need to store FOOTBALL_DATA_API_KEY and ANTHROPIC_API_KEY as repo secrets and reference them in the workflow file. Straightforward but easy to forget.
This should be enough to hand to Claude Code step by step. Want me to also draft the generate_weekly.py + GitHub Actions workflow skeleton now, or leave that for when you get to Step 11?
