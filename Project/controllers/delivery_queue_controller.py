from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from datetime import datetime, timedelta
import heapq

class DeliveryQueueController(QObject):
    delivery_status = pyqtSignal(str)
    delivery_complete = pyqtSignal(dict)
    queue_updated = pyqtSignal()
    
    def __init__(self, pump_controller, database_handler, relay_handler, volume_calculator):
        super().__init__()
        self.pump_controller = pump_controller
        self.database_handler = database_handler
        self.relay_handler = relay_handler
        self.volume_calculator = volume_calculator
        self.delivery_queue = []  # Priority queue
        self.active_deliveries = set()  # Track active relay units
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.check_schedule)
        self.check_timer.start(1000)  # Check every second
        self.current_delivery = None
        self.delivery_attempts = {}  # Track attempts and delivered volume
        
    def sort_queue_entry(self, instant):
        """Create a sortable queue entry tuple"""
        return (
            instant['delivery_time'].timestamp(),  # Primary sort: delivery time
            len(self.active_deliveries),          # Secondary sort: current load
            instant['relay_unit_id'],             # Tertiary sort: group by relay unit
            instant['instant_id']                 # Final sort: unique ID
        )
        
    async def load_schedule(self, schedule_id):
        """Load schedule deliveries into queue"""
        schedule = await self.database_handler.get_schedule_details(schedule_id)
        
        if schedule.delivery_mode == 'instant':
            for delivery in schedule.instant_deliveries:
                entry = {
                    'instant_id': f"{schedule_id}_{delivery['datetime'].timestamp()}",
                    'schedule_id': schedule_id,
                    'relay_unit_id': delivery['relay_unit_id'],
                    'delivery_time': delivery['datetime'],
                    'water_volume': delivery['volume'],
                    'num_triggers': self.volume_calculator.calculate_triggers(delivery['volume']),
                    'priority': 1
                }
                heapq.heappush(self.delivery_queue, (self.sort_queue_entry(entry), entry))
        # For staggered mode, queue is managed by RelayWorker
        
    async def requeue_instant(self, instant, delay_minutes=1):
        """Requeue a failed delivery with delay"""
        instant['delivery_time'] = datetime.now() + timedelta(minutes=delay_minutes)
        entry = (
            self.sort_queue_entry(instant),
            instant
        )
        heapq.heappush(self.delivery_queue, entry)
        self.queue_updated.emit()
        
    async def check_schedule(self):
        """Process due deliveries"""
        now = datetime.now().timestamp()
        
        while self.delivery_queue:
            delivery_time, _, _, instant = self.delivery_queue[0]
            
            if delivery_time <= now:
                # Time to deliver
                heapq.heappop(self.delivery_queue)
                await self.process_delivery(instant)
            else:
                break
                
    async def get_delivered_volume(self, schedule_id, animal_id):
        """Get total volume delivered for a specific schedule and animal"""
        try:
            with self.database_handler.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COALESCE(SUM(volume_dispensed), 0)
                    FROM dispensing_history
                    WHERE schedule_id = ? AND animal_id = ? AND status = 'completed'
                ''', (schedule_id, animal_id))
                return cursor.fetchone()[0]
        except Exception as e:
            self.delivery_status.emit(f"Error getting delivered volume: {str(e)}")
            return 0

    async def process_delivery(self, instant):
        try:
            # If there's a current delivery, only allow requeue if it's the same animal
            if self.current_delivery:
                if instant['animal_id'] == self.current_delivery['animal_id']:
                    await self.requeue_instant(instant, delay_minutes=0.5)
                return

            self.current_delivery = instant
            delivered_volume = await self.get_delivered_volume(
                instant['schedule_id'], 
                instant['animal_id']
            )
            
            remaining_volume = instant['water_volume'] - delivered_volume
            if remaining_volume <= 0:
                await self.database_handler.mark_instant_completed(instant['instant_id'])
                self.current_delivery = None
                # Signal completion for this animal before moving to next
                self.delivery_complete.emit({
                    'animal_id': instant['animal_id'],
                    'total_volume': instant['water_volume']
                })
                return

            # Use existing trigger calculation
            num_triggers = self.volume_calculator.calculate_triggers(remaining_volume)
            max_triggers_per_attempt = 5
            triggers_this_attempt = min(num_triggers, max_triggers_per_attempt)
            volume_this_attempt = (triggers_this_attempt * self.volume_calculator.pump_volume_ul) / 1000

            success = await self.pump_controller.dispense_water(
                instant['relay_unit_id'],
                volume_this_attempt,
                triggers_this_attempt
            )

            # Log attempt (using existing code)
            with self.database_handler.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO dispensing_history 
                    (schedule_id, animal_id, relay_unit_id, timestamp, 
                     volume_dispensed, status)
                    VALUES (?, ?, ?, datetime('now'), ?, ?)
                ''', (
                    instant['schedule_id'], 
                    instant['animal_id'], 
                    instant['relay_unit_id'], 
                    volume_this_attempt,
                    'completed' if success else 'failed'
                ))
                conn.commit()

            if success:
                new_total = delivered_volume + volume_this_attempt
                if new_total >= instant['water_volume']:
                    await self.database_handler.mark_instant_completed(instant['instant_id'])
                    self.delivery_status.emit(f"Completed delivery of {instant['water_volume']}mL")
                    # Block other animals until this one is complete
                    self.delivery_complete.emit({
                        'animal_id': instant['animal_id'],
                        'total_volume': instant['water_volume']
                    })
                else:
                    # Immediately requeue same animal with high priority
                    instant['priority'] = 0  # Highest priority
                    await self.requeue_instant(instant, delay_minutes=0.1)
            else:
                # Retry same volume on failure
                await self.requeue_instant(instant, delay_minutes=1)
                
            self.current_delivery = None
                
        except Exception as e:
            self.delivery_status.emit(f"Delivery error: {str(e)}")
            self.current_delivery = None
        
    async def track_delivery(self, delivery_data):
        """Track completed delivery in database"""
        try:
            with self.database_handler.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO dispensing_history 
                    (animal_id, relay_unit_id, timestamp, volume_dispensed, status)
                    VALUES (?, ?, datetime('now'), ?, ?)
                ''', (
                    delivery_data['animal_id'],
                    delivery_data['relay_unit_id'],
                    delivery_data['volume_ml'],
                    delivery_data['status']
                ))
                conn.commit()
                
            self.delivery_complete.emit(delivery_data)
            
        except Exception as e:
            self.delivery_status.emit(f"Error tracking delivery: {str(e)}")
        
    async def start_schedule(self, schedule, mode, window_start, window_end):
        # ... existing code ...
        
        if mode == "Staggered":
            worker_settings.update({
                'relay_unit_assignments': schedule.relay_unit_assignments,
                'schedule_id': schedule.schedule_id
            })
        
        worker = RelayWorker(
            worker_settings,
            self.relay_handler,
            self.notification_handler,
            self.delivery_queue
        )

    async def load_staggered_windows(self):
        """Load active staggered delivery windows into queue"""
        windows = await self.database_handler.get_active_staggered_windows()
        
        for window in windows:
            remaining_volume = window['target_volume'] - window['delivered_volume']
            if remaining_volume <= 0:
                continue
            
            entry = {
                'window_id': window['window_id'],
                'schedule_id': window['schedule_id'],
                'animal_id': window['animal_id'],
                'relay_unit_id': window['relay_unit_id'],
                'start_time': datetime.fromisoformat(window['start_time']),
                'end_time': datetime.fromisoformat(window['end_time']),
                'target_volume': window['target_volume'],
                'remaining_volume': remaining_volume,
                'mode': 'staggered'
            }
            
            # Calculate delivery instants within window
            timing = self.timing_calculator.calculate_staggered_timing(
                entry['start_time'],
                entry['end_time'],
                [{'animal_id': entry['animal_id'], 'volume_ml': remaining_volume}]
            )
            
            # Add each delivery instant to queue
            for instant in timing['schedule'][entry['animal_id']]['instants']:
                instant_entry = {
                    **entry,
                    'instant_id': f"staggered_{window['window_id']}_{instant['time'].timestamp()}",
                    'delivery_time': instant['time'],
                    'water_volume': instant['volume'],
                    'num_triggers': instant['triggers']
                }
                heapq.heappush(
                    self.delivery_queue,
                    (self.sort_queue_entry(instant_entry), instant_entry)
                )
