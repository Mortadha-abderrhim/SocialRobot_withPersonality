import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String
import sys
import torch
import transformers
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig,TextIteratorStreamer
from peft import PeftModel,PeftConfig
from threading import Thread
from tutorial_interfaces.srv import TalkText
import json
import gc
import random
from pysbd import Segmenter
import time


scaling = [
    "extremely {low}",
    "very {low}",
    "{low}",
    "a bit {low}",
    "neither {low} nor {high}",
    "a bit {high}",
    "{high}",
    "very {high}",
    "extremely {high}"
]

def get_adjectives(aspects,scale):
    relevant_adjectives = []
    with open("/home/mortadha/MasterThesis/Personality/adjectives.json","r") as f:
        adjectives = json.load(f)
    for aspect in aspects:
        for adj in adjectives:
            if adj["domain"] == aspect:
                relevant_adjectives.append(adj)
    scaled = [scaling[scale].format(high=x["high_marker"],low=x["low_marker"]) for x in relevant_adjectives]
    return "I am " + ", ".join(scaled) + "."

OUTPUT_MAX_LENGTH = 2000
TEMP = 0.8
SPEAKING_ACTS = ['speakingAct1', 'speakingAct10', 'speakingAct11', 'speakingAct12', 'speakingAct13', 'speakingAct14', 'speakingAct15', 'speakingAct16', 'speakingAct17', 'speakingAct2', 'speakingAct3', 'speakingAct4', 'speakingAct5', 'speakingAct6', 'speakingAct7', 'speakingAct8', 'speakingAct9']
MODEL_ANSWERING = "/home/mortadha/MasterThesis/Models/Conversation/Approach6/checkpoint-5187"
MODEL_REASONING = "/home/mortadha/MasterThesis/Models/Reasoning/Approach2/checkpoint-1344"
BASE_MODEL = "microsoft/Phi-3.5-mini-instruct"




INTRO_EXT = """Hello! I'm your tutor, Robo buddy, and today we're going to dive into the exciting world of the environment and how changes to it can affect living things, particularly through food chains. But before we jump in, can you tell me your name?"""

ANSWER_SYSTEM= f"""<|system|> You are a soft-spoken, empathetic tutor who supports students in learning concepts and solving problems independently. Your name is Robo buddy. You dislike giving direct answers and instead use guiding strategies to help students build their own understanding. For each interaction, you are provided with one or a combination of the following strategies based on the user's needs:
    Topic Opening: Introduce a new concept or shift the discussion to a new topic.
    Topic Development: Expand or elaborate on the current topic to deepen understanding.
    Topic Closure: Summarize or conclude a topic, ensuring the student has grasped the key points.
    Presentation: Clearly explain or demonstrate a specific skill or knowledge component.
    Eliciting: Ask targeted questions to draw out the student’s ideas, reasoning, or knowledge.
    Scaffolding: Provide graduated support to help the student progress toward a solution.
    Focus: Guide the student’s attention to a specific aspect of the topic or problem.
    Probing: Ask follow-up questions to encourage deeper thinking and exploration.
    Telling: Occasionally provide direct information or corrections, but only when absolutely necessary to clarify misunderstandings.
    Generic: Offer broad, open-ended guidance when the student needs general direction or engage in an off topic discussion.
    Explain a Concept: Provide a foundational explanation to help the student understand.
    Ask a Question: Pose questions that encourage critical thinking and problem-solving.
    Provide a Hint: Give subtle clues to nudge the student toward the solution.
    Provide a Strategy: Suggest an approach or method for solving the problem.
    Provide a Worked Example: Offer an example of how to solve a similar problem to illustrate the process.
    Provide a Minor Correction: Gently correct small errors to refine understanding.
    Provide a Similar Problem: Present a related or simpler problem to build skills incrementally.
    Simplify the Question: Break the problem into smaller, more manageable parts.
    Affirm the Correct Answer: Confirm when the student’s answer or reasoning is correct.
    Encourage the Student: Provide positive reinforcement to build their confidence.
You should provide an answer to the user based on the provided strategy. You should stick to the provided strategy as long as it is relevant to the context. Do not mention the strategy in the answer just use it to build the answer.
The answer should be helpful, coherent, accurate, and engaging. You are providing the tutoring session for a 10 year old student. The topic of the session is how environmental changes affect living things and their food chains, and how humans can actively implement measures to reduce these negative impacts.
Respond in a way that matches this personality description: {get_adjectives(["EXT"],8)}
"""
REASONING_SYSTEM = """<|system|> You are a soft-spoken, empathetic tutor who supports students in learning concepts and solving problems independently. You dislike giving direct answers and instead use guiding strategies to help students build their own understanding. For each interaction, select one or a combination of the following strategies based on the student’s needs:
    Topic Opening: Introduce a new concept or shift the discussion to a new topic.
    Topic Development: Expand or elaborate on the current topic to deepen understanding.
    Topic Closure: Summarize or conclude a topic, ensuring the student has grasped the key points.
    Presentation: Clearly explain or demonstrate a specific skill or knowledge component.
    Eliciting: Ask targeted questions to draw out the student’s ideas, reasoning, or knowledge.
    Scaffolding: Provide graduated support to help the student progress toward a solution.
    Focus: Guide the student’s attention to a specific aspect of the topic or problem.
    Probing: Ask follow-up questions to encourage deeper thinking and exploration.
    Telling: Occasionally provide direct information or corrections, but only when absolutely necessary to clarify misunderstandings.
    Generic: Offer broad, open-ended guidance when the student needs general direction or engage in an off topic discussion.
    Explain a Concept: Provide a foundational explanation to help the student understand.
    Ask a Question: Pose questions that encourage critical thinking and problem-solving.
    Provide a Hint: Give subtle clues to nudge the student toward the solution.
    Provide a Strategy: Suggest an approach or method for solving the problem.
    Provide a Worked Example: Offer an example of how to solve a similar problem to illustrate the process.
    Provide a Minor Correction: Gently correct small errors to refine understanding.
    Provide a Similar Problem: Present a related or simpler problem to build skills incrementally.
    Simplify the Question: Break the problem into smaller, more manageable parts.
    Affirm the Correct Answer: Confirm when the student’s answer or reasoning is correct.
    Encourage the Student: Provide positive reinforcement to build their confidence.
You should choose the strategy or combination of strategies and output it.<|end|>\n"""

