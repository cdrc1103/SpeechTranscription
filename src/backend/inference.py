import logging
import os
import queue
import time
from dataclasses import dataclass

import pydub
import streamlit as st
from azure.cognitiveservices.speech import (
    AudioConfig,
    PhraseListGrammar,
    SpeechConfig,
    SpeechRecognitionEventArgs,
    SpeechRecognizer,
)
from azure.cognitiveservices.speech.audio import (
    AudioStreamFormat,
    PushAudioInputStream,
)
from pydub import AudioSegment
from streamlit.delta_generator import DeltaGenerator
from streamlit_webrtc import WebRtcStreamerContext, WebRtcStreamerState
from streamlit_webrtc.receive import FrameT

from backend.settings import CHANNELS, SAMPLE_RATE, TIME_LIMIT
from constants import TRANSCRIPT_STATE, AppSettings
from frontend.settings import LANGUAGE_DICT


@dataclass
class TranscriptionResults:
    """Store transcription text mutable"""

    text: str
    change_flag: bool


def setup_inference_pipeline(
    frontend_status: DeltaGenerator,
    frontend_transcription: DeltaGenerator,
    inbound_stream: WebRtcStreamerContext,
    app_config: AppSettings,
) -> None:
    """
    Connect to azure cloud instance and transcribe recorded audio.
    """

    speech_recognizer, outbound_stream = configure_speech_recognizer(
        app_config
    )
    init_speech_recognition(
        speech_recognizer,
        frontend_status,
        outbound_stream,
        inbound_stream,
        frontend_transcription,
    )


def configure_speech_recognizer(
    app_config: AppSettings,
) -> tuple[SpeechRecognizer, PushAudioInputStream]:
    """Create the SpeechRecognizer object and configure it"""
    speech_config = SpeechConfig(
        subscription=os.getenv("S2T_KEY"), region=os.getenv("S2T_LOCATION")
    )
    stream_format = AudioStreamFormat(
        samples_per_second=SAMPLE_RATE, bits_per_sample=16, channels=CHANNELS
    )
    input_stream = PushAudioInputStream(stream_format=stream_format)
    audio_config = AudioConfig(stream=input_stream)
    configure_language(speech_config, app_config.language)
    speech_recognizer = SpeechRecognizer(
        speech_config=speech_config, audio_config=audio_config
    )
    if app_config.phrase_list:
        configure_phrases(app_config.phrase_list, speech_recognizer)
    return speech_recognizer, input_stream


def configure_phrases(
    phrase_list: list[str], speech_recognizer: SpeechRecognizer
) -> None:
    """Add phrases to speech recognizer"""

    phrase_list_grammar = PhraseListGrammar.from_recognizer(speech_recognizer)
    map(phrase_list_grammar.addPhrase, phrase_list)
    if phrase_list:
        logging.info(f"Submitted phrases: {', '.join(phrase_list)}")


def configure_language(speech_config: SpeechConfig, language: str) -> None:
    """Set the language the audio material is based on"""
    speech_config.speech_recognition_language = LANGUAGE_DICT[language]


def init_speech_recognition(
    speech_recognizer: SpeechRecognizer,
    frontend_status: DeltaGenerator,
    outbound_stream: PushAudioInputStream,
    inbound_stream: WebRtcStreamerContext,
    frontend_transcription: DeltaGenerator,
) -> None:
    """Build pipeline mapping from inbound to outbound audio stream"""

    speech_recognizer.start_continuous_recognition()
    start_time = time.time()

    transcription_results = TranscriptionResults(text="", change_flag=False)
    setup_event_callbacks(speech_recognizer, transcription_results)

    while True:
        sound_chunk = pydub.AudioSegment.empty()

        try:
            audio_frames = inbound_stream.audio_receiver.get_frames(timeout=1)
        except queue.Empty:
            frontend_status.write(
                "No audio frame arrived. Make sure your microphone is activated."
            )
            logging.info("No frame arrived")
            time.sleep(0.1)
            continue

        frontend_status.write("Audio recognition activated. Say something!")

        for frame in audio_frames:
            sound_chunk += process_audio_frames(frame)

        if len(sound_chunk) > 0:
            sound_chunk = sound_chunk.set_channels(CHANNELS)
            sound_chunk = sound_chunk.set_frame_rate(SAMPLE_RATE)
            outbound_stream.write(sound_chunk.get_array_of_samples())

        if transcription_results.change_flag:
            st.session_state[TRANSCRIPT_STATE] = transcription_results.text
            frontend_transcription.write(
                transcription_results.text, unsafe_allow_html=True
            )
            transcription_results.change_flag = False

        if not inbound_stream.state.playing:
            speech_recognizer.stop_continuous_recognition()
            outbound_stream.close()

        duration = time.time() - start_time
        if duration > TIME_LIMIT:
            logging.info("Time limit reached.")
            speech_recognizer.stop_continuous_recognition()
            outbound_stream.close()
            stream_state = WebRtcStreamerState(playing=False, signalling=False)
            inbound_stream._set_state(state=stream_state)
            break


def setup_event_callbacks(
    speech_recognizer: SpeechRecognizer,
    transcription_results: TranscriptionResults,
) -> None:
    """Connect callbacks to the events fired by the speech recognizer"""

    recognition_batches = []

    def handle_recognition_item(evt: SpeechRecognitionEventArgs):
        transcription_results.text = (
            " ".join(recognition_batches) + " " + evt.result.text
        )
        transcription_results.change_flag = True

    def handle_recognition_batch(evt: SpeechRecognitionEventArgs):
        transcription_batch = evt.result.text
        recognition_batches.append(transcription_batch)
        transcription_results.text = " ".join(recognition_batches)
        transcription_results.change_flag = True

    speech_recognizer.recognizing.connect(handle_recognition_item)
    speech_recognizer.recognized.connect(handle_recognition_batch)
    speech_recognizer.session_started.connect(
        lambda evt: logging.info("SESSION STARTED: {}".format(evt))
    )
    speech_recognizer.session_stopped.connect(
        lambda evt: logging.info("SESSION STOPPED {}".format(evt))
    )
    speech_recognizer.canceled.connect(
        lambda evt: logging.info("CANCELED {}".format(evt))
    )


def process_audio_frames(frame: FrameT) -> AudioSegment:
    """Process audio frames from webrtc to pydub audio segment"""
    return AudioSegment(
        data=frame.to_ndarray().tobytes(),
        sample_width=frame.format.bytes,
        frame_rate=frame.sample_rate,
        channels=len(frame.layout.channels),
    )
