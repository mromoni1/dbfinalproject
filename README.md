# dbfinalproject

Web-scraped NCAA DIII women's soccer statistics from the 2025 season to populate a SQL database and perform interesting queries

# Installation
python3 -m pip install -r requirements.txt # make sure requirements are installed 
python ./csv_to_sql.py # populate database with precomputed csv from scraped data 
python src/main/python/frontend/app.py # run app 

# After running app.py, app will be available at:
# http://127.0.0.1:5000

# Web Scraping 
Used public API from henrygd to scrape consumable data from NCAA.com 
https://github.com/henrygd/ncaa-api

# SQL 
SQL schema is defined in D3WomensSoccerSchema.sql.
SQL queries are defined in a Flask dictionary in src/python/frontend/app.py.

# Limitations / Notes 

Games
* Some games were skipped because their data was incomplete (missing team ids, null final score, etc.)
* Implemented a timeout if fetching a games' data took more than 10 seconds. 
* Only read regular season games 

Players
* Total rostered player data was not available. Our player table consists of all players who saw playing time in the 2025 season.
* Player_id was not provided by the data. We generated unique player_ids according to this schema: 
player_id = hash(f"{team_id}:{first}:{last}") % 10**9 
* Player grade was not provided by the data source. 

Universities 
* The API does not contain city or state information for any school. As such, we decided to adapt our schema for this. We may pivot to using external resources to fill in this information.

PlayerSeasonStats
* added new table for aggregate stats across the 2025 season

# Installation 
pip install -r requirements.txt
python3 ./NCAAscrape.py

