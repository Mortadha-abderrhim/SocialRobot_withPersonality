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
        while True:
            res = yield session.call("rom.optional.behavior.play",name="BlocklyRobotDance")
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
    realm="rie.675bdc9101e236295c517099",
)

wamp.on_join(main)

if __name__ == "__main__":
    run([wamp])



