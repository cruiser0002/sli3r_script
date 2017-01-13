

import re

def isLayerChange(line):
    match = re.match(r'^[g][01].+[z].+', line, re.I)
    if match:
        return 1
    return 0

def insertExtraLift(layer):
    return 0