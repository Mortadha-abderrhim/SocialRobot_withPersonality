#!/usr/bin/env python3
import torch
import transformers
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig,TextIteratorStreamer
from peft import PeftModel,PeftConfig
from threading import Thread
import rclpy
from rclpy.node import Node
from std_msgs.msg import String,Bool
import gc
import time
import random
from tutorial_interfaces.srv import TalkText

class Phi(Node):
    
    def __init__(self):
        super().__init__("phi")
        self.bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.bfloat16,
                )
        self.conv = "<|system|>: You are a helpful educational tutor. You teach the users about the concepts they are asking about. Your answers should be precise and enthusiastic. You can ask the student questions at the end of the answer to make sure he fully understands the concept. <|end|>\n"
        self.talkSpeech =   self.create_publisher(String,'/qt_robot/behavior/talkText',rclpy.qos.qos_profile_parameters)
        self.past_model = "-1"
        self.pub_LLM_last=self.create_publisher(String,"/video_builder/LLM_last",rclpy.qos.qos_profile_parameters)
        self.LLM_ready=self.create_publisher(Bool,"/video_builder/LLM_ready",rclpy.qos.qos_profile_parameters)
        self.pub_LLM_first=self.create_publisher(String,"/video_builder/LLM_first",rclpy.qos.qos_profile_parameters)
        self.fillers = [
            "That's a great point! I need to think about it for a bit.",
            "What an intriguing point! Let me ponder it for a moment.",
            "This point is so interesting! I have to mull it over.",
            "That's a fascinating point! Give me a second to consider it.",
            "Wow, what a compelling point! I need some time to think it through.",
            "This is such an exciting point! Let me reflect on it.",
            "This is so intriguing! Let me give it some serious thought.",
            "This is such a curious point! I need to give it some thought.",
            'This is an interesting point! Let me think about it'
        ]
        self.pub_LLM_done = self.create_publisher( Bool,"/video_builder/LLM_done",rclpy.qos.qos_profile_parameters)
        self.ready = False
        self.speaking_acts = ['speakingAct1', 'speakingAct10', 'speakingAct11', 'speakingAct12', 'speakingAct13', 'speakingAct14', 'speakingAct15', 'speakingAct16', 'speakingAct17', 'speakingAct2', 'speakingAct3', 'speakingAct4', 'speakingAct5', 'speakingAct6', 'speakingAct7', 'speakingAct8', 'speakingAct9']
    def new_conv(self,model_id):
        self.ready = False
        self.LLM_ready.publish(Bool(data=self.ready))
        if model_id in ["0","1"]:                
            if self.past_model not in ["0","1"]:
                self.model = None
                torch.cuda.empty_cache()
                gc.collect()
                model_name = "/home/mortadha/Desktop/Phi-3-mini-128k-instruct"
                adapters = "/home/mortadha/Desktop/SemProj/FinetunedModels/code/checkpoint-6414"
                
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name, quantization_config=self.bnb_config, device_map="cuda:0",trust_remote_code=True
                )
                peft_config = PeftConfig.from_pretrained(adapters)
                self.model.add_adapter(peft_config)
            else:
                time.sleep(10)
            if model_id == "0":
                self.model.disable_adapters()
            else:
                self.model.enable_adapters()
        else:
            self.model = None
            torch.cuda.empty_cache()
            gc.collect()
            model_name = "/home/mortadha/Desktop/stablelm-zephyr-3b"
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name, quantization_config=self.bnb_config, device_map="cuda:0",trust_remote_code=True
            )
        self.past_model = model_id
        self.round = []

        self.conv = "<|system|>: You are a helpful educational tutor. You teach the student about the concept he is asking about. Your answers should be precise, concise and enthusiastic. The answer should be short and to the point. You should ask the student some question at the end of the answer to make sure he fully understands the concept and deepen the conversation on the concept. <|end|>\n"
        self.ready = True
        self.LLM_ready.publish(Bool(data=self.ready))

    def create_msg(self,msg,final = "0;"):
        
        self.talkSpeech.publish(String(data=final + msg))

    def compute(self,filename,inp):

        """sentence = random.choice(self.fillers)
        print(sentence)
        self.talkSpeech(sentence)"""
        torch.cuda.empty_cache()
        gc.collect()
        self.conv += "<|user|>:" + inp.lower() +  "<|end|>\n<|assistant|>:"
        model_inputs = self.tokenizer([self.conv], return_tensors="pt").to("cuda")
        streamer = TextIteratorStreamer(self.tokenizer,skip_prompt=True)
        thread = Thread(target= self.model.generate, kwargs=dict(model_inputs,
                    streamer=streamer,
                    max_length = 20000,
                    do_sample = True,
                    temperature = 0.6,
                                ))
        thread.start()
        generated_text = ""
        this_round = ""
        for new_text in streamer:
            if generated_text == "":
                t_start= time.time()
                msg_LLM_first=String()
                msg_LLM_first.data=str(t_start)
                self.pub_LLM_first.publish(msg_LLM_first)
            generated_text += new_text
            if "." in new_text or "?" in new_text or "!" in new_text and len(generated_text.split())>2:
                self.conv += generated_text
                this_round += generated_text
                behavior = random.choice(self.speaking_acts)
                resp = self.create_msg(generated_text.replace("<|endoftext|>","").replace("<|end|>",""),"0"+behavior+";")
                generated_text = ""
        self.conv = self.conv.replace("<|endoftext|>","<|end|>")
        this_round = this_round.replace("<|endoftext|>","<|end|>")
        self.round.append(this_round)
        t_end= time.time()
        msg_LLM_last=String()
        msg_LLM_last.data=str(t_end)
        self.pub_LLM_last.publish(msg_LLM_last)
        self.pub_LLM_done.publish(Bool(data=True))
        return self.conv