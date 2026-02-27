#!/usr/bin/env python3

""" 
@Author: David Roch, Lucas Represa, Zeyu Pang, Daniel Tozadore
@Date: 05.01.2024
@Description : Video Class
	This is the main part of the Video module.
	First make sure to receive all data to build the video properly and then process it.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool
from std_msgs.msg import Int16MultiArray, String, Int64
from sensor_msgs.msg import Image, CompressedImage
from .video_builder import Video_builder
from .video_processing import Video_processing

import pickle
import os
import rospkg
import json
import shutil
import time
from .Phi import Phi
import sys
class Video(Node):
	def __init__(self):
		super().__init__("video_module")
		self.fps = 25
		self.image_format = self.declare_parameter("/image/image_format", "jpeg").value
		self.evaluation = self.declare_parameter("/evaluation/eval", False).value
		experiment = self.declare_parameter("/video/experiment", False).value
		self.LLM_bool = self.declare_parameter("/robot/LLM", False).value
		config_file = "/home/mortadha/ros2_ws/VSR/configs/LRS3_AV_WER0.9.ini"

		# prepare where to save the video
		self.data_path = "/home/mortadha/ros2_ws/src/Video_module"
		self.data_path += "/data"
		if experiment:
			os.makedirs(self.data_path,exist_ok=True)
			totalDir = len([name for name in os.listdir(self.data_path)]) - 1
			self.data_path = self.data_path+"/"+str(totalDir)
		
			number_of_noise_lvl = self.declare_parameter("/video/number_of_noise_lvl", 4).value
			for i in range(number_of_noise_lvl):
				os.makedirs(self.data_path+"/noise"+str(i))
		else:
			self.data_path += "/current"
			if not os.path.exists(self.data_path):
				os.makedirs(self.data_path)
		
		# Video builder init
		self.Video_builder = Video_builder(self.image_format)
		
		# Video processing init
		if self.evaluation:
			self.filename = "/video"
			self.create_subscription(String,'/evaluator/video_path',  self.update_filename,rclpy.qos.qos_profile_parameters)
			self.Video_processing = Video_processing(config_file, self.data_path + "/video.mp4")
		else:
			self.create_subscription(String,"/state_manager/video_name",  self.update_filename,rclpy.qos.qos_profile_parameters)
			self.filename = "/video"
			print(".... " +config_file)
			print("**** " +self.data_path + self.filename)
			self.Video_processing = Video_processing(config_file, self.data_path + self.filename + ".mp4")

		if self.image_format == "landmarks":
			self.Video_processing.args.landmarks_filename = self.data_path + self.filename + ".pkl"

		# LLM init
		self.LLM = Phi()
		self.model_id = "-1"
		self.create_subscription(String,"/model/choice",self.update_model,rclpy.qos.qos_profile_parameters)
		self.state = ""
		self.create_subscription(String,"/state_manager/state",  self.setState,rclpy.qos.qos_profile_parameters)

		self.pub_ready = self.create_publisher(Bool,"/video_builder/ready",rclpy.qos.qos_profile_parameters)
		self.pub_video_build = self.create_publisher(Bool,"/video_builder/video_building_done",rclpy.qos.qos_profile_parameters)
		self.pub_res = self.create_publisher(String,"/video_builder/result",rclpy.qos.qos_profile_parameters)
		self.pub_LLM = self.create_publisher(String,"/video_builder/LLM",rclpy.qos.qos_profile_parameters)
		self.pub_LLM_done = self.create_publisher(Bool,"/video_builder/LLM_done",rclpy.qos.qos_profile_parameters)
		self.LLM_ready=self.create_publisher(Bool,"/video_builder/LLM_ready",rclpy.qos.qos_profile_parameters)
		self.create_subscription(Int16MultiArray,"/audio_module/audio", self.recordAudio,rclpy.qos.qos_profile_parameters)

		self.create_subscription(Image,"/visual_module/raw_image",  self.recordImage,rclpy.qos.qos_profile_parameters)
		self.create_subscription(CompressedImage,"/visual_module/raw_image/compressed",  self.recordImage,rclpy.qos.qos_profile_parameters)
		self.create_subscription(Int16MultiArray,"/visual_module/landmarks",  self.recordLandmarks,rclpy.qos.qos_profile_parameters)
		self.pub_nb_frame_received = self.create_publisher(Int64,"/video_builder/nb_frame_received",rclpy.qos.qos_profile_parameters)
		self.pub_nb_chunk_received = self.create_publisher(Int64,"/video_builder/nb_chunk_received",rclpy.qos.qos_profile_parameters)
		self.video_built = False
		self.inference_done = False		
		self.transcript = {}

	def recordAudio(self, msg):
		self.Video_builder.recordAudio(msg)
		#(len(self.Video_builder.current_audio))
		self.pub_nb_chunk_received.publish(Int64(data=len(self.Video_builder.current_audio)))

	def recordImage(self, msg):
		self.Video_builder.recordImage(msg)
		#(len(self.Video_builder.current_video))
		self.pub_nb_frame_received.publish(Int64(data=len(self.Video_builder.current_video)))

	def recordLandmarks(self, msg):
		self.Video_builder.recordLandmarks(msg)

	def setState(self, msg):
		self.state = msg.data

	def update_model(self, msg):
		if msg.data != self.model_id:
			self.model_id = msg.data
			self.LLM.new_conv(msg.data)

	def update_filename(self, msg):
		if msg.data:
			self.filename = msg.data
		
	def __call__(self):
		rate = self.create_rate(self.fps)
		
		while rclpy.ok():
			if self.state == "Idle" or self.state == "Evaluation_idle":
				self.Video_builder.current_audio = []
				self.Video_builder.current_video = []
				self.pub_ready.publish(Bool(data=True))
				self.LLM_ready.publish(Bool(data=self.LLM.ready))
				built = False
			else:
				self.pub_ready.publish(Bool(data=False))

			if self.state == "Video_building" and (self.Video_builder.current_video or self.Video_builder.current_audio):
				if not self.evaluation:
					if self.image_format == "landmarks":
						pickle.dump(self.Video_builder.current_landmarks, open(self.data_path + self.filename + ".pkl", 'wb'))

					"""
					Reducing the number of fps avoid floating precision error in the moviepy library which is calculating 
					the duration of the video based on the fps and the number of frames to then place 
					the frame[n] every duration/fps which sometime produce a list index out of bound.
					"""
					fps = self.fps
					
					print("?"*50)
					while not built:
						print("*"*20)
						clip, whisper_trans = self.Video_builder.buildVideo(fps, self.data_path)
						clip.write_videofile((self.data_path + self.filename + ".mp4").replace(" ", "_"),fps=self.fps)
						save_videos = True
						if save_videos:
							if not os.path.exists(self.data_path + '/save'):
								os.makedirs(self.data_path + '/save')
							shutil.copyfile((self.data_path + self.filename + ".mp4").replace(" ", "_"), (self.data_path + '/save' + self.filename + str(time.time()) + ".mp4").replace(" ", "_"))
						built = True
						self.transcript["whisper"] = whisper_trans
						"""except:
							if fps <= 1:
								rospy.loginfo("There was a float precision exceptions error in the building of the video.")
								break
							fps -= 1
							rospy.loginfo("There was a float precision exceptions error in the building of the video. Retrying with " + str(fps) + " fps.")
						"""
					
					self.Video_builder.current_audio = []
					self.Video_builder.current_video = []
					self.current_landmarks = []

				else: # To handle the case of built vLLM_done.mp4" in save data path
						source_path =  self.filename
						destination_path = self.data_path +  '/video.mp4'

						shutil.copy(source_path, destination_path)

						built = True

				self.pub_video_build.publish(Bool(data=True))
				self.video_built = True

			elif self.state == "Inference" and self.video_built:
				self.video_built = False
				res = ""
				
				try:
					res = self.Video_processing.compute()
				except AttributeError:
					print('The video procesing didnt work properly. Maybe it was not able to detect faces in the image.')
				except:
					print('The video procesing didnt work properly. Further investigation are required.')
				self.pub_res.publish(String(data=res))
				self.inference_done = True
				self.transcript["AVSR"] = res

				
			elif self.state == "LLM" and self.inference_done:
				with open((self.data_path + '/save' + self.filename + str(time.time()) + ".json").replace(" ", "_"),"w") as f:
					json.dump(self.transcript,f)
				self.transcript = {}
				self.inference_done = False
				corr = ""
				
				corr = self.LLM.compute(self.filename, res)

				
				self.pub_LLM.publish(String(data=corr))
				self.pub_LLM_done.publish(Bool(data=True))

			rclpy.spin_once(self)

def main(args=None):
	rclpy.init(args=sys.argv)

	video = Video()
	try:
		video()
	except KeyboardInterrupt:
		pass

if __name__ == '__main__':
	main()