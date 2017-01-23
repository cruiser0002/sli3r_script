#!/usr/bin/python

import sys
import re
import printy_helpers
import math
#from printy_helpers import *

#repeat the first M layers N times to promote adhesion to build platform
base_layer_count = 3 #M layers, minimum 1
base_layer_over_cure = 3 #N times, minimum 1

#repeat other layers by P times within the same layer
normal_layer_over_cure = 1 #P times, minimum 1

laser_power = 0.02 #0.02 = 20mW

#layers with path length greater than A (joules) is considered to be sticky, will insert an extra retract within the layer
max_energy_threshold = 0.3 #joules

#layers with less energy than this threshold is not considered a printing layer and does not get any extra retracts.
#this can come in handy for vase prints!
min_energy_threshold = 0.0001 #joules

#this is the extra lift code to be inserted within a layer so it doesn't peel too hard
extra_lift_code = ['G91 ; relative position\n',
                   'G1 Z5 F100 ; extra lift code within a slice\n',
                   'G1 Z-5\n',
                   'G90 ; absolute position\n']

#this is the code to be inserted between layers if this is determined not to be a vase print
layer_lift_code = ['G91 ; relative position\n',
                   'G1 Z5 F100 ; layer lift code\n',
                   'G1 Z-4.8\n', # be careful with this one, it relies on the next line to contain Z to get to the right spot
                   'G90 ; absolute position\n']

#this is the initial code for homing
initial_lift_code = ['G28 ; home all axes\n', 'G91 ; relative position\n',
                     'G1 Z10 F200\n', 'G1 Z-10 F20\n', #drop slowly to squeeze out any air bubbles
                     'G1 Z5 F200\n', 'G1 Z-4 F200\n', #asymmetric, slosh a few times to mix the resin
                     'G1 Z4 F200\n', 'G1 Z-4 F200\n'  ,
                     'G1 Z4 F200\n', 'G1 Z-4 F200\n',
                     'G1 Z4 F200\n', 'G1 Z-4 F200\n',
                     'G1 Z4 F200\n', 'G1 Z-4 F200\n', #doesn't go all the way back to 0 so the gcode move down to the correct location.
                     'G90 ; absolute position\n'] #avoids the very sticky lift from 0


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

#layer_data is an array whose index reflects sliced layers
#each layer_data element is a dictionary
#raw_data contains a list whose elements represent a line of G-code

#statistics about each layer in a list of dictionaries
#layer_stats contains a dictionary where
#layer_length is printing length in mm
#layer_time is total time in seconds
#layer_energy in joules
#line_energy is a list of the energy of each line of G-code

#processed_data is a list whose elements are sublayers of a layer
#each sublayer is a list whose elements are lines of G-code

#The naive implementation is to insert extra lift codes whenever the accumulated energy looks too high.
#The best implementation is to rearrange the gocdes so print chunks are grouped together for the most efficient lift while maintaining boundaries

raw_data = 'raw_data'

stats = 'layer_stats'
stat_length = 'stat_length' #in mm
stat_time = 'stat_time' #in seconds
stat_energy = 'stat_energy' #in joules
stat_line_energy = 'stat_line_energy'

processed_data = 'processed_data'


#each print layer is now an array element in layer_data
#layer change happens at the start of a layer
with open(in_file_location, 'r') as f:

    one_layer = []
    for line in f:
        if printy_helpers.isLayerChange(line):
            layer_data_element = {}
            layer_data_element[raw_data] = one_layer
            layer_data += [layer_data_element]
            one_layer = []
        one_layer += [line]
    layer_data_element = {}
    layer_data_element[raw_data] = one_layer
    layer_data += [layer_data_element]

#some checks to make sure we process meaningful data
if len(layer_data) < 2:
    exit(1)



previous_xloc = 0
previous_yloc = 0
previous_eloc = 0
current_feed_rate = 0
current_xloc = 0
current_yloc = 0
current_eloc = 0

