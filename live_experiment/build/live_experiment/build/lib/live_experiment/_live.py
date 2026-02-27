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
from .robot import *
import time

# Config colors of printing 
GREEN = "\033[0;32m"
BLUE="\033[0;94m"
RESET="\033[0m"


class Live_experiment(Node):
    def __init__(self):
        super().__init__("live_experiment")
        # Basic preparation
        self.fps = self.declare_parameter("/image/fps", 30).value
        self.init=True
        self.round=0
        self.username=''
        self.folder_path='/home/mortadha/ros2_ws/src/live_experiment/data'      # to be re-defined after moving !!!
        self.survey = False
        self.done = False
        # Initial conditions
        self.state = ""
        self.create_subscription(String,"/state_manager/state",  self.setState,rclpy.qos.qos_profile_parameters)
        self.Idle_init=True
        self.Record_init=True
        self.Inference_init=True
        self.LLM_init=True
        self.LLM_done=False
        self.create_subscription(Bool,"/video_builder/LLM_done",  self.is_LLM_done,rclpy.qos.qos_profile_parameters)

        # Get 4 time points
        self.AVSR_start_time=0
        self.AVSR_end_time=0
        self.LLM_first_time=0
        self.LLM_last_time=0
        self.create_subscription(String,"/video_builder/AVSR_start",  self.get_AVSR_start_time,rclpy.qos.qos_profile_parameters)
        self.create_subscription(String,"/video_builder/AVSR_end",  self.get_AVSR_end_time,rclpy.qos.qos_profile_parameters)
        self.create_subscription(String,"/video_builder/LLM_first",  self.get_LLM_first_time,rclpy.qos.qos_profile_parameters)    
        self.create_subscription(String,"/video_builder/LLM_last",  self.get_LLM_last_time,rclpy.qos.qos_profile_parameters)
        self.create_subscription(Bool,"/done_speaking",  self.speaking_done,rclpy.qos.qos_profile_parameters)    
        self.pub_recording_request = self.create_publisher(Bool,"/visual_module/recording_request",rclpy.qos.qos_profile_parameters)
        # Get 2 results
        self.AVSR_result=''
        self.LLM_result=''
        self.create_subscription(String,"/video_builder/result",  self.get_AVSR_result,rclpy.qos.qos_profile_parameters)
        self.create_subscription(String,"/video_builder/LLM",  self.get_LLM_result,rclpy.qos.qos_profile_parameters)
        self.create_subscription(String,"/video_builder/LLM_words",  self.print_LLM_words,rclpy.qos.qos_profile_parameters)
        self.create_subscription(Bool,"/video_builder/LLM_ready",  self.getLLMState,rclpy.qos.qos_profile_parameters)
        self.create_subscription(Bool,"/done_speaking",  self.speaking_done,rclpy.qos.qos_profile_parameters)
        # Publisher to state_manager
        self.pub_record_done =  self.create_publisher(Bool,"/video_builder/record_done",rclpy.qos.qos_profile_parameters)
        self.talkSpeech =   self.create_publisher(String,'/qt_robot/behavior/talkText',rclpy.qos.qos_profile_parameters)
        self.model_pub =  self.create_publisher(String,'/model/choice',rclpy.qos.qos_profile_parameters)
        self.LLM_ready = False
        self.done_speaking = False
        self.model_list = [0,1,2]
        self.get_model()
        self.survey = False

    def speaking_done(self,msg):
        self.done_speaking = msg.data
    # Other tool functions    
    def getLLMState(self,msg):
        self.LLM_ready = msg.data

    def setState(self, msg):
        self.state = msg.data
    
    def is_LLM_done(self,msg):
        self.LLM_done=msg.data
    
    def get_AVSR_start_time(self,msg):
        self.AVSR_start_time=float(msg.data)

    def get_AVSR_end_time(self,msg):
        self.AVSR_end_time=float(msg.data)

    def get_LLM_first_time(self,msg):
        self.LLM_first_time=float(msg.data)
    
    def get_LLM_last_time(self,msg):
        self.LLM_last_time=float(msg.data)

    def get_AVSR_result(self,msg):
        self.AVSR_result=msg.data
        sys.stdout.write(BLUE)
        print('{}:'.format(self.username),end=' ')
        print(msg.data)
        sys.stdout.write(RESET)
    
    def get_LLM_result(self,msg):
        self.LLM_result=msg.data

    def print_LLM_words(self,msg):
        sys.stdout.write(GREEN)
        print(msg.data, end=" ", flush=True)
        sys.stdout.write(RESET)
    
    def get_model(self):
        self.model_id = random.choice(self.model_list)
        return str(self.model_list.remove(self.model_id))
    

    def conduct_survey(self,name):
        # Crea2te the main window
        print("started")
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        # Collect responses using dialogs
        comments = [name]
        comments.append(simpledialog.askinteger("Input", "It was easy to interact with the robot(1 Completely Disagree to 5 Compltely agree)", parent=root, minvalue=1, maxvalue=5))
        comments.append(simpledialog.askinteger("Input", "I would like to use the robot to learn about new concepts(1 Completely Disagree to 5 Compltely agree)", parent=root, minvalue=1, maxvalue=5))
        comments.append(simpledialog.askinteger("Input", "I would recommend interacting with the robot to others (especially children)(1 Completely Disagree to 5 Compltely agree)", parent=root, minvalue=1, maxvalue=5))
        comments.append(simpledialog.askinteger("Input", "The robot perfectly understood what I was saying ( in terms of transcription)(1 Completely Disagree to 5 Compltely agree)", parent=root, minvalue=1, maxvalue=5))
        comments.append(simpledialog.askinteger("Input", "The robot stopped recording at the perfect moment.(1 Completely Disagree to 5 Compltely agree)", parent=root, minvalue=1, maxvalue=5))
        comments.append(simpledialog.askstring("Input", "What did you like most about the interaction with the robot?", parent=root))
        comments.append(simpledialog.askstring("Input", "What did you like least about the interaction with the robot?", parent=root))
        comments.append(simpledialog.askstring("Input", "What are the features you think should be added to the robot? ", parent=root))

        # Ask a multiple-choice question

        # Save responses to a file
        with open("/home/mortadha/ros2_ws/src/live_experiment/data/survey_results.txt", "a") as file:
            file.write(f"{comments}\n")

        # Thank you message
        root.destroy()

    def conduct_survey_topic(self, name, model):
        # Create the main window
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        satisfaction = [name,model]
        # Ask a multiple-choice question
        satisfaction.append(simpledialog.askinteger("Input", "The answers provided by the robot are relevant to my questions (1 Completely Disagree to 5 Compltely agree)", parent=root, minvalue=1, maxvalue=5))
        satisfaction.append(simpledialog.askinteger("Input", "The answers provided by the robot are coherent (1 Completely Disagree to 5 Compltely agree)", parent=root, minvalue=1, maxvalue=5))
        satisfaction.append(simpledialog.askinteger("Input", "The answers provided by the robot seem accurate (1 Completely Disagree to 5 Compltely agree)", parent=root, minvalue=1, maxvalue=5))
        satisfaction.append(simpledialog.askinteger("Input", "The discussion with the robot was engaging (1 Completely Disagree to 5 Compltely agree)", parent=root, minvalue=1, maxvalue=5))
        satisfaction.append(simpledialog.askinteger("Input", "The response time was acceptable and did not break the flow of the conversation.(1 Completely Disagree to 5 Compltely agree)", parent=root, minvalue=1, maxvalue=5))
        # Save responses to a file
        
        df = pd.read_csv("/home/mortadha/ros2_ws/src/live_experiment/data/survey.csv")
        df.loc[df.shape[0]+1] = satisfaction
        df.to_csv("/home/mortadha/ros2_ws/src/live_experiment/data/survey.csv",index=False)
        # Thank you message
        if self.round != 9:
            messagebox.showinfo("Please Wait for the robot's signal to start the new conversation", "The robot is getting ready for next round! Wait for the robot's signal",parent = root)
        root.destroy()

    def create_msg(self,msg,final = "0;"):
        
        self.talkSpeech.publish(String(data=final + msg))

    # The main call function
    def __call__(self):
        rate = self.create_rate(self.fps)
        
        while rclpy.ok():

            self.model_pub.publish(String(data=str(self.model_id)))
            
                 # Initialise experiment 
            if self.init==True:
                print('\n')
                print('Hello, my dear friend! Welcome to our experiment!')
                resp = self.create_msg('Hello, my dear friend! Welcome to our experiment! Please enter your name',"0BlocklyWaveRightArm;")
                
                self.username=input('Please enter your name (could use a nickname if you want):')
                print('Hi! Dear {}~'.format(self.username))
                resp = self.create_msg('Hi! Dear {}'.format(self.username),"1BlocklyInviteRight;")
                
                self.init=False
            # Interaction during different states
            if self.done:
                print("I should be here at the end")
                if self.done_speaking:
                    print("I should be here at the end after stops speaking")
                    self.conduct_survey_topic(self.username, str(self.model_id))
                    resp = self.create_msg('Experiment is over! Let us evaluate it!')
                    self.conduct_survey(self.username)
                    print('\n')
                    print('Experiment is over!')
                    print('Thank you so much for your cooperation and patience! Have a nice day~')
                    resp = self.create_msg('Experiment is over! Thank you so much for your cooperation and patience! Have a nice day!')
                    raise SystemExit
            elif self.state == "Idle":
                if self.Idle_init==True:
                    
                    if self.round==0:
                        print("\r")
                        print('This is Round 0 for testing, please click on the camera-live-window, and wait fot the signal from the robot to start chatting!')
                        resp = self.create_msg('This is Round 0 for testing, please click on the camera live window! You can start speaking when Recording is indicated in the camera live window.',"1;")
                        
                        
                    elif self.round==1:
                        print('\n')
                        print('Now the experiment officially starts, we will do 3 conversations on three different topics. You choose the topic. For each topic, we would have 3 turns.')
                        resp = self.create_msg("Now the experiment officially starts, we will do 3 conversations on three different topics. You choose the topic. For each topic, we would have 3 rounds.")
                        
                        print('You should ask a question about a concept or a topic that you choose.')
                        resp = self.create_msg('You should ask a question about a concept or a topic that you choose! You can start speaking when Recording is indicated in the camera live window.',"1;")
                        
                    elif (self.round == 4 or self.round == 7):
                        self.get_model()
                        self.model_pub.publish(String(data=str(self.model_id)))
                        print("here1")
                        print("That was an interesting conversation, I hope you had as much fun as I did! Let us fill the following survey.")
                        resp = self.create_msg("That was an interesting conversation, I hope you had as much fun as I did! Let us fill the following survey.","1;")
                        self.survey = True

                        
                    else:
                        print('\n')
                        print('I am ready for another Round, press SPACE to start again!')
                        resp = self.create_msg("Let's further discuss this point! You can discuss my answer and ask for further clarifications! You can start speaking when Recording is indicated in the camera live window.","1;")
                        
                    self.Idle_init=False 
                    self.done_speaking = False 
                elif self.done_speaking and self.survey and (self.round == 4 or self.round == 7):
                    self.conduct_survey_topic(self.username, str(self.model_id))
                    print('\n')
                    print('You should ask a question about a concept or a topic that you choose!')
                    
                    resp = self.create_msg('You should ask a question about a new concept or topic that you choose! You can start speaking when Recording is indicated in the camera live window.',"1;")
                    self.survey = False
                    self.done_speaking = False
                    time.sleep(15)
                # automatically starts recording, comment it to start with space
                elif self.done_speaking:
                    self.pub_recording_request.publish(Bool(data=True))
            
            elif self.state == "Recording":
                if self.Record_init==True:
                    print('\r')
                    print('Round {} starts!'.format(self.round))
                    print('I am listening...')
                    self.Record_init=False

            elif self.state == "Transfering":
                if self.Inference_init== True:
                    print('I am understanding...')
                    resp = self.create_msg('I am understanding...',random.choice(["0Stand/Waiting/ScratchHead_1;","0face_035;"]))
                    
                    print('\r')
                    self.Inference_init=False
                
            
            elif self.state == "LLM":
                if self.LLM_init==True:
                    print('\r')
                    print('\r')
                    self.LLM_init=False
                
                if self.LLM_done==True:

                    if self.round!=0:
                        # Save the experiment data in a .csv file

                        ## difine the file path
                        file_name=self.username+'.csv'
                        file_path=os.path.join(self.folder_path,file_name)

                        ## calculate 3 needed time
                        AVSR_time=round(self.AVSR_end_time-self.AVSR_start_time,3)
                        thinking_time=round(self.LLM_first_time-self.AVSR_end_time,3)
                        talking_time=round(self.LLM_last_time-self.LLM_first_time,3)

                        ## create the data of current round
                        contents=[self.round, AVSR_time, thinking_time, talking_time, self.AVSR_result, self.LLM_result,self.model_id]
                    
                        ## write file
                        with open(file_path,'a') as file:
                            csv_writer=csv.writer(file)
                        
                            ### write head labels
                            if self.round==1:
                                labels=['Round','AVSR_time','Thinking_time','Talking_time','AVSR_result','LLM_response',"LLM_id"]
                                csv_writer.writerow(labels)
                        
                            ### write data of current round
                            csv_writer.writerow(contents)
                    

                    # End the experiment after 10 rounds
                    if self.round==10:
                        resp = self.create_msg("That was an interesting conversation, I hope you had as much fun as I did! Let us fill the following survey.","1;")
                        self.done = True
                        self.done_speaking = False
                        
                        
                        


                    # Update initial conidtions
                    if not self.Idle_init:
                        self.round+=1
                    self.Idle_init=True
                    self.Record_init=True
                    self.Inference_init=True
                    self.LLM_init=True
                    self.LLM_done=False
                    

                    # Update state to state_manager
                    self.pub_record_done.publish(Bool(data=True))
                                
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

