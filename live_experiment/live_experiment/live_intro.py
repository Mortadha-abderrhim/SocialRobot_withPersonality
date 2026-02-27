#!/usr/bin/env python3

""" 
@Author: Zeyu Pang, Daniel Tozadore
@Date: 05.01.2024
@Description : Live experiment Class
	Facilitate interaction with users during experiments, and save critical data in the live-stream mode
"""


import rclpy
from rclpy.node import Node
from std_msgs.msg import String,Bool
import sys
import tkinter as tk
import pandas as pd
import json
from datetime import datetime

# Config colors of printing 
GREEN = "\033[0;32m"
BLUE="\033[0;94m"
RESET="\033[0m"

INTRO ="""Hello, I'm your tutor, and today we'll be discussing how changes to the environment can pose dangers to living things, especially from the point of view of food chains. Can you tell me your name? What do you know about this topic? I am listening."""
class Live_experiment(Node):
    def __init__(self):
        super().__init__("live_experiment")
        # Basic preparation
        self.fps = self.declare_parameter("/image/fps", 30).value
        self.record_config =   self.create_publisher(String,'/robot/record/config',rclpy.qos.qos_profile_parameters)
        self.talkSpeech =   self.create_publisher(String,'/qt_robot/behavior/talkText',rclpy.qos.qos_profile_parameters)
        self.record =   self.create_publisher(Bool,'/request/record',rclpy.qos.qos_profile_parameters)
        self.create_subscription(String,"/send/round",self.current_round,rclpy.qos.qos_profile_parameters)
        self.round = 0
        self.stat_record = self.create_publisher(Bool,"/request/save_stats",rclpy.qos.qos_profile_parameters)
        self.create_subscription(Bool,"/done_speaking",  self.speaking_done,rclpy.qos.qos_profile_parameters)    
        self.can_start = True
        self.total_time = 15 * 60
        self.done_speaking = False

    def speaking_done(self,msg):
        self.done_speaking = msg.data



    def create_msg(self,msg,final = "0;"):
        self.talkSpeech.publish(String(data=final + msg))


    def current_round(self,msg):
        self.round = int(msg.data)
        self.can_start = True
    # The main call function
    def __call__(self):
        rate = self.create_rate(self.fps)
        self.record_config.publish(String(data= json.dumps({"VAD":True})))
        self.create_msg(INTRO,"1speakingAct7;")
        experiment_start = datetime.now()
        while rclpy.ok():  
            if self.can_start and (datetime.now()-experiment_start).total_seconds()<self.total_time and self.done_speaking:
                self.stat_record.publish(Bool(data=True))
                self.can_start = False
                self.done_speaking = False
                self.record.publish(Bool(data=True))
            elif (datetime.now()-experiment_start).total_seconds()>=self.total_time:
                self.stat_record.publish(Bool(data=True))
            rclpy.spin_once(self)




def main(args=None):
    rclpy.init(args=sys.argv)
    live_experiment=Live_experiment()       # __init__

    try:
        live_experiment()                   # __call__
    except SystemExit:
        pass
    live_experiment.destroy_node()
    rclpy.shutdown()

# The main running
if __name__=='__main__':
    main()



