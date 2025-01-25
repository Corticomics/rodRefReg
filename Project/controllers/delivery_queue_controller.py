from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from datetime import datetime, timedelta
import heapq
import logging

class DeliveryQueueController(QObject):
    delivery_status = pyqtSignal(str)
    delivery_complete = pyqtSignal(dict)
    queue_updated = pyqtSignal()
    cycle_complete = pyqtSignal(dict)  # New signal for cycle completion
    
    def __init__(self, pump_controller, database_handler, relay_handler, volume_calculator, timing_calculator):
        super().__init__()
        self.pump_controller = pump_controller
        self.database_handler = database_handler
        self.relay_handler = relay_handler
        self.volume_calculator = volume_calculator
        self.timing_calculator = timing_calculator
        
        self.delivery_queue = []  # Priority queue
        self.active_deliveries = set()  # Track active relay units
        self.current_delivery = None
        self.delivery_attempts = {}  # Track attempts and delivered volume
        self.cycle_tracking = {}    # Track cycle progress
        
        # Setup check timer
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.check_schedule)
        self.check_timer.start(1000)  # Check every second
        
    def sort_queue_entry(self, instant):
        """Create a sortable queue entry tuple"""
        priority = 0 if instant.get('is_recovery', False) else 1
        return (
            priority,                                # First sort: recovery priority
            instant['delivery_time'].timestamp(),    # Second sort: delivery time
            len(self.active_deliveries),            # Third sort: current load
            instant['relay_unit_id'],               # Fourth sort: group by relay unit
            instant.get('cycle_index', 0),          # Fifth sort: cycle order
            instant['instant_id']                   # Final sort: unique ID
        )
        
    async def load_schedule(self, schedule_id):
        """Load schedule deliveries into queue"""
        try:
            schedule = await self.database_handler.get_schedule_details(schedule_id)
            
            if schedule.delivery_mode == 'instant':
                await self._load_instant_schedule(schedule)
            else:
                await self._load_staggered_schedule(schedule)
                
            self.queue_updated.emit()
            
        except Exception as e:
            logging.error(f"Error loading schedule {schedule_id}: {str(e)}")
            self.delivery_status.emit(f"Failed to load schedule: {str(e)}")
            
    async def _load_instant_schedule(self, schedule):
        """Load instant delivery schedule"""
        for delivery in schedule.instant_deliveries:
            entry = {
                'instant_id': f"{schedule.schedule_id}_{delivery['datetime'].timestamp()}",
                'schedule_id': schedule.schedule_id,
                'animal_id': delivery['animal_id'],
                'relay_unit_id': delivery['relay_unit_id'],
                'delivery_time': delivery['datetime'],
                'water_volume': delivery['volume'],
                'num_triggers': self.volume_calculator.calculate_triggers(delivery['volume']),
                'mode': 'instant'
            }
            heapq.heappush(self.delivery_queue, (self.sort_queue_entry(entry), entry))
            
    async def _load_staggered_schedule(self, schedule):
        """Load staggered delivery schedule with cycles"""
        animals_data = []
        for animal_id in schedule.animals:
            animals_data.append({
                'animal_id': animal_id,
                'volume_ml': schedule.desired_water_outputs.get(str(animal_id), schedule.water_volume),
                'relay_unit_id': schedule.relay_unit_assignments.get(str(animal_id))
            })
        
        # Calculate timing for all animals
        timing_plan = self.timing_calculator.calculate_staggered_timing(
            datetime.fromisoformat(schedule.start_time),
            datetime.fromisoformat(schedule.end_time),
            animals_data
        )
        
        # Initialize cycle tracking
        self.cycle_tracking[schedule.schedule_id] = {
            animal['animal_id']: {
                'current_cycle': 0,
                'cycles_completed': 0,
                'volume_delivered': 0
            } for animal in animals_data
        }
        
        # Queue all delivery instants
        for animal_id, animal_plan in timing_plan['schedule'].items():
            for cycle_idx, cycle in enumerate(animal_plan['delivery_instants']):
                entry = {
                    'instant_id': f"stag_{schedule.schedule_id}_{animal_id}_{cycle['time'].timestamp()}",
                    'schedule_id': schedule.schedule_id,
                    'animal_id': animal_id,
                    'relay_unit_id': cycle['relay_unit_id'],
                    'delivery_time': cycle['time'],
                    'water_volume': cycle['volume'],
                    'num_triggers': cycle['triggers'],
                    'cycle_index': cycle_idx,
                    'total_cycles': animal_plan['total_cycles'],
                    'mode': 'staggered'
                }
                heapq.heappush(self.delivery_queue, (self.sort_queue_entry(entry), entry))
                
    async def process_delivery(self, instant):
        """Process a single delivery instant"""
        try:
            if self.current_delivery:
                if instant['animal_id'] == self.current_delivery['animal_id']:
                    await self.requeue_instant(instant, delay_minutes=0.5)
                return

            self.current_delivery = instant
            delivered_volume = await self.get_delivered_volume(
                instant['schedule_id'], 
                instant['animal_id']
            )
            
            # Calculate volume for this attempt
            remaining_volume = instant['water_volume'] - delivered_volume
            if remaining_volume <= 0:
                await self._complete_delivery(instant)
                return

            # Execute delivery
            success = await self._execute_delivery(instant, remaining_volume)
            
            if success:
                # Update cycle tracking for staggered mode
                if instant['mode'] == 'staggered':
                    await self._update_cycle_progress(instant)
                
                # Check if complete or needs requeue
                new_total = delivered_volume + instant['water_volume']
                if new_total >= instant['water_volume']:
                    await self._complete_delivery(instant)
                else:
                    await self.requeue_instant(instant, delay_minutes=0.1)
            else:
                # Handle failure
                await self._handle_delivery_failure(instant)
                
        except Exception as e:
            logging.error(f"Error processing delivery: {str(e)}")
            self.delivery_status.emit(f"Delivery error: {str(e)}")
        finally:
            self.current_delivery = None
            
    async def _execute_delivery(self, instant, volume):
        """Execute the actual delivery"""
        num_triggers = self.volume_calculator.calculate_triggers(volume)
        max_triggers_per_attempt = self.volume_calculator.max_triggers_per_cycle
        triggers_this_attempt = min(num_triggers, max_triggers_per_attempt)
        volume_this_attempt = (triggers_this_attempt * self.volume_calculator.pump_volume_ul) / 1000

        success = await self.pump_controller.dispense_water(
            instant['relay_unit_id'],
            volume_this_attempt,
            triggers_this_attempt
        )

        await self.track_delivery({
            'schedule_id': instant['schedule_id'],
            'animal_id': instant['animal_id'],
            'relay_unit_id': instant['relay_unit_id'],
            'volume_ml': volume_this_attempt,
            'status': 'completed' if success else 'failed',
            'cycle_index': instant.get('cycle_index')
        })

        return success
        
    async def _update_cycle_progress(self, instant):
        """Update cycle progress tracking"""
        tracking = self.cycle_tracking[instant['schedule_id']][instant['animal_id']]
        tracking['volume_delivered'] += instant['water_volume']
        
        if instant['cycle_index'] > tracking['current_cycle']:
            tracking['cycles_completed'] += 1
            tracking['current_cycle'] = instant['cycle_index']
            
            self.cycle_complete.emit({
                'schedule_id': instant['schedule_id'],
                'animal_id': instant['animal_id'],
                'cycle': instant['cycle_index'],
                'total_cycles': instant['total_cycles']
            })

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

    async def _complete_delivery(self, instant):
        await self.database_handler.mark_instant_completed(instant['instant_id'])
        self.delivery_status.emit(f"Completed delivery of {instant['water_volume']}mL")
        self.delivery_complete.emit({
            'animal_id': instant['animal_id'],
            'total_volume': instant['water_volume']
        })
        
    async def _handle_delivery_failure(self, instant):
        # Retry same volume on failure
        await self.requeue_instant(instant, delay_minutes=1)
        
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
