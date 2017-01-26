

import re
from printy_keys import *

def isLayerChange(line):
    zloc = getZLoc(line)
    if zloc != -1 or isMCommand(line):
        return 1
    return 0


def hasFeedRate(line):
    f_match = re.match(r'^[g][01].+[f]([-]?\d+\.?\d*)', line, re.I)
    if f_match:
        return 1
    return 0

def getFeedRate(line):
    f_match = re.match(r'^[g][01].+[f]([-]?\d+\.?\d*)', line, re.I)
    if f_match:
        return float(f_match.group(1))
    return -1

def getXLoc(line):
    x_match = re.match(r'^[g][0-9]+.+[x]([-]?\d+\.?\d*)', line, re.I)
    if x_match:
        return float(x_match.group(1))
    return -1

def getYLoc(line):
    y_match = re.match(r'^[g][0-9]+.+[y]([-]?\d+\.?\d*)', line, re.I)
    if y_match:
        return float(y_match.group(1))
    return -1

def getZLoc(line):
    z_match = re.match(r'^[g][0-9]+.+[z]([-]?\d+\.?\d*)', line, re.I)
    if z_match:
        return float(z_match.group(1))
    return -1

def getELoc(line):
    e_match = re.match(r'^[g][0-9]+.+[e]([-]?\d+\.?\d*)', line, re.I)
    if e_match:
        return float(e_match.group(1))
    return -1

#returns the first move G-code line within a layer with the extrusion stripped
def stripELoc(layer):
    for line in layer:
        if isMove(line):
            e_match = re.match(r'^[g][01].+([e][-]?\d+\.?\d*)', line, re.I)
            if e_match:
                #strip any mention of e
                line = line.replace(e_match.group(1), '')
            return line
    return -1

def isMove(line):
    g_match = re.match(r'^[g][01].*', line, re.I)
    x = getXLoc(line)
    y = getYLoc(line)
    if not g_match or (x == -1 and y == -1):
        return 0
    return 1

def isG92(line): #this sets locations
    g92_match = re.match(r'^[g]92', line, re.I)
    if g92_match:
        return 1
    return 0

def isG28(line): #this homes all axes
    g28_match = re.match(r'^[g]28', line, re.I)
    if g28_match:
        return 1
    return 0

def isMCommand(line):
    m_match = re.match(r'^[m]\d+', line, re.I)
    if m_match:
        return 1
    return 0


def repeatLayerData(layer, sublayer_lift_code):
    output_data = []
    overcure = layer[stats][stat_over_cure]
    sublayerindex = 0
    if len(layer) == 0:
        return [[]]
    for sublayer in layer[processed_data][:-1]:

        if len(sublayer) == 0:
            continue

        #Insert extra move between each repeated sublayer
        for index in range(overcure-1):
            output_data += sublayer
            output_data += [layer[extra_move_data][sublayerindex]]
        output_data += sublayer

        #Insert extra lift code after each subslice finishes
        output_data += sublayer_lift_code
        #Insert a feedrate line so the speed is correct after the extra lift code
        output_data += layer[extra_feedrate_data][sublayerindex]
        sublayerindex += 1

    sublayer = layer[processed_data][-1]
    for index in range(overcure-1):
        output_data += sublayer
        output_data += [layer[extra_move_data][sublayerindex]]
    output_data += sublayer

    return output_data