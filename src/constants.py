from dataclasses import dataclass

TRANSCRIPT_STATE = "transcript"


@dataclass
class AppSettings:
    language: str
    phrase_list: list[str]
