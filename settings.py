import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    MAIL_TO = os.getenv("MAIL_TO")
    MAIL_USER = os.getenv("MAIL_USER")
    MAIL_PASS = os.getenv("MAIL_PASS")
    GEO_KEY = os.getenv("GEO_KEY")
