from models.database_handler import DatabaseHandler
from models.animal import Animal
from models.Schedule import Schedule
class ProjectsController:
    def __init__(self):
        self.db_handler = DatabaseHandler()

    # Animal-related methods
    def add_animal(self, name, initial_weight, last_weight, last_weighted):
        animal = Animal(
            animal_id=None,  # Will be set by the database
            name=name,
            initial_weight=initial_weight,
            last_weight=last_weight,
            last_weighted=last_weighted
        )
        animal_id = self.db_handler.add_animal(animal)
        return animal_id

    def remove_animal(self, animal_id):
        self.db_handler.remove_animal(animal_id)

    def update_animal(self, animal):
        self.db_handler.update_animal(animal)

    def get_all_animals(self):
        return self.db_handler.get_all_animals()
    
    def get_animal_by_id(self, animal_id):
        return self.db_handler.get_animal_by_id(animal_id)
    
    
    # Schedule related methods
    def add_schedule(self, schedule):
        schedule_id = self.db_handler.add_schedule(schedule)
        return schedule_id

    def remove_schedule(self, schedule_id):
        self.db_handler.remove_schedule(schedule_id)

    def get_all_schedules(self, trainer_id=None, role='normal'):
        if role == 'super':
            return self.db_handler.get_all_schedules()
        else:
            return self.db_handler.get_schedules_by_trainer(trainer_id)
        
    def get_schedule_details(self, schedule_id):
        return self.db_handler.get_schedule_details(schedule_id)

    def close(self):
        self.db_handler.close()