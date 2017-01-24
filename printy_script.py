#!/usr/bin/python

import sys
import re
import math
import printy_helpers
from printy_keys import *

#repeat the first M layers N times to promote adhesion to build platform
base_layer_count = 3 #M layers, minimum 1
base_layer_over_cure = 10 #N times, minimum 1

#repeat other layers by P times within the same layer
normal_layer_over_cure = 2 #P times, minimum 1

laser_power = 0.02 #0.02 = 20mW

#layers with path energy greater than A (joules) is considered to be sticky, will insert an extra retract within the layer
max_energy_threshold = 1 #joules

#layers with fairly low energy should not stick too hard, this allows us to use a faster retract and less retract distance
#not implemented yet
fast_retract_energy_threshold = 0.03

#layers with less energy than this threshold is not considered a printing layer and does not get any extra retracts.
#this can come in handy for vase prints!
min_energy_threshold = 0.00000000001 #joules

#this is the extra lift code to be inserted within a layer so it doesn't peel too hard
sublayer_lift_code = ['; start lift code between sublayers\n',
                      'G91 ; relative position\n',
                      'G1 Z5 F100\n',
                      'G1 Z-5 F300\n', #go down faster since there's no resistance
                      'G90 ; absolute position\n',
                      'G4 P200 ; dwell in milliseconds\n',
                      '; end lift code between sublayers\n']

#this is the code to be inserted between layers if this is determined not to be a vase print
layer_lift_code = ['; start lift code between layers\n',
                   'G91 ; relative position\n',
                   'G1 Z5 F100 ; layer lift code\n',
                   'G1 Z-4.8 F300\n', # be careful with this one, it relies on the next line to contain Z to get to the right spot
                   'G90 ; absolute position\n',
                   'G4 P200 ; dwell in milliseconds\n',
                   '; end lift code between layers\n']

layer_lift_code_fast = ['; start fast lift code between layers\n',
                   'G91 ; relative position\n',
                   'G1 Z2 F200 ; layer lift code\n',
                   'G1 Z-1.8 F300\n', # be careful with this one, it relies on the next line to contain Z to get to the right spot
                   'G90 ; absolute position\n',
                   'G4 P200 ; dwell in milliseconds\n',
                   '; end fast lift code between layers\n']

#this is the initial code for homing
initial_lift_code = ['; start initial lift code\n',
                     'G28 ; home all axes\n', 'G91 ; relative position\n',
                     'G1 Z10 F200\n', 'G1 Z-10 F20\n', #drop slowly to squeeze out any air bubbles
                     'G1 Z5 F200\n', 'G1 Z-4 F200\n', #asymmetric, slosh a few times to mix the resin
                     'G1 Z4 F200\n', 'G1 Z-4 F200\n'  ,
                     'G1 Z4 F200\n', 'G1 Z-4 F200\n',
                     'G1 Z4 F200\n', 'G1 Z-4 F200\n',
                     'G1 Z4 F200\n', 'G1 Z-4 F200\n', #doesn't go all the way back to 0 so the gcode move down to the correct location.
                     'G90 ; absolute position\n', #avoids the very sticky lift from 0
                     'G4 P1000 ; dwell in milliseconds\n',
                     '; end initial lift code\n']


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

home_layer = 1
base_layer = base_layer_count

