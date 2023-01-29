from pathlib import Path

import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer

from backend.inference import setup_inference_pipeline
from constants import TRANSCRIPT_STATE, AppSettings
from frontend.settings import LANGUAGE_DICT, LAYOUT, MAX_PAGE_WIDTH, PAGE_TITLE
from frontend.streamlit_style import max_page_width, streamlit_style

STYLE_ELEMENTS = Path(__file__).parents[1].joinpath("media")


def run_app() -> None:
    """Initialize the streamlit app"""

    # Page config
    st.set_page_config(
        page_title=PAGE_TITLE,
        layout=LAYOUT,
    )
    st.markdown(streamlit_style(), unsafe_allow_html=True)
    st.markdown(max_page_width(MAX_PAGE_WIDTH), unsafe_allow_html=True)

    # Initialization of state persisting variables
    if TRANSCRIPT_STATE not in st.session_state:
        st.session_state[TRANSCRIPT_STATE] = ""

    # Header and Intro
    st.header("Real Time Speech Transcription")

    with st.expander("ℹ️ - About this app", expanded=False):
        st.markdown(
            """
            - click on SELECT DEVICE and choose your microphone
            - have a look at the settings and make adjustments if needed
            - hit the START button to initialize the transcription
            - Wait for the signal that your microphone is active and start speaking...
        """
        )

    # Main Page
    col1, col2 = st.columns([2, 6])

    # Config
    with col1:
        st.markdown("### Settings")
        language = st.selectbox(
            "Choose a language.", tuple(LANGUAGE_DICT.keys()), 0
        )

        phrase_list = []
        phrase_list.append(
            st.text_input(
                "Enter special phrases or abbreviations you would like the AI to understand."
            )
        )
        st.markdown(", ".join(phrase_list))

    # Transcription
    with col2:
        st.markdown("### Transcription")
        st.write("")

        # WebRTC interface
        webrtc_ctx = webrtc_streamer(
            key="speech-to-text",
            mode=WebRtcMode.SENDONLY,
            audio_receiver_size=1024,
            rtc_configuration={
                "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
            },
            media_stream_constraints={"video": False, "audio": True},
        )
        # Recognition status
        status_indicator = st.empty()

        # Transcript text
        transcript_block = st.expander("Recognized Text", expanded=True)
        with transcript_block:
            transcript_placeholder = st.empty()

    # Placeholder for Transcript content
    transcript_placeholder.write(st.session_state[TRANSCRIPT_STATE])

    # Gate that awaits activation of webrtc streamer
    if not webrtc_ctx.state.playing:
        status_indicator.write("Audio recognition deactivated.")
        return

    # Reset transcription content when audio stream is started
    transcript_placeholder.write("")

    # load transcript configuration
    app_config = AppSettings(language=language, phrase_list=phrase_list)

    # azure speech service
    setup_inference_pipeline(
        status_indicator, transcript_placeholder, webrtc_ctx, app_config
    )
