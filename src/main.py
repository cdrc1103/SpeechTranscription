import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from frontend.dashboard import run_app

if __name__ == "__main__":

    load_dotenv(Path(__file__).parents[0].joinpath(".env"))

    logging.basicConfig(
        filename=f"{Path(__file__).parents[0]}/logs/last_run.log",
        filemode="a",
        format="[%(asctime)s] %(levelname)7s from %(name)s: %(message)s",
        force=True,
    )

    run_app()