for layer_data_element in layer_data:
    layer_data_element[stats] = {}
    layer_data_element[stats][stat_line_energy] = []
    layer_data_element[stats][stat_line_feedrate] = []
    layer_data_element[stats][stat_sublayer_indices] = []
    layer_data_element[processed_data] = []
    layer_data_element[extra_feedrate_data] = []
    layer_data_element[extra_move_data] = []

    if home_layer == 1:
        layer_data_element[stats][stat_over_cure] = -1
    elif base_layer > 0:
        layer_data_element[stats][stat_over_cure] = base_layer_over_cure
        base_layer -= 1
    else:
        layer_data_element[stats][stat_over_cure] = normal_layer_over_cure

    #total energy should depend on the amount of over cure
    over_cure_factor = 1
    if layer_data_element[stats][stat_over_cure] > 1:
        over_cure_factor = layer_data_element[stats][stat_over_cure]

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
            current_feed_rate = float(temp_rate) #convert mm/min to mm/sec
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

        if printy_helpers.isG28(line):
            home_layer = 0

        if not printy_helpers.isMove(line):
            layer_data_element[stats][stat_line_energy] += [draw_energy]
            layer_data_element[stats][stat_line_feedrate] += [current_feed_rate]
            continue

        if current_eloc > previous_eloc:
            segment_distance = ((current_xloc - previous_xloc)**2 + (current_yloc - previous_yloc)**2)**0.5
            print_length += segment_distance
            segment_time = segment_distance / current_feed_rate * 60.0
            print_time += segment_time
            draw_energy += segment_time * laser_power * over_cure_factor

        previous_xloc = current_xloc
        previous_yloc = current_yloc
        previous_eloc = current_eloc
        layer_data_element[stats][stat_line_energy] += [draw_energy]
        layer_data_element[stats][stat_line_feedrate] += [current_feed_rate]

    layer_data_element[stats][stat_time]=print_time
    layer_data_element[stats][stat_length]=print_length


    layer_data_element[stats][stat_energy]=draw_energy


    #time to see if we need to divide the layer into multiple sublayers
    if draw_energy < max_energy_threshold:
        layer_data_element[processed_data] = [layer_data_element[raw_data]] #all of raw_data fits on one sublayer
    else: #time to divide
        sublayer_threshold = draw_energy/math.ceil(draw_energy/max_energy_threshold) #figure out how many slices
        current_section = sublayer_threshold
        #store a list of indices where the sublayer splits should happen
        sublayer_indices = []
        index = 0
        for current_energy in layer_data_element[stats][stat_line_energy]:
            if current_energy > current_section:
                sublayer_indices += [index]
                current_section += sublayer_threshold
            index += 1
        layer_data_element[stats][stat_sublayer_indices] = sublayer_indices

        #used the indices to split each layer into multiple sublayers
        previous_index = 0
        for index in sublayer_indices:
            layer_data_element[processed_data] += [layer_data_element[raw_data][previous_index:index]]
            previous_index = index
        layer_data_element[processed_data] += [layer_data_element[raw_data][previous_index:]]

        #use the indices to find out the gcode

    #need to add a line for feedrate so the G-code resumes correctly
    #this grabs the starting feedrate for each sublayer
    extra_gcode = []
    for sublayerindex in [0]+layer_data_element[stats][stat_sublayer_indices]:
        extra_gcode += ['G0 F%d ; extra feedrate data\n' %(layer_data_element[stats][stat_line_feedrate][sublayerindex])]
    layer_data_element[extra_feedrate_data] = extra_gcode

    #need to add a line to go back to the beginning without any e value so the laser can start from the right spot
    extra_gcode = []
    for sublayer in layer_data_element[processed_data]:
        stripped_first = printy_helpers.stripELoc(sublayer)
        if stripped_first != -1:
            extra_gcode += [stripped_first + ';extra move data\n']
        else:
            extra_gcode += [';failed to generate extra move data\n']
    #store it in the data structure
    layer_data_element[extra_move_data] = extra_gcode

    #print(layer_data_element[extra_feedrate_data])

#for layer in layer_data:
#    print(layer)

#take all the processed data to the output
output_data = []

home_layer = 1
for layer in layer_data:
    #just copy and paste until we find G92 (home axes)
    if home_layer == 1:
        output_data += layer[processed_data]
        if layer[stats][stat_over_cure] != -1:
            home_layer = 0
            output_data += [initial_lift_code]

    #for the reset of the layers, repeat controled by stat_over_cure
    else:
        output_data += printy_helpers.repeatLayerData(layer, layer[stats][stat_over_cure], sublayer_lift_code)

        #insert extra lift between layers
        #if the energy is low, such as a vase print, don't add a lift between layers
        if layer[stats][stat_energy] > min_energy_threshold:
            output_data += [layer_lift_code]
        #print(layer[raw_data])

#output the processed gcode file
with open(out_file_location, 'w') as f:
    for layer in output_data:
        for line in layer:
            f.write(line)
