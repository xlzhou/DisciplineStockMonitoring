from app.config import load_env
from app.scheduler import start_scheduler

if __name__ == "__main__":
    load_env()
    start_scheduler()
