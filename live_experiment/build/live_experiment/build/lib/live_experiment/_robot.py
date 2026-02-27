from autobahn.asyncio.component import Component, run
from autobahn.asyncio.util import sleep
import asyncio
import queue
from rclpy.node import Node
from std_msgs.msg import String,Bool
import random
import rclpy
from datetime import datetime

class Robot(Node):
    def __init__(self):
        super().__init__("alpha_mini")
        self.alive=True
        self.fps = 30
        self.messages = queue.Queue()
        self.speaking = True
        self.create_subscription(String,'/qt_robot/behavior/talkText',self.callback,rclpy.qos.qos_profile_parameters)  
        self.done_speaking = self.create_publisher(Bool,"/done_speaking",rclpy.qos.qos_profile_parameters)
        self.just_spoke = datetime.now()
    def callback(self,data):
        self.enqueue(data.data)

    def enqueue(self,string):
        self.messages.put(string)
        self.speaking = False
        print(f'Enqueued: {string}')

    # Function to remove and return a string from the queue
    def dequeue(self):
        if not self.messages.empty():
            string = self.messages.get()                
            print(f'Dequeued: {string}')
            return string
        else:
            print('Queue is empty')
            return None
    
    def speaking_callback(self,x):
        self.speaking = self.is_empty() and x=="1"
        
        
    def is_empty(self):

        return self.messages.empty()
    async def __call__(self,session):
        rate = self.create_rate(self.fps)
        speaking_acts = ['speakingAct1', 'speakingAct10', 'speakingAct11', 'speakingAct12', 'speakingAct13', 'speakingAct14', 'speakingAct15', 'speakingAct16', 'speakingAct17', 'speakingAct2', 'speakingAct3', 'speakingAct4', 'speakingAct5', 'speakingAct6', 'speakingAct7', 'speakingAct8', 'speakingAct9']

        while rclpy.ok():
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
    
    # myrobot.talk("Hello, I am testing the class comunication here.", block=False)
    
    await myrobot(session)



    return

def main(args = None):
    rclpy.init(args=args)
    wamp = Component(
    transports=[{
            "url": "ws://wamp.robotsindeklas.nl",
            "serializers": ["msgpack"]
            }],
            realm="rie.67053ffd9d40636bb19da62d",
    )
    wamp.on_join(mainFunc)
    run([wamp])
    

if __name__=='__main__':
    main()
