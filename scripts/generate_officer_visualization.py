# -*- coding: UTF-8 -*-

"""Create interactive visualization of graph for network of officers
included in Myanmar Financial leak.

This script assumes that Gephi has been previously used to generate a graph
drawing, and included a modularity class attribute.

"""

###############################################################################

import pickle
from collections import Counter
import os

from bs4 import BeautifulSoup
import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
from matplotlib.colors import rgb2hex

import holoviews as hv
from bokeh.models import HoverTool
import colorcet
hv.extension('bokeh')
renderer = hv.renderer('bokeh')

###############################################################################

# Colors used for different graph modularity classes
COLORS = colorcet.glasbey_light

# Pandas DataFrame of edges, generated by `generat_gexf.py`
INPUT_EDGES_DF = '../output/officers_edges.pkl'

# GEXF file generated bu Gephi
INPUT_GEXF = '../output/officers_graph_layout.gexf'

NODES_ATTRIBUTES_DF = '../output/officers_attributes.pkl'

# File to save visualization to (without `.html` extension)
OUTPUT_HTML = '../visualizations/officer_graph'

# Scaling factors for visualization glyphs
EDGE_SCALING = 0.5
NODE_SCALING = 1.25

###############################################################################

def get_edge_color( row ):

  """Color edge based on the mean of its node colors
  """

  rgb = 0.5 * (
    node_color_dict[ row[ 'source' ] ] + \
    node_color_dict[ row[ 'target' ] ] )

  return rgb2hex( rgb )

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

def hex2rgb( hex ):

  """Convert a hex color to an RGB color.

  Taken from:
    https://gist.github.com/matthewkremer/3295567

  """

  hex = hex.lstrip( '#' )
  hlen = len( hex )
  hlen3 = int( hlen / 3 )

  return np.asarray( tuple(
    int( hex[ i : i + hlen3 ], 16 ) / 255. for i in range( 0, hlen, hlen3 ) ) )

###############################################################################

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
# Read in GEXF file generated by Gephi, store node information in a DataFrame
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

with open( INPUT_GEXF, 'r' ) as f:
  data = f.read( )

# Use BeautifulSoup to parse Gephi XML to find list of all nodes
soup = BeautifulSoup( data, 'xml' )
nodes = soup.find( 'nodes' )

# Get list of all nodes
nodes = nodes.find_all( 'node' )

data = list( )

# Loop over all nodes
for i, node in enumerate( nodes ):

  # Create dict containing data for each node
  row = dict( )

  row[ 'x' ] =  float( node.find( 'viz:position' )[ 'x' ] )
  row[ 'y' ] =  float( node.find( 'viz:position' )[ 'y' ] )
  row[ 'index' ] = i
  row[ 'size' ] = float( node.find( 'viz:size' )[ 'value' ] ) / NODE_SCALING
  row[ 'unique' ] = node['id']
  row[ 'mod_class' ] = int( node.find(
    'attvalue', {'for' : 'modularity_class' } ) [ 'value' ] )

  # Append the dict of data to the list of row data
  data.append( row )

# Convert list of dicts to DataFrame
nodes_df = pd.DataFrame( data = data)

# convert string representation of unique officer tuple to tuple of strings
nodes_df[ 'unique' ] = nodes_df[ 'unique' ].apply( eval )

# Define conversion dict between unique officer tuple and node index
unique_to_idx = dict( zip( nodes_df[ 'unique' ], nodes_df[ 'index'] ) )

# Define spatial bounds of graph
graph_extents = (
  nodes_df[ 'x' ].min( ),
  nodes_df[ 'y' ].min( ),
  nodes_df[ 'x' ].max( ),
  nodes_df[ 'y' ].max( ), )

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
# Incorporate attribute information about each officer
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

# Read in attribute information
nodes_attributes_df = pd.read_pickle( NODES_ATTRIBUTES_DF )

# Rename the column for the corporation ID number to be consistent with the
# corresponding column in `nodes_df`
nodes_attributes_df.rename(
  columns = { 'OfficerUnique' : 'unique'}, inplace = True )

# Merge node attributes with nodes dataframe
nodes_df = nodes_df.merge( nodes_attributes_df, how = 'left', on = 'unique', )

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
# Color each node according to its modularity class
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

# Sort modularity classes by most common
mod_classes = np.asarray(
  Counter( nodes_df[ 'mod_class' ] ).most_common( ) )[ :, 0 ]

# Number of colors included in specified colormap
N_colors = len( COLORS )

# Initialize list of colors (we don't assume that the number of colors is equal
# to or gerater than the number of modularity classes, so we repeat the colors)
mod_class_colors = list( )

for i in range( len( mod_classes ) ):
  mod_class_colors.append( hex2rgb( COLORS[ i % N_colors ] ) )

# Define dict that maps a modularity class to its corresponding color
mod_color_dict = dict( zip( mod_classes, mod_class_colors ) )

# Store color of node's modularity class as a column
nodes_df[ 'color_rgb' ] = nodes_df[ 'mod_class' ].map( mod_color_dict )
nodes_df[ 'color' ] = nodes_df[ 'color_rgb' ].apply( rgb2hex )

# Define dict that maps a node index to its corresponding modularity class color
node_color_dict = dict( zip( nodes_df[ 'index' ], nodes_df[ 'color_rgb' ] ) )

# Remove the RGB color column (otherwise Holoviews can't sort the DataFrame,
# which leads to an error)
nodes_df = nodes_df.drop( labels = 'color_rgb', axis = 'columns' )

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
# Read in edge data, color each edge according to the modularity classes of
# its source and target nodes
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

# Read in edge data
edges_df = pd.read_pickle( INPUT_EDGES_DF )

# Convert corporation ID to node index
edges_df[ 'source' ] = edges_df[ 'source' ].map( unique_to_idx )
edges_df[ 'target' ] = edges_df[ 'target' ].map( unique_to_idx )

# Color each edge according to its nodes
edges_df[ 'color' ] = edges_df.apply( get_edge_color, axis = 1 )

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
# Convert edge and node DataFrames into Holoviews graph, define tooltips
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

# Convert node DataFrame to HoloViews object
hv_nodes = hv.Nodes( nodes_df )

# Create HoloViews Graph object from nodes and edges, with x and y limits
# bounded by `GRAPH_EXTENTS`
hv_graph = hv.Graph(
  ( edges_df, hv_nodes ), )

# Define custom hover tooltip
hover = HoverTool( tooltips = [
  ( 'Officer Name', '@FullName' ),
  ( 'ID', '@IdNumber' ),
  ( 'Company 1', '@Company1' ),
  ( 'Company 2', '@Company2' ),
  ( 'Company 3', '@Company3' ), ] )

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#
# Define configuration options for visualization, and render visualization
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++#

# Specify Holoviews options
hv_graph.opts(
  node_radius = 'size',
  edge_color = 'color',
  node_color = 'color',
  node_hover_fill_color = '#EF4E02',
  edge_alpha = 0.2,
  edge_line_width = 'weight',
  edge_hover_line_color = '#DF0000',
  responsive = True,
  aspect = 1,
  bgcolor = 'black',
  tools = [ hover ],
  xticks = 0,
  yticks = 0,
  xlabel = '',
  ylabel = '')

# Create output directory if it doesn't already exist
os.makedirs( os.path.dirname( OUTPUT_HTML ), exist_ok = True )

# Generate visualization
renderer.save( hv_graph, OUTPUT_HTML )

###############################################################################