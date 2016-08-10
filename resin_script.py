#!/usr/bin/python

#  11:30:43 PM: <Slic3r> Can't exec "/Users/cruiser0002/Documents/resinprinter/sli3r_script/resin_script.py": Permission denied at /Applications/Repetier-Host Mac.app/Contents/Resources/Slic3r.app/Contents/Resources/lib/std/Slic3r/Print.pm line 472.

import sys
import re

repeat_layers = 3
repeat_times = 3

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


new_data = []
layer_num = 0

for layer in layer_data:
    if layer_num <= repeat_layers and layer_num > 0:
        new_data += [layer, extra_lift_code]*repeat_times
    else:
        new_data += [layer, extra_lift_code]
    layer_num += 1







with open(out_file_location, 'w') as f:
    for layer in new_data:
        for line in layer:
            f.write(line)
