# -*- coding: UTF-8 -*-

"""Create networks of corporate officers and corporations, from Myanmar
Financial data leak.

Data originally downloaded from the website:

  https://ddosecrets.com/wiki/Myanmar_Financials

Prior to running this script, extract corporate records into a separate folder
using the terminal command:

  tar -I zstd -xf myco_details.tar.zst -C myco_details

"""

###############################################################################

import os
import json
from collections import Counter

import pandas as pd
import networkx as nx

###############################################################################

# Directory containing JSON files for each company
INPUT_DIR = '../Myanmar_Financials/myco_details/'

# List of relevant subkeys in the `Corp` attribute
CORP_KEYS = [
  'CorpId',
  'CompanyName',
  'RegistrationNumber',
  'HoldingCompanyName',
  'HoldingCompanyRegNumber',
  'RegistrationDate',
  'AltName', ]

# List of relevant subkeys in the `Officers` attribute
OFFICER_KEYS = [
  'CorpOfficerId',
  'FullNameNormalized',
  'FullName',
  'Nationality',
  'IdNumber' ]

# Directory to save results to
OUTPUT_DIR = '../output'

###############################################################################

def get_most_popular_officers( corpid ):

  """Get the 3 officers from the given corporation that are officers in the
  most companies. If there are fewer than 3 officers in the corporation, empty
  strings are returned.
  """

  # Create dict whose keys are the officer, and values are the number of
  # companies that officer is an officer for
  _d = {
    officer : len( companies_by_officer[ officer ] ) \
      for officer in officers_by_company[ corpid ] }

  # Create list of officers, sorted by number of companies they're officers for
  l = list(
    { k : v for k, v in sorted(
      _d.items( ),
      key = lambda item: item[ 1 ], reverse = True ) }.keys( ) )

  # Get length of list (i.e. number of officers for the given corporation)
  ll = len( l )

  # If there are fewer than 3 officers, fill the rest with None
  l = l[ : min( 3, ll ) ]
  l.extend( [ None ] * ( 3 - ll ) )

  # Map officer unique tuple to officer full name
  names = list( unique_to_name.get( name, '' ) for name in l )

  return names

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

def get_most_popular_companies( unique ):

  """Get the 3 companies for the given officer that the most officers are
  officers of. If there are fewer than 3 corporations for the officer, empty
  strings are returned.
  """

  # Create dict whose keys are the corporation ID, and values are the number of
  # officers that company has
  _d = {
    corpid : len( officers_by_company[ corpid ] ) \
      for corpid in companies_by_officer[ unique ] }

  # Create list of corporations, sorted by number of officers they have
  l = list(
    { k : v for k, v in sorted(
      _d.items( ),
      key = lambda item: item[ 1 ], reverse = True ) }.keys( ) )

  # Get length of list (i.e. number of corporations for the given officer)
  ll = len( l )

  # If there are fewer than 3 corporations, fill the rest with None
  l = l[ : min( 3, ll ) ]
  l.extend( [ None ] * ( 3 - ll ) )

  # Map corporation ID to corporation name
  names = list( corpid_to_company_name.get( name, '' ) for name in l )

  return names

###############################################################################

# Read in all JSON files containing company data
files = os.listdir( INPUT_DIR )

# Initialize list of dicts to store corporation information
company_list = list( )

# Loop over all JSON files
for file in files:

  # Open the file, store contents as a dict
  with open( os.path.join( INPUT_DIR, file ), 'r' ) as f:
    data = json.load( f )

  # Append the dict of corporation data to the list
  company_list.append( data )

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
# Create DataFrame where each row contains information about one officer
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

# Initialize list of dicts to store officer-level information
officer_dict_list = list( )

# Loop over all corporations
for i, company in enumerate( company_list ):

  # Define dict with information about the given corporation
  corp_dict = {
    key : company.get( 'Corp', dict( ) ).get( key ) for key in CORP_KEYS }

  # Loop over all officers for the given corporation
  for officer in company.get( 'Officers', list( ) ):

    # Define dict with information about the given officer
    officer_dict = { key : officer.get( key ) for key in OFFICER_KEYS }

    # combine officer dict and corporation dict into a single dict
    full_dict = { **officer_dict, **corp_dict }

    # append the combined dict to the list of dicts
    officer_dict_list.append( full_dict )

# Convert list of dicts to Pandas DataFrame
df = pd.DataFrame( officer_dict_list )

# Create tuple that uniquely specifies a single officer (since two different
# people may have the same name OR ID number, but they probably won't BOTH be
# the same)
df[ 'OfficerUnique' ] = df.apply(
  lambda row : ( row[ 'FullNameNormalized' ], row[ 'IdNumber' ] ), axis = 1 )

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
# Get set of all officers for a given company, and set of all companies for
# a given officer
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

