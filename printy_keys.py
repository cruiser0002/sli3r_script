

#raw_data contains a list whose elements represent a line of G-code

#statistics about each layer in a list of dictionaries
#stats contains a dictionary where
#stat_length is printing length in mm
#stat_time is total time in seconds
#stat_energy in joules
#stat_over_cure is the number of times this layer is repeated
#stat_line_energy is a list of the energy of each line of G-code
#stat_line_feedrate is a list of the feedrate of each line of G-code

#stat_sublayer_indices is a list whose elements are the indices of lines from raw data the sublayer splits happened at
#processed_data is a list whose elements are sublayers of a layer
#each sublayer is a list whose elements are lines of G-code

#extra_data are G-code for when we insert extra lifts
#extra_data is a list where each element is a list of G-code to add for each subslice
#should be an extra line of feedrate followed by an extra move line back to the start
#the move should have the feedrate stripped out so to not be an extruding move

#The naive implementation is to insert extra lift codes whenever the accumulated energy looks too high.
#The best implementation is to rearrange the gocdes so print chunks are grouped together for the most efficient lift while maintaining boundaries

raw_data = 'raw_data'

stats = 'layer_stats'
stat_length = 'stat_length' #in mm
stat_time = 'stat_time' #in seconds
stat_energy = 'stat_energy' #in joules
stat_over_cure = 'stat_over_cure'
stat_line_energy = 'stat_line_energy'
stat_line_feedrate = 'stat_line_feedrate'

stat_sublayer_indices = 'stat_sublayer_indices'
processed_data = 'processed_data'

extra_feedrate_data = 'extra_feedrate_data'
extra_move_data = 'extra_move_data'