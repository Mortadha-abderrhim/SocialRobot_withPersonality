#!/usr/bin/env python3

""" 
@Author: Zeyu Pang, Daniel Tozadore
@Date: 05.01.2024
@Description : Live experiment Class
	Facilitate interaction with users during experiments, and save critical data in the live-stream mode
"""


from typing import Any
import rclpy
from rclpy.node import Node
from std_msgs.msg import String,Bool
import os
import csv
import sys
import random
from tutorial_interfaces.srv import TalkText
import tkinter as tk
from tkinter import simpledialog, messagebox
import pandas as pd
import time
import streamlit as st
import json
# Config colors of printing 
GREEN = "\033[0;32m"
BLUE="\033[0;94m"
RESET="\033[0m"


class Live_experiment(Node):
    def __init__(self):
        super().__init__("live_experiment")
        # Basic preparation
        self.fps = self.declare_parameter("/image/fps", 30).value
        self.record_config =   self.create_publisher(String,'/robot/record/config',rclpy.qos.qos_profile_parameters)
        self.talkSpeech =   self.create_publisher(String,'/qt_robot/behavior/talkText',rclpy.qos.qos_profile_parameters)
        self.record =   self.create_publisher(Bool,'/request/record',rclpy.qos.qos_profile_parameters)
        self.create_subscription(String,"/done_speaking",self.callback,rclpy.qos.qos_profile_parameters)
        self.create_subscription(String,"/send/round",self.current_round,rclpy.qos.qos_profile_parameters)
        self.round = 0
        self.stat_record = self.create_publisher(Bool,"/request/save_stats",rclpy.qos.qos_profile_parameters)
    

    def callback(self,x):
        print(x)

    def create_msg(self,msg,final = "0;"):
        self.talkSpeech.publish(String(data=final + msg))

    def current_round(self,msg):
        self.round = int(msg.data)
        print(self.round)
    # The main call function
    def __call__(self):
        rate = self.create_rate(self.fps)
        self.record_config.publish(String(data= json.dumps({"VAD":True})))
        time.sleep(3)
        self.record.publish(Bool(data = True))
        while rclpy.ok():  
            if self.round == 1:
                self.stat_record.publish(Bool(data=True)) 
                break
            rclpy.spin_once(self)


left, middle, right = st.columns(3)
if left.button("Plain button", use_container_width=True):
    left.markdown("You clicked the plain button.")
if middle.button("Emoji button", icon="😃", use_container_width=True):
    middle.markdown("You clicked the emoji button.")
if right.button("Material button", icon=":material/mood:", use_container_width=True):
    right.markdown("You clicked the Material button.")

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

