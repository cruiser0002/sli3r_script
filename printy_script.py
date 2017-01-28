#!/usr/bin/python

import sys
import re
import math
import printy_helpers
from printy_keys import *

#repeat the first M layers N times to promote adhesion to build platform
#the first layer is usually thicker than the slicer thinks it is
#thus we should independently increase the over curing of the first layer
base_layer_count = 1 #M layers, minimum 1
base_layer_over_cure = 10 #N times, minimum 1

#repeat the next O layers by P times
#this is handly for making the previous layer where the actual object is much much harder so the object can be extracted more easily from the brim
early_layer_count = 2 #O layers, minimum 0
early_layer_over_cure = 3 #P times, minimum 1

#repeat other layers by Q times within the same layer
normal_layer_over_cure = 2 #Q times, minimum 1

laser_power = 0.02 #0.02 = 20mW
laser_dot_diameter = 0.1 #0.1mm
layer_height = 0.1 #0.1mm

#layers with path energy greater than A (joules) is considered to be sticky, will insert an extra retract within the layer
#make this a big number to disable
max_energy_threshold = 100 #0.1 joules to start

#layers with fairly low energy should not stick too hard, this allows us to use a faster retract and less retract distance
#make this a small number to disable
fast_retract_energy_threshold = 0.02

#the resin likely doesn't absorb energy in a linear scale and stickiness is related to energy absorbtion
#assume derating of absorbed laser power as a function of time. C*(1-e^(-t/tau))
#where C is the max curing energy absorbtion and tau is the time constant
#initial math based on speed of 100mm/s and a laser diameter of 0.1mm and assuming layer thickness of 0.1mm to keep math simple
resin_cure_tau = 0.001 #1ms to start
resin_max_cure = 0.01 #10mW/mm^2 to start

#layers with less energy than this threshold is not considered a printing layer and does not get any extra retracts.
#this can come in handy for vase prints!
min_energy_threshold = 0.00000000001 #joules

#this is the extra lift code to be inserted within a layer so it doesn't peel too hard
sublayer_lift_code = ['; start lift code between sublayers\n',
                      'G91 ; relative position\n',
                      'G1 Z5 F100\n',
                      'G4 P100 ; dwell in milliseconds\n',
                      'G1 Z-5 F300\n', #go down faster since there's no resistance
                      'G90 ; absolute position\n',
                      'G4 P100 ; dwell in milliseconds\n',
                      '; end lift code between sublayers\n']

#this is the code to be inserted between layers if this is determined not to be a vase print
layer_lift_code = ['; start lift code between layers\n',
                   'G91 ; relative position\n',
                   'G1 Z5 F100 ; layer lift code\n',
                   'G4 P100 ; dwell in milliseconds\n',
                   'G1 Z-4.9 F300\n', # be careful with this one, it relies on the next line to contain Z to get to the right spot
                   'G90 ; absolute position\n',
                   'G4 P100 ; dwell in milliseconds\n',
                   '; end lift code between layers\n']

layer_lift_code_fast = ['; start fast lift code between layers\n',
                   'G91 ; relative position\n',
                   'G1 Z2 F300 ; layer lift code\n',
                   'G4 P100 ; dwell in milliseconds\n',
                   'G1 Z-1.9 F300\n', # be careful with this one, it relies on the next line to contain Z to get to the right spot
                   'G90 ; absolute position\n',
                   'G4 P1 ; dwell in milliseconds\n',
                   '; end fast lift code between layers\n']

