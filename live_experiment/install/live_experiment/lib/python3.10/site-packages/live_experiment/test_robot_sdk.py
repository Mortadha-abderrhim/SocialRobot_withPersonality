from autobahn.twisted.component import Component, run
from twisted.internet.defer import inlineCallbacks
from autobahn.wamp.exception import ApplicationError
from autobahn.twisted.util import sleep
import wave
import pyaudio

@inlineCallbacks
def explore_category(session, category):
    try:
        print(f"Exploring category: {category}")
        procedures = yield session.call(f'wamp.registration.lookup', category)
        print(procedures)
        for proc in procedures:
            print(f"Procedure in {category}: {proc}")
    except ApplicationError as e:
        print(f"ApplicationError while exploring {category}: {e}")
    except Exception as e:
        print(f"Unexpected error while exploring {category}: {e}")


@inlineCallbacks
def main(session, details):
    samples = []
    def build_audio(frame):
        samples.append(frame["data"]["body.head"])
    try:
        """registrations = yield session.call('wamp.registration.list')
        print("Registrations: ", registrations)
        
        for registration_id in registrations['exact']:
            try:
                registration_details = yield session.call('wamp.registration.get', registration_id)
                if "info" in registration_details['uri']:
                    print("Registration details: ", registration_details)
            except Exception as e:
                print(f"Error fetching details for registration I {registration_id}: ", e)"""
        """
        yield session.call("rie.vision.face.find")
        yield session.call("rie.dialogue.say", text="Hello!")
        yield session.call("rie.vision.face.track")
        yield session.call("rom.optional.behavior.play", name="BlocklyStand")
        yield session.subscribe(build_audio, "rom.sensor.hearing.stream")
        yield session.call("rom.sensor.hearing.stream")
        yield sleep(3)
        yield session.call("rom.sensor.hearing.close")
		# Save the recorded data as a WAV file
        print(samples)
        wf = wave.open("audio.wav", 'wb')
        wf.setnchannels(2)
        wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
        wf.setframerate(8000)
        wf.writeframes(b''.join(samples))
        wf.close()
        """
        l = ["body.mouth"]
        for x in l:
            frames=[{"time": 1000, "data":  [0,255,0]},
                    {"time": 2000, "data":  [255,0,0]},
                    {"time": 3000, "data": [0,0,255]}]
            res = yield session.call("rom.actuator.light.write",frames=frames)
            print(res)
        res = yield session.call("rom.actuator.light.info")
        print(res)
        
    except ApplicationError as e:
        print(f"Error: {e}")

    session.leave()  # Close the connection with the robot

wamp = Component(
    transports=[{
        "url": "ws://wamp.robotsindeklas.nl",
        "serializers": ["msgpack"],
        "max_retries": 0
    }],
    realm="rie.67176d9c8d3e74c137eb082f",
)

wamp.on_join(main)

if __name__ == "__main__":
    run([wamp])


