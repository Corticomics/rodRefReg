# Project/main.py
from app_controller import AppController

def main():
    controller = AppController()
    controller.setup()
    controller.execute()

if __name__ == "__main__":
    main()
