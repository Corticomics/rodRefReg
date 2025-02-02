from PyQt5.QtCore import QObject, pyqtSignal, QThread
from datetime import datetime
import asyncio
from gpio.relay_worker import RelayWorker
from utils.volume_calculator import VolumeCalculator
from utils.timing_calculator import TimingCalculator

class ScheduleController(QObject):
    """
    Controls the execution and management of watering schedules.
    Handles schedule state, execution flow, and error handling.
    """
    schedule_status = pyqtSignal(str)
    schedule_complete = pyqtSignal(dict)
    
    def __init__(self, pump_controller, database_handler, relay_handler, notification_handler, delivery_queue_controller, settings):
        super().__init__()
        self.pump_controller = pump_controller
        self.database_handler = database_handler
        self.relay_handler = relay_handler
        self.notification_handler = notification_handler
        self.delivery_queue = delivery_queue_controller
        self.active_schedules = {}
        self.volume_calculator = VolumeCalculator(settings)
        self.timing_calculator = TimingCalculator(settings)
        
        # Connect to delivery queue signals
        self.delivery_queue.delivery_complete.connect(self.handle_delivery_complete)
        self.delivery_queue.delivery_status.connect(self.handle_delivery_status)
        
    async def start_schedule(self, schedule, window_start, window_end):
        """Start executing a schedule"""
        try:
            schedule_id = schedule.schedule_id
            
            # Prevent duplicate starts
            if schedule_id in self.active_schedules:
                self.schedule_status.emit(f"Schedule {schedule_id} already running")
                return
            
            # Initialize schedule tracking
            self.active_schedules[schedule_id] = {
                'schedule': schedule,
                'window_start': window_start,
                'window_end': window_end,
                'dispensed_volumes': {},
                'status': 'running',
                'mode': schedule.delivery_mode
            }
            
            # Load schedule into delivery queue
            await self.delivery_queue.load_schedule(schedule_id)
            
            self.schedule_status.emit(
                f"Started {schedule.delivery_mode} schedule {schedule.name} "
                f"from {window_start} to {window_end}"
            )
            
            # Start completion checking
            asyncio.create_task(self.check_schedule_completion(schedule_id))
            
        except Exception as e:
            self.schedule_status.emit(f"Schedule start error: {str(e)}")
            if schedule_id in self.active_schedules:
                del self.active_schedules[schedule_id]
    
    async def check_schedule_completion(self, schedule_id):
        """Periodically check if schedule is complete"""
        try:
            while schedule_id in self.active_schedules:
                schedule_data = self.active_schedules[schedule_id]
                
                if datetime.now() > schedule_data['window_end']:
                    await self.handle_schedule_complete(schedule_id, "Window ended")
                    break
                
                # Check if all volumes are delivered
                all_complete = True
                schedule = schedule_data['schedule']
                
                for animal_id in schedule.animals:
                    delivered = schedule_data['dispensed_volumes'].get(str(animal_id), 0)
                    target = schedule.desired_water_outputs.get(
                        str(animal_id), 
                        schedule.water_volume
                    )
                    if delivered < target:
                        all_complete = False
                        break
                
                if all_complete:
                    await self.handle_schedule_complete(schedule_id, "All volumes delivered")
                    break
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
        except Exception as e:
            self.schedule_status.emit(f"Completion check error: {str(e)}")
    
    async def handle_schedule_complete(self, schedule_id, reason=""):
        """Handle schedule completion"""
        try:
            if schedule_id not in self.active_schedules:
                return
                
            schedule_data = self.active_schedules[schedule_id]
            
            # Log completion
            await self.database_handler.update_schedule_status(
                schedule_id,
                'completed',
                schedule_data['dispensed_volumes']
            )
            
            # Notify completion
            completion_msg = (
                f"Schedule {schedule_data['schedule'].name} completed: {reason}\n"
                f"Delivered volumes:"
            )
            for animal_id, volume in schedule_data['dispensed_volumes'].items():
                completion_msg += f"\nAnimal {animal_id}: {volume:.3f}mL"
            
            self.schedule_status.emit(completion_msg)
            if self.notification_handler:
                self.notification_handler.send_slack_notification(completion_msg)
            
            # Emit completion signal
            self.schedule_complete.emit({
                'schedule_id': schedule_id,
                'volumes': schedule_data['dispensed_volumes'].copy(),
                'reason': reason
            })
            
            # Cleanup
            del self.active_schedules[schedule_id]
            
        except Exception as e:
            self.schedule_status.emit(f"Completion handling error: {str(e)}")
    
    def handle_delivery_complete(self, delivery_data):
        """Handle completed delivery from queue"""
        schedule_id = delivery_data.get('schedule_id')
        if schedule_id in self.active_schedules:
            animal_id = str(delivery_data['animal_id'])
            volume = delivery_data['total_volume']
            
            # Update tracking
            current = self.active_schedules[schedule_id]['dispensed_volumes'].get(animal_id, 0)
            self.active_schedules[schedule_id]['dispensed_volumes'][animal_id] = current + volume
    
    def handle_delivery_status(self, status_msg):
        """Forward delivery status messages"""
        self.schedule_status.emit(status_msg)
    
    async def pause_schedule(self, schedule_id):
        """Pause a running schedule"""
        if schedule_id in self.active_schedules:
            self.active_schedules[schedule_id]['status'] = 'paused'
            await self.database_handler.update_schedule_status(
                schedule_id,
                'paused',
                self.active_schedules[schedule_id]['dispensed_volumes']
            )
            self.schedule_status.emit(f"Paused schedule {schedule_id}")
    
    def stop_all_schedules(self):
        """Stop all running schedules"""
        for schedule_id in list(self.active_schedules.keys()):
            asyncio.create_task(self.pause_schedule(schedule_id))