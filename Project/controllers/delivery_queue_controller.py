from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from datetime import datetime, timedelta
import heapq

class DeliveryQueueController(QObject):
    delivery_status = pyqtSignal(str)
    delivery_complete = pyqtSignal(dict)
    queue_updated = pyqtSignal()
    
    def __init__(self, pump_controller, database_handler, relay_handler):
        super().__init__()
        self.pump_controller = pump_controller
        self.database_handler = database_handler
        self.relay_handler = relay_handler
        self.delivery_queue = []  # Priority queue
        self.active_deliveries = set()  # Track active relay units
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.check_schedule)
        self.check_timer.start(1000)  # Check every second
        
    def sort_queue_entry(self, instant):
        """Create a sortable queue entry tuple"""
        return (
            instant['delivery_time'].timestamp(),  # Primary sort: delivery time
            len(self.active_deliveries),          # Secondary sort: current load
            instant['relay_unit_id'],             # Tertiary sort: group by relay unit
            instant['instant_id']                 # Final sort: unique ID
        )
        
    async def load_schedule(self, schedule_id):
        """Load schedule time instants into delivery queue"""
        if not self.can_accept_schedule(schedule_id):
            raise ValueError("No available relay units")
            
        instants = await self.database_handler.get_pending_schedule_instants(schedule_id)
        for instant in instants:
            entry = (
                self.sort_queue_entry(instant),
                instant
            )
            heapq.heappush(self.delivery_queue, entry)
        self.queue_updated.emit()
        
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
                
    async def process_delivery(self, instant):
        """Process a single water delivery"""
        try:
            relay_unit = await self.database_handler.get_relay_unit_for_animal(
                instant['animal_id']
            )
            
            success = await self.pump_controller.dispense_water(
                relay_unit,
                instant['water_volume']
            )
            
            if success:
                await self.database_handler.mark_instant_completed(
                    instant['instant_id']
                )
                self.delivery_status.emit(
                    f"Delivered {instant['water_volume']}mL to animal {instant['animal_id']}"
                )
            else:
                # Requeue with small delay
                heapq.heappush(
                    self.delivery_queue,
                    (
                        datetime.now().timestamp() + 60,  # Retry in 1 minute
                        instant['priority'],
                        instant
                    )
                )
                
        except Exception as e:
            self.delivery_status.emit(f"Delivery error: {str(e)}") 