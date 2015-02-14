import os, json, pprint, pandas as pd
from dota2py import api
from pymongo import Connection

pp = pprint.PrettyPrinter(indent = 2)

# API Credentials and Mongo db name and collection name
api_key = os.environ.get('DOTA2_API_KEY')
account_id = os.environ.get('ACCOUNT_ID')
db_name = 'dota2'
collection_name = 'aaron'

def gen_match_ids():
	# Create match_idn list of user-specific matches
	api.set_api_key(api_key)
	start_match_id = None
	match_ids = []
	while True:
		match_ids_hold = []
		matches = api.get_match_history(start_at_match_id = start_match_id,
									account_id = account_id,
								    skill = 3,
								    game_mode = 2,
								    min_players = 10)['result']

		match_ids_hold = [i['match_id'] for i in matches['matches']]
		if not match_ids_hold: break
		print "Adding %s match ids..." %len(match_ids_hold)
		start_match_id = match_ids_hold[len(match_ids_hold)-1]-1
		match_ids += match_ids_hold
	return match_ids

def get_match_details(match_id):
	# Retrieves match details given match_id
	api.set_api_key(api_key)
	return api.get_match_details(match_id = match_id)['result']

def setup(skip=None):
	# MongoDB connection and Dota 2 API Key
	if skip == True: return
	con = Connection()
	db = getattr(con, db_name)
	collection = getattr(db, collection_name)

	match_ids = gen_match_ids()
	for idx, match_id in enumerate(match_ids):
		collection.insert(get_match_details(match_id))
		print "Inserting match details %s/%s into mongoDB..." %(idx, len(match_ids))

def heroes_played():
	# Generate dataframe of heroes played
	con = Connection()
	db = getattr(con, db_name)
	matches = getattr(db, collection_name)
	heroes_raw = matches.find({'players.account_id':75135011}, 
									{'players.account_id','players.hero_id'})
	heroes = [i['players']['account_id' == 75135011]['hero_id'] \
				    for i in heroes_raw]
	heroes_df = pd.DataFrame(heroes)
	heroes_df.columns = ['hero_id']
	return heroes_df

def main():
	
	heroes = heroes_played()
	print heroes
		

	# data = json.loads(aaron_games)

	# pp.pprint(matches.find_one())


if __name__ == "__main__":
	setup(skip=True)
	main()
