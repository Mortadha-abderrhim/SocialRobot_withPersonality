
import torch
import wave
import librosa
import pyaudio
import numpy as np
SAMPLING_RATE = 16000



class Audio_processor():
    def __init__(self):
        self.model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                            model='silero_vad',
                            force_reload=True,
                            onnx=False)
        (get_speech_timestamps,
        save_audio,
        read_audio,
        VADIterator,
        collect_chunks) = utils
        self.vad_iterator = VADIterator(self.model, sampling_rate=SAMPLING_RATE)
        muted_windows = 0
        print("ready")


    def save_audio(self,audio_samples,path):
        wf = wave.open(path, 'wb')
        wf.setnchannels(2)
        wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
        wf.setframerate(8000)
        wf.writeframes(b''.join(audio_samples))
        wf.close()

    def speech_probability(self,audio_frame: bytes):
        buffer = np.frombuffer(audio_frame, dtype=np.int16).astype(np.float32) / 32767.0
        speech_prob = []
        wav = buffer
        speech_probs = []
        window_size_samples = 512 if SAMPLING_RATE == 16000 else 256
        for i in range(0, len(wav), window_size_samples):
            chunk = wav[i: i+ window_size_samples]
            if len(chunk) < window_size_samples:
                break
            speech_prob = self.model(torch.from_numpy(chunk), SAMPLING_RATE).item()
            speech_probs.append(speech_prob)
        self.vad_iterator.reset_states()
        if len(speech_probs) == 0:
            return 0.0
        return np.mean(speech_probs)