#this is the initial code for homing
initial_lift_code = ['; start initial lift code\n',
                     'G28 ; home all axes\n', 'G91 ; relative position\n',
                     'G1 Z10 F300\n', 'G1 Z-10 F20\n', #drop slowly to squeeze out any air bubbles
                     'G1 Z4.5 F300\n', 'G1 Z-4 F300\n', #asymmetric, slosh a few times to mix the resin
                     'G1 Z4 F300\n', 'G1 Z-4 F300\n'  ,
                     'G1 Z4 F300\n', 'G1 Z-4 F300\n',
                     'G1 Z4 F300\n', 'G1 Z-4 F300\n',
                     'G1 Z4 F300\n', 'G1 Z-4.4 F100\n', #doesn't go all the way back to 0 so the gcode move down to the correct location.
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

#initialize the data structure
for layer_data_element in layer_data:
    layer_data_element[stats] = {}
    layer_data_element[stats][stat_line_energy] = []
    layer_data_element[stats][stat_line_feedrate] = []
    layer_data_element[stats][stat_sublayer_indices] = []
    layer_data_element[processed_data] = []
    layer_data_element[extra_feedrate_data] = []
    layer_data_element[extra_move_data] = []


#figure out how many times each layer should be duplicated by
home_layer = 1
base_layer = base_layer_count
early_layer = early_layer_count
for layer_data_element in layer_data:
    for line in layer_data_element[raw_data]:
        if printy_helpers.isMove(line):
            home_layer = 0
    if home_layer == 1:
        layer_data_element[stats][stat_over_cure] = -1
    elif base_layer > 0:
        layer_data_element[stats][stat_over_cure] = base_layer_over_cure
        base_layer -= 1
    elif early_layer > 0:
        layer_data_element[stats][stat_over_cure] = early_layer_over_cure
        early_layer -= 1
    else:
        layer_data_element[stats][stat_over_cure] = normal_layer_over_cure


#tabulate total distances and energy
previous_xloc = 0
previous_yloc = 0
previous_eloc = 0
current_feed_rate = 0
current_xloc = 0
current_yloc = 0
current_eloc = 0
total_print_time = 0
for layer_data_element in layer_data:
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


        if not printy_helpers.isMove(line):
            layer_data_element[stats][stat_line_energy] += [draw_energy]
            layer_data_element[stats][stat_line_feedrate] += [current_feed_rate]
            continue

        if current_eloc > previous_eloc:
            segment_distance = ((current_xloc - previous_xloc)**2 + (current_yloc - previous_yloc)**2)**0.5
            print_length += segment_distance
            segment_time = segment_distance / current_feed_rate * 60.0
            print_time += segment_time
            #draw_energy += segment_time * laser_power * over_cure_factor
            segment_energy = resin_max_cure * laser_dot_diameter**2 * (1 - math.e**(-(segment_time*over_cure_factor)/laser_dot_diameter/resin_cure_tau))
            draw_energy += segment_energy

        previous_xloc = current_xloc
        previous_yloc = current_yloc
        previous_eloc = current_eloc
        layer_data_element[stats][stat_line_energy] += [draw_energy]
        layer_data_element[stats][stat_line_feedrate] += [current_feed_rate]

    layer_data_element[stats][stat_time]=print_time
    total_print_time += print_time * over_cure_factor
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

for layer in layer_data:
    print("sulayers: %d\tlayer energy: %f\n" %(len(layer[processed_data]), layer[stats][stat_energy]))
print("total print time (excluding extra lifts): %f\n" %total_print_time)
#with open('out.txt', 'w') as f:
#    for layer in layer_data:
#        f.write('%d\n' % len(layer[processed_data]))

#take all the processed data to the output
output_data = []

home_layer = 1
for layer in layer_data:
    #just copy and paste until we find real printing layers
    if layer[stats][stat_over_cure] == -1:
        output_data += layer[processed_data]

    #for the reset of the layers, repeat controled by stat_over_cure
    else:
        if home_layer == 1:
            home_layer = 0
            output_data += [initial_lift_code]
        output_data += printy_helpers.repeatLayerData(layer, sublayer_lift_code)

        #insert extra lift between layers
        #if the energy is low, such as a vase print, don't add a lift between layers
        if layer[stats][stat_energy] > min_energy_threshold:
            if layer[stats][stat_energy] < fast_retract_energy_threshold:
                output_data += [layer_lift_code_fast]
            else:
                output_data += [layer_lift_code]
        #print(layer[raw_data])

#output the processed gcode file
with open(out_file_location, 'w') as f:
    for layer in output_data:
        for line in layer:
            f.write(line)
