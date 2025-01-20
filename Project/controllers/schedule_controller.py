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
        self.workers = {}  # Store active RelayWorkers
        self.worker_threads = {}  # Store worker threads
        self.volume_calculator = VolumeCalculator(settings)
        self.timing_calculator = TimingCalculator(settings)
        
    async def start_schedule(self, schedule, mode, window_start, window_end):
        """Start executing a schedule in specified mode"""
        try:
            schedule_id = schedule.schedule_id
            
            # Calculate base water volume and triggers
            base_volume = schedule.water_volume
            base_triggers = self.volume_calculator.calculate_triggers(base_volume)
            
            if mode == "Instant":
                # Use timing calculator for instant deliveries
                animals_data = [
                    {'animal_id': d['animal_id'], 'volume_ml': d['volume']}
                    for d in schedule.instant_deliveries
                ]
                timing_plan = self.timing_calculator.calculate_instant_timing(
                    window_start, 
                    animals_data
                )
                
                worker_settings = {
                    'mode': mode,
                    'delivery_instants': [
                        {
                            'relay_unit_id': schedule.relay_unit_id,
                            'delivery_time': timing['start_time'].isoformat(),
                            'water_volume': animals_data[idx]['volume_ml'],
                            'num_triggers': len(timing['trigger_times'])
                        }
                        for idx, (animal_id, timing) in enumerate(timing_plan.items())
                    ]
                }
            else:  # Staggered mode
                animals_data = [
                    {'animal_id': animal_id, 'volume_ml': schedule.desired_water_outputs.get(str(animal_id), base_volume)}
                    for animal_id in schedule.animals
                ]
                
                timing_plan = self.timing_calculator.calculate_staggered_timing(
                    window_start,
                    window_end,
                    animals_data
                )
                
                worker_settings = {
                    'mode': mode,
                    'window_start': window_start,
                    'window_end': window_end,
                    'delivery_instants': [],
                    'target_volumes': {
                        str(animal['animal_id']): animal['volume_ml'] 
                        for animal in animals_data
                    },
                    'cycle_interval': timing_plan['cycle_interval'],
                    'stagger_interval': timing_plan['stagger_interval'],
                    'pump_volume_ul': self.volume_calculator.pump_volume_ul
                }
            
            # Create and start RelayWorker
            worker = RelayWorker(worker_settings, self.relay_handler, self.notification_handler)
            worker_thread = QThread()
            self.workers[schedule_id] = worker
            self.worker_threads[schedule_id] = worker_thread
            
            worker.moveToThread(worker_thread)
            worker.progress.connect(lambda msg: self.schedule_status.emit(msg))
            worker.finished.connect(lambda: self.handle_schedule_complete(schedule_id))
            
            # Add schedule to delivery queue before starting worker
            await self.delivery_queue.load_schedule(schedule_id)
            
            worker_thread.started.connect(worker.run_cycle)
            worker_thread.start()
            
            self.active_schedules[schedule_id] = {
                'schedule': schedule,
                'dispensed_volumes': {},
                'status': 'running'
            }
            
        except Exception as e:
            self.schedule_status.emit(f"Schedule error: {str(e)}")
    
    def handle_schedule_complete(self, schedule_id):
        """Handle schedule completion"""
        if schedule_id in self.workers:
            worker = self.workers[schedule_id]
            thread = self.worker_threads[schedule_id]
            
            # Cleanup
            worker.deleteLater()
            thread.quit()
            thread.wait()
            thread.deleteLater()
            
            del self.workers[schedule_id]
            del self.worker_threads[schedule_id]
            
            self.schedule_complete.emit(self.active_schedules[schedule_id]['dispensed_volumes'])
    
    async def pause_schedule(self, schedule_id):
        """Pause a running schedule"""
        if schedule_id in self.workers:
            worker = self.workers[schedule_id]
            worker.stop()
            
            # Update schedule status
            if schedule_id in self.active_schedules:
                self.active_schedules[schedule_id]['status'] = 'paused'
                await self.database_handler.update_schedule_status(
                    schedule_id,
                    'paused',
                    self.active_schedules[schedule_id]['dispensed_volumes']
                )
    
    def stop_all_schedules(self):
        """Stop all running schedules"""
        for schedule_id in list(self.workers.keys()):
            asyncio.create_task(self.pause_schedule(schedule_id))