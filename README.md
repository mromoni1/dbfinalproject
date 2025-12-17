# dbfinalproject

Web-scraped NCAA DIII women's soccer statistics from the 2025 season to populate a SQL database and perform interesting queries

# Installation

# Web Scraping 
Used public API from henrygd to scrape consumable data from NCAA.com 
https://github.com/henrygd/ncaa-api

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

# Installation 
pip install -r requirements.txt
python3 ./NCAAscrape.py

# Limitations

The API does not contain city or state information for any school. As such, we decided to adapt our schema for this. We may pivot to using external resources to fill in this information.
