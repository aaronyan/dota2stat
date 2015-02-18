import os, json, pprint, pandas as pd, matplotlib.pyplot as plt, seaborn
import numpy as np
from dota2py import api
from pymongo import Connection

pp = pprint.PrettyPrinter(indent = 2)
pd.set_option('display.width', 1000)

class Credentials(object):
	def __init__ (self, api_key = None, account_id = None, \
				  db_name = None, collection_name = None):
		self.api_key = api_key
		self.account_id = account_id
		self.db_name = db_name
		self.collection_name = collection_name

"""
Setup Functions / Pull Data from API
"""

def gen_match_ids(cred):
	# Create match_idn list of user-specific matches
	api_key = cred.api_key
	account_id = cred.account_id
	db_name = cred.db_name
	collection_name = cred.collection_name

	api.set_api_key(api_key)
	start_match_id = None
	match_ids = []

	while True:
		match_ids_hold = []
		matches = api.get_match_history(start_at_match_id = start_match_id,
										account_id = account_id,
								    	skill = 3,
								    	game_mode = 1,
								    	min_players = 10)['result']

		match_ids_hold = [i['match_id'] for i in matches['matches']]
		if not match_ids_hold: break
		print "Adding %s match ids..." %len(match_ids_hold)
		start_match_id = match_ids_hold[len(match_ids_hold)-1]-1
		match_ids += match_ids_hold
	return match_ids

def get_match_details(cred, match_id):
	# Retrieves match details given match_id
	api_key = cred.api_key
	db_name = cred.db_name
	collection_name = cred.collection_name
	api.set_api_key(api_key)
	return api.get_match_details(match_id = match_id)['result']

def setup(cred, skip = None):
	# MongoDB connection and Dota 2 API Key
	db_name = cred.db_name
	collection_name = cred.collection_name
	if skip == True: return
	con = Connection()
	db = getattr(con, db_name)
	collection = getattr(db, collection_name)

	match_ids = gen_match_ids()
	for idx, match_id in enumerate(match_ids):
		collection.insert(get_match_details(cred, match_id))
		print "Inserting match details %s/%s into mongoDB..." %(idx, len(match_ids))

"""
Single Attribute Analysis - Personal
"""

def heroes_win(cred):
	# Generate dataframe of heroes played
	account_id = cred.account_id
	db_name = cred.db_name
	collection_name = cred.collection_name

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

def create_hero_attribute_df():
	# Reads the tab-delimited .txt file for hero attributes
	dirname = os.path.dirname(os.path.dirname(__file__))
	path = os.path.join(dirname, 'data\hero-attributes.txt')
	return pd.DataFrame.from_csv(path, sep="\t")

def add_attributes_df(heroes, hero_attributes):
	# Adds detailed information (hero name, win)
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

def calc_primary_attribute_stats(cred):
	# Summarizes attributes df
	heroes = heroes_win(cred)
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
	# Plots the primary attribute summary dataframe
	results_primary['win %'].plot(kind='barh')
	plt.show()
	
"""
Team Attribute Analysis - Personal
"""

def hereos_composition(cred):
	db_name = cred.db_name
	collection_name = cred.collection_name
	con = Connection()
	db = getattr(con, db_name)
	matches = getattr(db, collection_name)

	heroes_raw = matches.find({'game_mode':1}, 
						  {'players.hero_id',
						   'players.player_slot',
						   'radiant_win'})

	games = []
	match = {}
	for game in heroes_raw:
		match = {}
		match['radiant_win'] = game['radiant_win']
		for i in range(len(game['players'])):
			addme = {}
			addme[game['players'][i]['player_slot']] = game['players'][i]['hero_id']
			match = dict(match.items() +  addme.items())
		games.append(match)

	return games

def calc_primary_attribute_composition(cred):

	api_key = cred.api_key
	account_id = cred.account_id
	db_name = cred.db_name
	collection_name = cred.collection_name

	heroes = hereos_composition(cred)
	
	df = pd.DataFrame.from_dict(heroes)
	df_attribute_cols = df.columns.values[:len(df.columns.values)-1]
	df_attribute_cols = ['attr_'+ str(x) for x in df_attribute_cols]
	
	print df_attribute_cols

if __name__ == "__main__":
	# API Credentials and Mongo db name and collection name
	api_key = os.environ.get('DOTA2_API_KEY')
	account_id = int(os.environ.get('DOTA2_ACCOUNT_ID'))
	db_name = 'dota2'
	collection_name = 'aaron'

	cred = Credentials(api_key = api_key, account_id = account_id,
					   db_name = db_name, collection_name = collection_name)
	
	setup(cred, skip=True)
	# results_primary = calc_primary_attribute_stats(cred)
	# print results_primary

	calc_primary_attribute_composition(cred)
