import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String
import sys
import whisperx


class Audio_module(Node):
    def __init__(self):
        super().__init__("audio_module")
        self.fps = 30
        self.create_subscription(String,"/request/transcribe",self.transcribe,rclpy.qos.qos_profile_parameters)
        self.pub =  self.create_publisher(String,"/audio/transcribe/done",rclpy.qos.qos_profile_parameters)
        self.model = whisperx.load_model("large-v2", "cuda", compute_type="float16")
    
    def transcribe(self,data):
        audio = whisperx.load_audio(data.data)
        result = self.model.transcribe(audio, batch_size=16, language="en")
        result = " ".join([t["text"] for t in result["segments"]])
        self.pub.publish(String(data=result))

    def __call__(self):
        self.create_rate(self.fps)
        while rclpy.ok():
            rclpy.spin_once(self)


def main(args=None):
    rclpy.init(args=sys.argv)

    audio_module = Audio_module()
    try:
        audio_module()
    except KeyboardInterrupt:
        pass
    rclpy.shutdown()
if __name__ == '__main__':
    main()