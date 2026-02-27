from autobahn.asyncio.component import Component, run
from autobahn.asyncio.util import sleep
import asyncio
import queue
from rclpy.node import Node
from std_msgs.msg import String,Bool
import random
import rclpy
from datetime import datetime
import json
from .audio_processing import Audio_processor

class Robot(Node):
    def __init__(self):
        super().__init__("alpha_mini")
        self.alive=True
        self.fps = 30
        self.messages = queue.Queue()
        self.speaking = True
        self.create_subscription(String,'/qt_robot/behavior/talkText',self.callback,rclpy.qos.qos_profile_parameters)
        self.create_subscription(String,'/robot/record/config',self.record_config,rclpy.qos.qos_profile_parameters)
        self.create_subscription(Bool,'/robot/record/fire',self.recording_callback,rclpy.qos.qos_profile_parameters)  
        self.done_speaking = self.create_publisher(Bool,"/done_speaking",rclpy.qos.qos_profile_parameters)
        self.done_recording = self.create_publisher(String,"/robot/record/done",rclpy.qos.qos_profile_parameters)
        self.just_spoke = datetime.now()
        self.audio_samples = []
        self.session = None
        self.recording_fired = False
        self.is_recording = False
        self.path = "audio.wav"
        self.VAD = False
        self.vad_model = Audio_processor()
        self.muted_windows = 0
        self.spoken = False


    def callback(self,data):
        self.enqueue(data.data)

    def enqueue(self,string):
        self.messages.put(string)
        self.speaking = False

    # Function to remove and return a string from the queue
    def dequeue(self):
        if not self.messages.empty():
            string = self.messages.get()
            print(string)                
            return string
        else:
            return None
    
    def speaking_callback(self,x):
        self.speaking = self.is_empty() and x=="1"
        print(x,self.speaking)

    def recording_callback(self,x):
        self.recording_fired = True
    
    def record_config(self,x):
        config = json.loads(x.data)
        if "PATH" in config:
            self.path = config["PATH"]
        if "VAD" in config:
            self.VAD = config["VAD"]


    async def start_recording(self):
        await self.session.call("rom.sensor.hearing.stream")
        self.spoken = False
        self.muted_windows = 0
    
    async def stop_recording(self):
        await self.session.call("rom.sensor.hearing.close")
        self.vad_model.save_audio(self.audio_samples,self.path)
        self.audio_samples = []
        self.done_recording.publish(String(data=self.path))

    def build_audio(self,frame):
        if self.is_recording:
            self.audio_samples.append(frame["data"]["body.head"])
            if self.VAD:
                prob = self.vad_model.speech_probability(frame["data"]["body.head"])
                print(prob)
                if  prob < 0.7:
                    self.muted_windows += 1
                else:
                    self.muted_windows = 0
                    self.spoken = True
                if self.muted_windows > 20 and self.spoken:
                    self.recording_fired = True
        
        
    def is_empty(self):
        return self.messages.empty()
    
    async def __call__(self,session):
        rate = self.create_rate(self.fps)
        self.session = session
        speaking_acts = ['speakingAct1', 'speakingAct10', 'speakingAct11', 'speakingAct12', 'speakingAct13', 'speakingAct14', 'speakingAct15', 'speakingAct16', 'speakingAct17', 'speakingAct2', 'speakingAct3', 'speakingAct4', 'speakingAct5', 'speakingAct6', 'speakingAct7', 'speakingAct8', 'speakingAct9']
        
        task = session.call("rie.dialogue.say", text="Hi! Nice to see you again! Today's secret word is inside. I,  N,  S,   I,   D,   E.")
        await task

        await session.call("rom.sensor.hearing.sensitivity",sensitivity=1.0)
        await session.subscribe(self.build_audio, "rom.sensor.hearing.stream")
        
        while rclpy.ok():
            await session.call("rom.sensor.hearing.sensitivity",sensitivity=1.0)
            if self.recording_fired:
                if not self.is_recording:
                    await self.start_recording()
                else:
                    await self.stop_recording()
                self.is_recording = not self.is_recording
                self.recording_fired = not self.recording_fired
            while not self.is_empty():
                self.speaking = self.is_empty()
                text = self.dequeue()
                starting_index = text.index(";")+1
                if starting_index>2:
                    task1 = session.call("rom.optional.behavior.play",name=text[1:starting_index-1])
                else:
                    task1 = None
                if starting_index!= len(text):
                    task = session.call("rie.dialogue.say", text=text[starting_index:])
                    task.add_done_callback(lambda x: self.speaking_callback(text[0]))
                else:
                    task = None

                if task1 and task:
                    await asyncio.gather(task1, task)
                elif task1:
                    await task1
                elif task:
                    await task
                self.just_spoke = datetime.now()
                self.done_speaking.publish(Bool(data=self.speaking))  
            if (datetime.now() - self.just_spoke).total_seconds()>15:
                task1 = session.call("rom.optional.behavior.play",name=random.choice(speaking_acts))
                await task1
                self.just_spoke = datetime.now()
            rclpy.spin_once(self)

async def mainFunc(session, details):
    try: 
        myrobot = Robot()
    except Exception as e:
        print(e)
        
    await myrobot(session)



    return

def main(args = None):
    rclpy.init(args=args)
    wamp = Component(
    transports=[{
            "url": "ws://wamp.robotsindeklas.nl",
            "serializers": ["msgpack"]
            }],
            realm="rie.675bdc9101e236295c517099",
    )
    wamp.on_join(mainFunc)
    run([wamp])
    

if __name__=='__main__':
    main()