# Create dict where keys are the corporate IDs, and values are the set of all
# unique tuples for officers of the corporation
_officers_by_company = df.groupby( 'CorpId' ).agg( { 'OfficerUnique' : set } )
officers_by_company = dict( _officers_by_company[ 'OfficerUnique' ] )

# Create dict where keys are unique officer tuples, and the values are the set
# of all corporation IDs that individual is the officer of
_companies_by_officer = df.groupby( 'OfficerUnique' ).agg( { 'CorpId' : set } )
companies_by_officer = dict( _companies_by_officer[ 'CorpId' ] )

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
# Create list of edges for officer network, where the nodes are individual
# officers, and the weight of the edge between two nodes is the number of
# companies the two officers are both officers of
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

# Initialize list to store edge tuple (source, target, weight) for each
# edge in the officer-aggregated network
officer_edges = list( )

# Loop over all unique officer tuples
for unique in companies_by_officer.keys( ):

  # Find all individuals that are officers in the same companies as the officer
  c = Counter( [ officer for corpid in companies_by_officer[ unique ] \
    for officer in officers_by_company[ corpid ] ] )

  # Remove self-loops
  del c[ unique ]

  # For each individual the given officer shares a company with, create an
  # edge (tuple of source, target, and weight)
  for unique_2, weight in c.items( ):

    # Sort target and source so it's easy to remove duplicates
    element = ( *sorted( [ unique, unique_2 ] ), weight )

    officer_edges.append( element )

# Remove duplicates
officer_edges = list( set( officer_edges ) )

# Initialize list to store edge data (source, target, attribute dict) for each
# edge (NetworkX seems to require that the weight is specified as a dict)
officer_edges_bunch = list( )

# Loop over edges, make the weight a dict
for edge in officer_edges:

  source, target, weight = edge
  officer_edges_bunch.append(  ( source, target, { 'weight' : weight } ) )

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
# Create list of edges for corporation network, where the nodes are individual
# corporations, and the weight of the edge between two nodes is the number of
# officers the two corporations share
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

# Initialize list to store edge tuple (source, target, weight) for each edge in
# the corporation-aggregated network
corp_edges = list( )

# Loop over all corporation IDs
for corpid in officers_by_company.keys( ):

  # Find all corporations that are have mutual officers with the given
  # corporation
  c = Counter( [ corp for officer in officers_by_company[ corpid ] \
    for corp in companies_by_officer[ officer ] ] )

  # Remove self-loops
  del c[ corpid ]

  # For each corporation the given corporation shares a company with, create an
  # edge (tuple of source, target, and weight)
  for corpid_2, weight in c.items( ):

    # Sort target and source so it's easy to remove duplicates
    element = ( *sorted( [ corpid, corpid_2 ] ), weight )

    corp_edges.append( element )

# Remove duplicates
corp_edges = list( set( corp_edges ) )

# Initialize list to store edge data (source, target, attribute dict) for each
# edge (NetworkX seems to require that the weight is specified as a dict)
corp_edges_bunch = list( )

for edge in corp_edges:

  source, target, weight = edge
  corp_edges_bunch.append(  ( source, target, { 'weight' : weight } ) )

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
# Use list of edges to create the two graphs, find the largest connected
# subgraphs of each, and export as Gephi files
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

# Create NetworkX graph for officer-aggregated network
_G_officers = nx.Graph( )
_G_officers.add_edges_from( officer_edges_bunch )

# Find largest connected subgraph of the officer network
G_officers = _G_officers.subgraph(
  max( nx.connected_components( _G_officers ), key = len ) )

# Create NetworkX graph for corporation-aggregated network
_G_corps = nx.Graph( )
_G_corps.add_edges_from( corp_edges_bunch )

# Find largest connected subgraph of the corporation network
G_corps = _G_corps.subgraph(
  max( nx.connected_components( _G_corps ), key = len ) )

# Create output directory if it doesn't already exist
os.makedirs( OUTPUT_DIR, exist_ok = True )

# Write both officer and corporation networks to GEXF files
nx.write_gexf(
  G = G_officers,
  path = os.path.join( OUTPUT_DIR, 'officers_graph.gexf' ) )

nx.write_gexf(
  G = G_corps,
  path = os.path.join( OUTPUT_DIR, 'corporations_graph.gexf' ) )

# Get set of all officers and corporations included in the subgraphs
filtered_officers = set( G_officers.nodes )
filtered_corps = set( G_corps.nodes )

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
# Save picked Pandas DataFrames of edges to file
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

