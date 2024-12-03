# controllers/watering_controller.py
class WateringController:
    def __init__(self, database_handler, pump_controller):
        self.db = database_handler
        self.pump_controller = pump_controller
        self.active_schedules = {}