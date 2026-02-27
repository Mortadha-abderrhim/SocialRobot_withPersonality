
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String
import sys
from datetime import datetime
import os
import shutil
import pandas as pd


DATA_FOLDER = "/home/mortadha/MasterThesis/ExperimentData"
class State_Manager(Node):
    def __init__(self):
        super().__init__("state_manager")
        self.directory = os.path.join(DATA_FOLDER,datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))
        os.makedirs(self.directory)
        self.state = "Idle"
        self.pub = self.create_publisher(String,'/state_manager/state',rclpy.qos.qos_profile_parameters)
        self.fps = self.declare_parameter("/image/fps", 30).value

        self.record =   self.create_publisher(Bool,'/robot/record/fire',rclpy.qos.qos_profile_parameters)
        self.create_subscription(Bool,'/request/record',self.start_recording,rclpy.qos.qos_profile_parameters)
        self.create_subscription(String,"/robot/record/done",self.recorded,rclpy.qos.qos_profile_parameters)

        self.transcribe = self.create_publisher(String,"/request/transcribe",rclpy.qos.qos_profile_parameters)
        self.create_subscription(String,"/audio/transcribe/done",self.transcribed,rclpy.qos.qos_profile_parameters)

        self.query = self.create_publisher(String,"/request/query",rclpy.qos.qos_profile_parameters)
        self.create_subscription(String,"/LLM/query/done",self.queried,rclpy.qos.qos_profile_parameters)

        self.create_subscription(Bool,"/request/save_stats",self.save_stats,rclpy.qos.qos_profile_parameters)

        self.rounds = self.create_publisher(String,"/send/round",rclpy.qos.qos_profile_parameters)
        self.interface = self.create_publisher(String,"/send/qa",rclpy.qos.qos_profile_parameters)
        self.statistics = []
        self.stat_saved = True
        self.round = 0
        self.recording_duration = 0
        self.transcription_duration = 0
        self.query_duration = 0

        self.transcription = ""
        self.response = ""

    def save_stats(self,data):
        columns = ["round","record_time","transcript_time","query_time","transcript","llm_response"]
        path = os.path.join(self.directory,"stats.csv")
        pd.DataFrame(self.statistics,columns=columns).to_csv(path)

    def queried(self,data):
        self.query_duration = datetime.now() - self.start_query_time
        self.state = "Idle"
        self.response = data.data
        self.pub.publish(String(data=self.state))
        print(self.state)


    def transcribed(self,data):
        self.start_query_time = datetime.now()
        self.state = "LLM"
        self.query.publish(data)
        self.transcription = data.data
        self.pub.publish(String(data=self.state))
        self.transcription_duration = self.start_query_time - self.start_transcription_time
        print(self.state)

    def recorded(self,data):
        self.start_transcription_time = datetime.now()
        self.state = "Transcribe"
        self.transcribe.publish(data)
        self.path = data.data
        self.pub.publish(String(data=self.state))
        self.recording_duration = self.start_transcription_time - self.start_recording_time
        print(self.state)

    def start_recording(self,data):
        if  self.stat_saved and self.state == "Idle":
            self.stat_saved = False
            self.record.publish(Bool(data=True))
            self.start_recording_time = datetime.now()
            self.state= "Record"
            self.pub.publish(String(data=self.state))
            print(self.state)
    

    
    def __call__(self):
        rate = self.create_rate(self.fps)
        while rclpy.ok():  
            if not self.stat_saved and self.state == "Idle":
                self.round = self.round + 1
                filename = str(self.round) + ".wav"
                shutil.move(self.path,os.path.join(self.directory,filename))
                self.statistics.append([self.round,self.recording_duration,self.transcription_duration,self.query_duration,self.transcription,self.response])
                self.stat_saved = True
                self.interface.publish(String(data=self.response))
                self.rounds.publish(String(data=str(self.round)))
            rclpy.spin_once(self)

                



def main(args=None):
    rclpy.init(args=sys.argv)

    state_manager = State_Manager()
    try:
        state_manager()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
    