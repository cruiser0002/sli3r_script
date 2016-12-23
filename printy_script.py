#!/usr/bin/python

import sys
import re
import printy_helpers
#from printy_helpers import *

#repeat the first M layers N times to promote adhesion to build platform
base_layer_count = 3 #M layers
base_layer_over_cure = 3 #N times

#repeat other layers by P times
normal_layer_over_cure = 3 #P times

#layers with path length greater than A (mm) is considered to be sticky, will insert an extra retract here
sticky_threshold = 1000 #A (mm)
extra_lift_code = ['G91 ; relative position\n', 'G1 Z5\n', 'G1 Z-5\n', 'G90 ; absolute position\n']

#argument processing
if len(sys.argv) < 2 or len(sys.argv) > 3:
    print ('usage: python printy_script.py filename or python printy_script.py infile outfile')
    exit(1)

#probably need some sort of checking here
in_file_location = sys.argv[1]
out_file_location = in_file_location
if len(sys.argv) == 3:
    out_file_location = sys.argv[2]

#load file into memory
layer_data = []

#each print layer is now an array element in layer_data
#layer change happens at the end of a layer
with open(in_file_location, 'r') as f:
    one_layer = []
    for line in f:
        if printy_helpers.isLayerChange(line):
            layer_data += [one_layer]
            one_layer = []
        one_layer += [line]
    layer_data += [one_layer]

#some checks to make sure we process meaningful data
if len(layer_data) < 2:
    exit(1)

#statistics about each layer in a list of dictionaries
#will help make processing smarter in the future
#not yet implemented
layer_stats = []
layer_length = 'layer_length' #in mm
layer_speeds = 'layer_speeds' #list of speeds
layer_time = 'layer_time' #in seconds


#processed data, each resulting layer is an array element
processed_layer_data = []
layer_index = 0

#insert additional lifts inside each sticky layer

#insert additional lifts after each layer change
layer_data = [layer_data[0]] + list(map(lambda x: x+extra_lift_code, layer_data[1:]))

#print(layer_data[0])
#repeat the first M layers N times to promote adhesion to build platform
#print(len(layer_data))

processed_layer_data += layer_data[0]
list_of_lists = list(map(lambda x: [x]*base_layer_over_cure, layer_data[1:base_layer_count]))
processed_layer_data += [val for sublist in list_of_lists for val in sublist]
#print(len(processed_layer_data))

#repeate the rest of the layers by P times
if(len(layer_data) >= base_layer_count):
    list_of_lists = list(map(lambda x: [x]*base_layer_over_cure, layer_data[base_layer_count:]))
    processed_layer_data += [val for sublist in list_of_lists for val in sublist]
#print(len(processed_layer_data))


#output the processed gcode file
with open(out_file_location, 'w') as f:
    for layer in processed_layer_data:
        for line in layer:
            f.write(line)
