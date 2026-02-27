import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/mortadha/ros2_ws/src/live_experiment/install/live_experiment'
