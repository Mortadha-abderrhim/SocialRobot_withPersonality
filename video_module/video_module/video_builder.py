#!/usr/bin/env python3

""" 
@Author: David Roch, Daniel Tozadore
@Date: 01.05.2022
@Description : Video_builder Class
	Receive the data to then build the video.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int16MultiArray, String, UInt64
from sensor_msgs.msg import Image, CompressedImage

from cv_bridge import CvBridge
import whisperx
import cv2

import pyaudio
import wave

from moviepy.editor import ImageSequenceClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
import numpy as np

class Video_builder():
	def __init__(self, image_format):
		self.channels = 2
		self.sample_rate = 48000
		self.sample_format = "pyaudio.paInt16"
		self.chunk = 1024
		self.image_format = image_format

		self.bridge = CvBridge()
		self.model = whisperx.load_model("large-v2", "cuda", compute_type="float16")
		

		self.current_audio = []
		self.current_video = []
		self.current_landmarks = []
		

		

	def recordAudio(self, msg):
		#("Wselna")
		self.current_audio.append(msg.data)

	def recordImage(self, msg):
		if self.image_format == "raw_images":
			img = self.bridge.imgmsg_to_cv2(msg)
			img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
		elif self.image_format == "jpeg" or self.image_format == "png" or self.image_format == "landmarks":
			img = self.bridge.compressed_imgmsg_to_cv2(msg)
			img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
		else: raise NameError('The image_format ', self.image_format," is not recognised.")
		self.current_video.append(img)
		#(len(self.current_video))

	def recordLandmarks(self, msg):
		self.current_landmarks.append(np.array(msg.data).reshape(-1, 2))

	def buildVideo(self, fps, data_path):
		video_clip = None

		audio = []
		
		for a in self.current_audio:
			audio.append(a)
		
		dict = {"pyaudio.paInt8" : pyaudio.paInt8, "pyaudio.paInt16": pyaudio.paInt16, "pyaudio.paInt32": pyaudio.paInt32}
		# Save the recorded data as a WAV file
		wf = wave.open(data_path + "/audio.wav", 'wb')
		wf.setnchannels(2)
		wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
		wf.setframerate(44100)
		wf.writeframes(b''.join(audio))
		wf.close()
		whis = whisperx.load_audio(data_path + "/audio.wav")
		result = self.model.transcribe(whis, batch_size=16, language="en")
		result = " ".join([t["text"] for t in result["segments"]])
		if self.current_video:
			print("here")
			image_clip = ImageSequenceClip(self.current_video, fps=fps)
			if audio:
				audio_clip = AudioFileClip(data_path + "/audio.wav", fps=44100)
				audio_clip.nchannels = 2
				video_clip = image_clip.set_audio(audio_clip)
			else: video_clip = image_clip
			
		elif audio:
				audio_clip = AudioFileClip(data_path + "/audio.wav", fps=44100)
				audio_clip.nchannels = self.channels
				video_clip = audio_clip
		
		return video_clip,result
