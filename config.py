from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("API_KEY")
PROXY: dict = {
    "server": "proxy-server.scraperapi.com:8001",
    "username": "scraperapi",
    "password": API_KEY,
}

with open("user-agents.txt") as f:
    USER_AGENTS = [line.strip() for line in f.readlines()]
