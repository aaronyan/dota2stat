import os, json, pprint, pandas as pd, matplotlib.pyplot as plt, seaborn
import numpy as np, time
from dota2py import api
from pymongo import Connection

pp = pprint.PrettyPrinter(indent = 2)
pd.set_option('display.width', 2000)
pd.set_option('display.max_columns', 30)

class Credentials(object):
	def __init__ (self, api_key = None, account_id = None, \
				  db_name = None, collection_name = None, \
				  start_match_id = None):
		self.api_key = api_key
		self.account_id = account_id
		self.db_name = db_name
		self.collection_name = collection_name
		self.start_match_id = start_match_id

"""
Setup Functions / Pull Data from API - Personal
"""

def gen_match_ids(cred):
	# Create match_idn list of user-specific matches
	api_key = cred.api_key
	account_id = cred.account_id
	db_name = cred.db_name
	collection_name = cred.collection_name
	start_match_id = cred.start_match_id

	api.set_api_key(api_key)
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
	collection.create_index('match_id',unique=True,background=True, drop_dups=True)

	match_ids = gen_match_ids(cred)
	for idx, match_id in enumerate(match_ids):
		if collection.find({'match_id':match_id}).count() == 0:
			collection.insert(get_match_details(cred, match_id))
			print "Inserting match details %s/%s into mongoDB..." %(idx+1, len(match_ids))
			time.sleep(.6)

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

def abbreviate_attribute(att):
	abbrev = {'Strength': 'STR',
			  'Intelligence': 'INT',
			  'Agility': 'AGI'}
	return abbrev[att]

def count_comp(attr_summary):
	new_col = []
	for indx,v in attr_summary.iterrows():
		s = 0; a = 0; i = 0;
		s = sum([1 for j in v if j == 'STR'])
		a = sum([1 for j in v if j == 'AGI'])
		i = sum([1 for j in v if j == 'INT'])
		new_col.append(str(s)+str(a)+str(i))
	attr_summary['composition'] = new_col

	return attr_summary


def team_att_comp(all_players_abbrev_df):
	radiant = all_players_abbrev_df.iloc[:,0:5]
	dire = all_players_abbrev_df.iloc[:,5:10]
	radiant = count_comp(radiant)
	dire = count_comp(dire)

	compare_comp = radiant.loc[:,['composition']]
	compare_comp.columns = ['radiant']
	compare_comp['dire'] = dire['composition']

	return compare_comp
	

def calc_primary_attribute_composition(cred):
	heroes = hereos_composition(cred)
	all_players_df = pd.DataFrame.from_dict(heroes)
	df_attribute_cols = all_players_df.columns.values[:len(all_players_df.columns.values)-1]
	df_new_attribute_cols = ['attr_'+ str(x) for x in df_attribute_cols]
	hero_attributes = create_hero_attribute_df()
	all_players_abbrev_df = pd.DataFrame()

	for x,x2 in zip(df_attribute_cols, df_new_attribute_cols):
		temp_col = [abbreviate_attribute(hero_attributes.ix[i]['primary_attribute']) \
					for i in all_players_df[x]]
		all_players_abbrev_df[x2] = temp_col

	compare_comp = team_att_comp(all_players_abbrev_df)
	compare_comp['radiant_win'] = all_players_df['radiant_win']
	radiant_comp = compare_comp.loc[:,['radiant','radiant_win']]
	radiant_comp_win = radiant_comp.groupby(['radiant'], sort=True).sum()
	radiant_comp_total = radiant_comp.groupby(['radiant'], sort=True).count()
	radiant_comp_win['total'] = radiant_comp_total
	percent_win = [x/y for x,y in zip(radiant_comp_win['radiant_win'],radiant_comp_win['total'])]
	radiant_comp_win['percent'] = percent_win
	print radiant_comp_win
	# print compare_comp


if __name__ == "__main__":
	# API Credentials and Mongo db name and collection name
	api_key = os.environ.get('DOTA2_API_KEY')
	account_id = None # account_id = int(os.environ.get('DOTA2_ACCOUNT_ID'))
	db_name = 'dota2'
	collection_name = 'public'
	start_match_id = None

	cred = Credentials(api_key = api_key, account_id = account_id,
					   db_name = db_name, collection_name = collection_name,
					   start_match_id = start_match_id)
	
	"""
	Personal Games - Analysis
	"""
	# setup(cred, skip=True)
	# results_primary = calc_primary_attribute_stats(cred)
	# print results_primary

	"""
	Public Games - Analysis
	"""
	setup(cred)
	# con = Connection()
	# db = getattr(con, db_name)
	# collection = getattr(db, collection_name)

	# all_match_ids = list(collection.find({},{'match_id'}))
	# # print all_match_ids

	# only_ids = [i['match_id'] for i in all_match_ids ]

	# seen = set()
	# uniq = [x for x in only_ids if x not in seen and not seen.add(x)]

	# print len(only_ids)
	# print len(uniq)


