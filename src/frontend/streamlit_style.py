import base64
from pathlib import Path

import streamlit as st


def streamlit_style() -> str:
    """Configure visibility of streamlit elements"""
    return """
        <style>
        #MainMenu {visibility:hidden;}
        footer {visibility:hidden;}
        footer:after {
            content:'Developed by Cedric Issel';
            visibility: visible;
            display: block;
            position: relative;
            text-align: center;
        }
        </style>
    """


def max_page_width(max_width: int):
    """Configure max width of main page in pixels"""
    return f"""
        <style>
        .appview-container .main .block-container{{
            max-width: {max_width}px;
            padding-top: 1rem;
        }}
        </style>
    """


def configure_background_image(image_file: Path) -> str:
    """Configure background image"""
    encoded_string = get_base64_of_bin_file(image_file)
    return f"""
        <style>
        .css-0 {{
            ::before, ::after {{
                background-color: transparent
            }}
        .stApp {{
            background-image: url("data:image/png;base64,{encoded_string}");
            background-size: 1400px;
            background-repeat: no-repeat;
        }}
        </style>
    """


@st.cache(allow_output_mutation=True)
def get_base64_of_bin_file(bin_file):
    """Convert image to base64 encoding"""
    with open(bin_file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()
