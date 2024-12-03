from PyQt5.QtCore import QObject, pyqtSignal, QThread
from datetime import datetime
import asyncio
from gpio.relay_worker import RelayWorker

class ScheduleController(QObject):
    """
    Controls the execution and management of watering schedules.
    Handles schedule state, execution flow, and error handling.
    """
    schedule_status = pyqtSignal(str)
    schedule_complete = pyqtSignal(dict)
    
    def __init__(self, pump_controller, database_handler, relay_handler, notification_handler, delivery_queue_controller):
        super().__init__()
        self.pump_controller = pump_controller
        self.database_handler = database_handler
        self.relay_handler = relay_handler
        self.notification_handler = notification_handler
        self.delivery_queue = delivery_queue_controller
        self.active_schedules = {}
        self.workers = {}  # Store active RelayWorkers
        self.worker_threads = {}  # Store worker threads
        
    async def start_schedule(self, schedule_id):
        """Start executing a schedule by ID"""
        try:
            schedule = await self.database_handler.get_schedule_details(schedule_id)
            if not schedule:
                raise ValueError("Schedule not found")
            
            # Get all pending time instants for this schedule
            instants = await self.database_handler.get_pending_schedule_instants(schedule_id)
            if not instants:
                raise ValueError("No pending deliveries found for schedule")
                
            # Create settings for the RelayWorker with time instants
            worker_settings = {
                'delivery_instants': instants,
                'stagger': 5,  # 5 seconds between triggers
                'num_triggers': {}
            }
            
            # Map animals to relay units and set trigger counts
            for instant in instants:
                relay_unit_id = instant['relay_unit_id']
                if str(relay_unit_id) not in worker_settings['num_triggers']:
                    worker_settings['num_triggers'][str(relay_unit_id)] = 1
            
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