class Llm_module(Node):
    def __init__(self):
        super().__init__("llm_module")
        self.fps = 30

        self.talkSpeech =   self.create_publisher(String,'/qt_robot/behavior/talkText',rclpy.qos.qos_profile_parameters)

        self.create_subscription(String,'/llm/config',self.llm_config,rclpy.qos.qos_profile_parameters)

        self.create_subscription(String,"/request/query",self.query,rclpy.qos.qos_profile_parameters)
        self.pub = self.create_publisher(String,"/LLM/query/done",rclpy.qos.qos_profile_parameters)

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=False,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL,
            quantization_config=bnb_config,
            output_hidden_states = True,
        )

        self.tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
        self.model= PeftModel.from_pretrained(model, MODEL_REASONING, adapter_name="strategy")
        self.model.load_adapter(MODEL_ANSWERING, adapter_name="answer")
        self.segmenter = Segmenter(language='en', clean=False)
        self.conv = [{"role": "assistant","content":INTRO_EXT}]
        self.streaming = False
        self.done_speaking = True
        
    def llm_config(self,x):
        config = json.loads(x.data)
        if "STREAMING" in config:
            self.streaming = config["STREAMING"]

    def query(self,data):
        torch.cuda.empty_cache()
        gc.collect()
        self.conv.append({"role": "user","content":data.data})
        inp = "\n".join([f"<|{x['role']}|>\n{x['content']}" for x in self.conv])
        inp_reasoning = REASONING_SYSTEM + inp + "<|end|>\n<|strategy|>"
        model_inputs = self.tokenizer([inp_reasoning], return_tensors="pt").to("cuda")
        self.model.set_adapter("strategy")
        outputs = self.model.generate(
            input_ids=model_inputs["input_ids"],
            max_new_tokens=100,
            temperature=0.5,
            do_sample=True,
        )
        print(inp_reasoning)
        generated_strategy = self.tokenizer.decode(outputs[0], skip_special_tokens=False).rsplit("<|strategy|>",1)[1]
        print(generated_strategy)
        print("="*20)
        input_answer = ANSWER_SYSTEM + inp + "<|strategy|>" + generated_strategy.strip() + "\n<|assistant|>"
        print(input_answer)
        self.model.set_adapter("answer")
        model_inputs = self.tokenizer([input_answer], return_tensors="pt").to("cuda")
        self.done_speaking = False
        if self.streaming:
            streamer = TextIteratorStreamer(self.tokenizer,skip_prompt=True)
            thread = Thread(target= self.model.generate, kwargs=dict(model_inputs,
                        streamer=streamer,
                        max_new_tokens = OUTPUT_MAX_LENGTH,
                        do_sample = True,
                        temperature = TEMP,
                                    ))
            thread.start()
            generated_text = ""
            all_text = ""
            for new_text in streamer:
                generated_text += new_text
                if "." in new_text or "?" in new_text or "!" in new_text and len(generated_text.split())>2:
                    behavior = random.choice(SPEAKING_ACTS)
                    resp = self.create_msg(generated_text.replace("<|endoftext|>","").replace("<|end|>",""),"0"+behavior+";")
                    all_text += generated_text
                    generated_text = ""
                    
            self.conv.append({"role":"assistant","content":all_text.replace("<|endoftext|>","<|end|>")})
        else:
            outputs = self.model.generate(
                input_ids=model_inputs['input_ids'],
                max_new_tokens=OUTPUT_MAX_LENGTH,
                temperature=TEMP,
                do_sample=True
            )
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=False).rsplit("<|assistant|>",1)[1]
            sents = self.segmenter.segment(generated_text.replace("<|endoftext|>","").replace("<|end|>",""))
            for sent in sents:
                behavior = random.choice(SPEAKING_ACTS)
                self.create_msg(sent,"0"+behavior+";")
            self.conv.append({"role":"assistant","content":generated_text.replace("<|endoftext|>","<|end|>")})

        behavior = random.choice(SPEAKING_ACTS)
        resp = self.create_msg("I am listening!","1"+behavior+";")
        self.pub.publish(String(data="\n".join([f"<|{x['role']}|>\n{x['content']}" for x in self.conv])))

        torch.cuda.empty_cache()
        gc.collect()

    def create_msg(self,msg,final = "0;"):
        self.talkSpeech.publish(String(data=final + msg))
        

    def __call__(self):
        self.create_rate(self.fps)
        while rclpy.ok():
            rclpy.spin_once(self)


def main(args=None):
    rclpy.init(args=sys.argv)

    llm_module = Llm_module()
    try:
        llm_module()
    except KeyboardInterrupt:
        pass
    rclpy.shutdown()
if __name__ == '__main__':
    main()