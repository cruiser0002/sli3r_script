#!/usr/bin/python

import sys
import re

first_layer_threshold = 20 #config
first_layer_repeat = 1 #config

extra_lift_retraction_factor = 3.0 #config
extra_lift_code = ['G91 ; relative position\n', 'G1 Z5\n', 'G1 Z-5\n', 'G90 ; absolute position\n']

#print ('Number of arguments:', len(sys.argv), 'arguments.')
#print ('Argument List:', str(sys.argv))

if len(sys.argv) < 2 or len(sys.argv) > 3:
    print ('usage: python sli3r_script.py filename or pythong sli3r_script.py infile outfile')
    exit(1)

in_file_location = sys.argv[1]
out_file_location = in_file_location
if len(sys.argv) == 3:
    out_file_location = sys.argv[2]

layer_data = []
layer_num = 0


def isLayerChange(line):
    match = re.match(r'^[g][01].+[z].+', line, re.I)
    if match:
        return 1
    return 0


#stuff file data into layer_data
with open(in_file_location, 'r') as f:
    #data = f.read()
    #print ('file length:', len(data))
    one_layer = []
    for line in f:
        if isLayerChange(line):
            layer_num += 1
            layer_data += [one_layer]
            one_layer = []
        one_layer += [line]
    layer_data += [one_layer]

if len(layer_data) < 2:
    exit(1)



first_layer_sum_extrusion = 0

previous_extrusion_distance = 0
current_extrusion_distance = 0
previous_sum_distance = 0



new_data = []
new_layer = []
layer_index = 0
first_layer = []
feed_rate = 1
#new_data += [layer_data[0]]

while first_layer_sum_extrusion <= 0:
    first_layer = layer_data[layer_index]
    layer_index += 1
    new_layer = []
    for line in first_layer:
        new_layer += [line]
        match = re.match(r'^[g][01].+[f]([0-9]+[\.]?[0-9]*)', line, re.I)
        if match:
            feed_rate = float(match.group(1))
        match = re.match(r'^[g][01].+[e]([0-9]+[\.]?[0-9]*)', line, re.I)
        if match:
            current_extrusion_distance = float(match.group(1))
            delta = current_extrusion_distance - previous_extrusion_distance
            if delta >= 0:
                first_layer_sum_extrusion += delta / feed_rate
            else:
                first_layer_sum_extrusion += current_extrusion_distance / feed_rate

            previous_extrusion_distance = current_extrusion_distance
        if (current_extrusion_distance - previous_sum_distance) >= first_layer_threshold:
            #print("first layer insertion needed")
            new_layer += extra_lift_code
            previous_sum_distance = current_extrusion_distance

    if first_layer_sum_extrusion <= 0:
        new_data += [new_layer]
        #print(new_layer)
    else:
        new_layer += extra_lift_code
        new_data += [new_layer] * first_layer_repeat

    #print(new_data)
    #print("firstlayer sum")
    #print(first_layer_sum_extrusion)


extra_lift_threshold = first_layer_sum_extrusion / extra_lift_retraction_factor
#print(extra_lift_threshold)

feed_rate = 1

for layer in layer_data[layer_index:]:
    previous_extrusion_distance = 0
    current_extrusion_distance = 0
    sum_extrusion = 0
    previous_sum_distance = 0
    new_layer = []

    for line in layer:
        match = re.match(r'^[g][01].+[e]([0-9]+[\.]?[0-9]*)', line, re.I)
        if match:
            previous_extrusion_distance = float(match.group(1))
            #print(previous_extrusion_distance)
            break

    #print("first:" + str(previous_extrusion_distance))

    for line in layer:
        new_layer += [line]
        #find out if the feed rate changed
        match = re.match(r'^([g][01].+[f]([0-9]+[\.]?[0-9]*)', line, re.I)
        if match:
            feed_rate = float(match.group(1))
        #find out if the line contains extrusion
        match = re.match(r'^[g][01].+[e]([0-9]+[\.]?[0-9]*)', line, re.I)
        if match:
            current_extrusion_distance = float(match.group(1))
            delta = current_extrusion_distance - previous_extrusion_distance

            #print("prev:" + str(previous_extrusion_distance))
            #print("delta:" + str(delta))
            #print("current:" + str(current_extrusion_distance))

            previous_extrusion_distance = current_extrusion_distance
            if delta >= 0:
                sum_extrusion += delta / feed_rate
            else:
                sum_extrusion += current_extrusion_distance / feed_rate

            if (sum_extrusion - previous_sum_distance) >= extra_lift_threshold:
                #print("insertion needed")
                new_layer += extra_lift_code
                previous_sum_distance = sum_extrusion

    #print(sum_extrusion)
    #print("Extra lift for Z operation")
    new_layer += extra_lift_code
    new_data += [new_layer]



with open(out_file_location, 'w') as f:
    for layer in new_data:
        for line in layer:
            f.write(line)
