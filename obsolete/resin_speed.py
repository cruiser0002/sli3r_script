#!/usr/bin/python

import sys
import re



z_lift_feed_rate = 300
xy_feed_rate = 12000
move_feed_rate = 12000
extra_lift_code = ['G91 ; relative position\n',
                   'G1 Z5 F%d\n' %(z_lift_feed_rate),
                   'G1 Z-5\n',
                   'G90 ; absolute position\n']


#print ('Number of arguments:', len(sys.argv), 'arguments.')
#print ('Argument List:', str(sys.argv))

if len(sys.argv) < 2 or len(sys.argv) > 3:
    print ('usage: python sli3r_script.py filename or pythong sli3r_script.py infile outfile')
    exit(1)

in_file_location = sys.argv[1]
out_file_location = in_file_location
if len(sys.argv) == 3:
    out_file_location = sys.argv[2]

#each element is one z layer worth of data
layer_data = []
layer_num = 0


def isLayerChange(line):
    match = re.match(r'^[g][01].+[z].+', line, re.I)
    if match:
        return 1
    return 0


#stuff file data into layer_data
with open(in_file_location, 'r') as f:
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


new_data = []


for layer in layer_data:
    new_layer = []
    for line in layer:
        z_match = re.match(r'^[g][01].+([z]\d+\.?\d*)', line, re.I)
        f_match = re.match(r'^[g][01].+([f]\d+\.?\d*)', line, re.I)
        e_match = re.match(r'^[g][01].+([e]\d+\.?\d*)', line, re.I)
        g_match = re.match(r'^[g][01].*', line, re.I)

        if z_match:
            if f_match:
                #z with feedrate get repaced
                line = line.replace(f_match.group(1), 'F%d' %(z_lift_feed_rate))
            else:
                #independent z movement get a feedrate line inserted before
                new_layer += ['G0 F%d\n' %(z_lift_feed_rate)]
        else:
            if f_match and not e_match:
                #moving to point
                line = line.replace(f_match.group(1), 'F%d' %(move_feed_rate))
            if f_match and e_match:
                #real printing
                line = line.replace(f_match.group(1), 'F%d' %(xy_feed_rate))


        new_layer += [line]


        #follow any z move with extra lift, simultaneous e move means vase print
        if z_match and not e_match:
            new_layer += extra_lift_code

    new_data += [new_layer]


with open(out_file_location, 'w') as f:
    for layer in new_data:
        for line in layer:
            f.write(line)