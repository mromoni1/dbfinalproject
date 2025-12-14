# dbfinalproject

Web-scraped NCAA DIII women's soccer statistics from the 2025 season to populate a SQL database and perform interesting queries

# Installation

pip install -r requirements.txt
python3 ./NCAAscrape.py

# Limitations

The API does not contain city or state information for any school. As such, we decided to adapt our schema for this. We may pivot to using external resources to fill in this information.
