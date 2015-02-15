import os, json, pprint, pandas as pd, matplotlib.pyplot as plt, seaborn
from dota2py import api
from pymongo import Connection

pp = pprint.PrettyPrinter(indent = 2)
pd.set_option('display.width', 1000)

# API Credentials and Mongo db name and collection name
api_key = os.environ.get('DOTA2_API_KEY')
account_id = int(os.environ.get('DOTA2_ACCOUNT_ID'))
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

def heroes_win():
	# Generate dataframe of heroes played
	con = Connection()
	db = getattr(con, db_name)
	matches = getattr(db, collection_name)
	heroes_raw = matches.find({'players.account_id':account_id}, 
							  {'players.account_id',
							   'players.hero_id',
							   'players.player_slot',
							   'radiant_win'})

	games = []
	for game in heroes_raw:
		add_dict = {}
		add_dict['radiant_win'] = game['radiant_win']
		for player in game['players']:
			if player['account_id'] == account_id:
				add_dict['hero_id'] = player['hero_id']
				add_dict['player_slot'] = player['player_slot']
		games.append(add_dict)

	heroes_df = pd.DataFrame(games)
	return heroes_df

def create_hero_dictionary():
	# Creates a simple dictioanry of idns and hero names
	hero_dict = {}
	hero_name_and_id = api.get_heroes()['result']['heroes']
	for hero in hero_name_and_id:
		hero_dict[hero['id']] = hero['localized_name']
	return hero_dict

def create_hero_attribute_df():
	# Reads the tab-delimited .txt file for hero attributes
	return pd.DataFrame.from_csv("hero-attributes.txt", sep="\t")

def add_attributes_df(heroes, hero_attributes):
	primary_attribute_detail = [hero_attributes.ix[i]['primary_attribute'] \
								for i in heroes['hero_id']]
	name = [hero_attributes.ix[i]['hero'] \
								for i in heroes['hero_id']]
	win = [True if (
					(i['player_slot'] > 100 and i['radiant_win'] == False) or \
		            (i['player_slot'] < 100 and i['radiant_win'] == True) \
		           ) else False for k,i in heroes.iterrows()] 

	heroes.loc[:,'primary_attribute'] = primary_attribute_detail
	heroes.loc[:,'name'] = name
	heroes.loc[:,'win'] = win
	return

def calc_primary_attribute_stats():
	heroes = heroes_win()
	hero_attributes = create_hero_attribute_df()
	add_attributes_df(heroes, hero_attributes)
	
	heroes_primary = heroes.loc[:,('primary_attribute','win')].groupby('primary_attribute').sum()
	heroes_primary_count = heroes.loc[:,('primary_attribute','win')].groupby('primary_attribute').count()
	results_primary = heroes_primary/heroes_primary_count
	results_primary.ix['Average'] = heroes_primary.sum()/heroes_primary_count.sum()
	results_primary['wins'] = heroes_primary
	results_primary.loc['Average','wins'] = heroes_primary.sum()['win']
	results_primary['total'] = heroes_primary_count
	results_primary.loc['Average','total'] = heroes_primary_count.sum()['win']
	columns_rename = results_primary.columns.values
	columns_rename[0] = 'win %'
	results_primary.columns = columns_rename

	return results_primary

def plot_primary_attribute(results_primary):
	results_primary['win %'].plot(kind='barh')
	# plt.subplots_adjust(bottom=0.2)
	plt.show()
	

def main():
	results_primary = calc_primary_attribute_stats()
	plot_primary_attribute(results_primary)
	print results_primary


if __name__ == "__main__":
	setup(skip=True)
	main()