# Get list of all edges (in tuple form) that are in the filtered officer network
filtered_officer_edges = [
  ( source, target, attr[ 'weight' ] ) \
    for source, target, attr in list( G_officers.edges( data = True ) ) ]

# Store officer edges as DataFrame
officer_df = pd.DataFrame(
  data = filtered_officer_edges,
  columns = [ 'source', 'target', 'weight' ] )

# Save officer edges as pickled DataFrame
officer_df.to_pickle( os.path.join( OUTPUT_DIR, 'officers_edges.pkl' ) )

# Get list of all edges (in tuple form) that are in the filtered corporation
# network
filtered_corporation_edges = [
  ( source, target, attr[ 'weight' ] ) \
    for source, target, attr in list( G_corps.edges( data = True ) ) ]

# Store corporation edges as DataFrame
corporation_df = pd.DataFrame(
  data = filtered_corporation_edges,
  columns = [ 'source', 'target', 'weight' ] )

# Save corporation edges as pickled DataFrame
corporation_df.to_pickle( os.path.join( OUTPUT_DIR, 'corporations_edges.pkl' ) )

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
# Create DataFrames of corporation and officer attributes
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

# Define dict that maps unique officer tuples to the officer's full name
unique_to_name = dict( zip(
  df[ 'OfficerUnique' ],
  df[ 'FullName' ].apply( lambda s : s.strip( ) ) ) )

# Define dicts that return the first, second, and third most "popular" officers
# for all corporations
most_popular_officer_1 = {
  corpid : get_most_popular_officers( corpid )[ 0 ] \
    for corpid in filtered_corps }
most_popular_officer_2 = {
  corpid : get_most_popular_officers( corpid )[ 1 ] \
    for corpid in filtered_corps }
most_popular_officer_3 = {
  corpid : get_most_popular_officers( corpid )[ 2 ] \
    for corpid in filtered_corps }

# Define dict that maps corporation ID to the company name
corpid_to_company_name = dict( zip( df[ 'CorpId' ], df[ 'CompanyName' ] ) )

# Define dict that maps corporation ID to the company alternative name
# (usually in Burmese)
corpid_to_alt_name = dict( zip( df[ 'CorpId' ], df[ 'AltName' ] ) )

# Create DataFrame of information attributes for each corporation
cdf = pd.DataFrame( )
cdf[ 'CorpId' ] = list( filtered_corps )

cdf[ 'CompanyName' ] = cdf[ 'CorpId' ].map( corpid_to_company_name )
cdf[ 'AltName' ] = cdf[ 'CorpId' ].map( corpid_to_alt_name )

cdf[ 'Officer1' ] = cdf[ 'CorpId' ].map( most_popular_officer_1 )
cdf[ 'Officer2' ] = cdf[ 'CorpId' ].map( most_popular_officer_2 )
cdf[ 'Officer3' ] = cdf[ 'CorpId' ].map( most_popular_officer_3 )

# Save corporation attributes as pickled DataFrame
cdf.to_pickle( os.path.join( OUTPUT_DIR, 'corporations_attributes.pkl' ))

#-----------------------------------------------------------------------------#

# Define dicts that return the first, second, and third most "popular"
# corporations for all officers
most_popular_company_1 = {
  unique : get_most_popular_companies( unique )[ 0 ] \
    for unique in companies_by_officer.keys( ) }
most_popular_company_2 = {
  unique : get_most_popular_companies( unique )[ 1 ] \
    for unique in companies_by_officer.keys( ) }
most_popular_company_3 = {
  unique : get_most_popular_companies( unique )[ 2 ] \
    for unique in companies_by_officer.keys( ) }

# Define dict that maps unique officer tuple to the officer's ID number
unique_to_id = dict( zip( df[ 'OfficerUnique' ], df[ 'IdNumber' ] ) )

# Create DataFrame of information attributes for each officer
odf = pd.DataFrame( )
odf[ 'OfficerUnique' ] = list( filtered_officers )

odf[ 'FullName' ] = odf[ 'OfficerUnique' ].map( unique_to_name )
odf[ 'IdNumber' ] = odf[ 'OfficerUnique' ].map( unique_to_id )

odf[ 'Company1' ] = odf[ 'OfficerUnique' ].map( most_popular_company_1 )
odf[ 'Company2' ] = odf[ 'OfficerUnique' ].map( most_popular_company_2 )
odf[ 'Company3' ] = odf[ 'OfficerUnique' ].map( most_popular_company_3 )

# Save officer attributes as pickled DataFrame
odf.to_pickle( os.path.join( OUTPUT_DIR, 'officers_attributes.pkl' ))

###############################################################################