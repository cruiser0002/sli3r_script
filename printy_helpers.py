

import re

def isLayerChange(line):
    match = re.match(r'^[g][01].+[z].+', line, re.I)
    if match:
        return 1
    return 0

def hasFeedRate(line):
    f_match = re.match(r'^[g][01].+[f](\d+\.?\d*)', line, re.I)
    if f_match:
        return 1
    return 0

def getFeedRate(line):
    f_match = re.match(r'^[g][01].+[f](\d+\.?\d*)', line, re.I)
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

def isMove(line):
    g_match = re.match(r'^[g][01].*', line, re.I)
    x = getXLoc(line)
    y = getYLoc(line)
    if not g_match or (x == -1 and y == -1):
        return 0
    return 1

def isG92(line):
    g92_match = re.match(r'^[g]92', line, re.I)
    if g92_match:
        return 1
    return 0

def insertExtraLift(layer):
    return 0