for layer_data_element in layer_data:
    layer_data_element[stats] = {}
    layer_data_element[stats][stat_line_energy] = []
    draw_energy = 0
    print_length = 0
    print_time = 0
    for line in layer_data_element[raw_data]:
        temp_rate = printy_helpers.getFeedRate(line)
        temp_x = printy_helpers.getXLoc(line)
        temp_y = printy_helpers.getYLoc(line)
        temp_e = printy_helpers.getELoc(line)
        temp_z = printy_helpers.getZLoc(line)

        if temp_rate != -1:
            current_feed_rate = float(temp_rate)/60.0 #convert mm/min to mm/sec
        if temp_x == -1:
            current_xloc = previous_xloc
        else:
            current_xloc = temp_x
        if temp_y == -1:
            current_yloc = previous_yloc
        else:
            current_yloc = temp_y
        if temp_e == -1:
            current_eloc = previous_eloc
        elif temp_e > current_eloc:
            current_eloc = temp_e

        if printy_helpers.isG92(line):
            if temp_e != -1:
                current_eloc = temp_e
                previous_eloc = temp_e

        if not printy_helpers.isMove(line):
            layer_data_element[stats][stat_line_energy] += [draw_energy]
            continue

        if current_eloc > previous_eloc:
            segment_distance = ((current_xloc - previous_xloc)**2 + (current_yloc - previous_yloc)**2)**0.5
            print_length += segment_distance
            segment_time = segment_distance / current_feed_rate
            print_time += segment_time
            draw_energy += segment_time * laser_power

        previous_xloc = current_xloc
        previous_yloc = current_yloc
        previous_eloc = current_eloc
        layer_data_element[stats][stat_line_energy] += [draw_energy]

    layer_data_element[stats][stat_time]=print_time
    layer_data_element[stats][stat_length]=print_length
    layer_data_element[stats][stat_energy]=draw_energy


    #time to see if we need to divide the layer into multiple sublayers
    if draw_energy < max_energy_threshold:
        layer_data_element[processed_data] = [layer_data_element[raw_data]] #all of raw_data fits on one sublayer
    else: #time to divide
        sublayer_threshold = draw_energy/math.ceil(draw_energy/max_energy_threshold) #figure out how many slices
        current_section = sublayer_threshold
        layer_data_element[processed_data] = []
        #print(len(layer_data_element[stats][stat_line_energy]))
        sublayer = [] #store a list of indices where the sublayer splits should happen
        sublayer_number = 1
        index = 0
        for current_energy in layer_data_element[stats][stat_line_energy]:
            if current_energy > current_section:
                sublayer += [index]
                sublayer_number += 1
                current_section = sublayer_threshold * sublayer_number
            index += 1

        previous_index = 0
        for index in sublayer:
            layer_data_element[processed_data] += [layer_data_element[raw_data][previous_index:index]]
            previous_index = index
        layer_data_element[processed_data] += [layer_data_element[raw_data][previous_index:]]

output_data = []
output_data += layer_data[0][processed_data]
output_data += [initial_lift_code]


for layer in layer_data[1:base_layer_count+1]:
    if (len(layer[processed_data]) <= 1):
        output_data += layer[processed_data]*base_layer_over_cure
    else:
        for sublayer in layer[processed_data][:-1]:
            output_data += sublayer*base_layer_over_cure
            output_data += [extra_lift_code]
        output_data += layer[processed_data][-1]*base_layer_over_cure
    if layer[stats][stat_energy] > min_energy_threshold:
        output_data += [layer_lift_code]


for layer in layer_data[base_layer_count+1:]:
    if (len(layer[processed_data]) <= 1):
        output_data += layer[processed_data]*normal_layer_over_cure
    else:
        for sublayer in layer[processed_data][:-1]:
            output_data += sublayer*normal_layer_over_cure
            output_data += [extra_lift_code]
        output_data += layer[processed_data][-1]*normal_layer_over_cure
    if layer[stats][stat_energy] > min_energy_threshold:
        output_data += [layer_lift_code]
    print(layer[raw_data])

#output the processed gcode file
with open(out_file_location, 'w') as f:
    for layer in output_data:
        for line in layer:
            f.write(line)
