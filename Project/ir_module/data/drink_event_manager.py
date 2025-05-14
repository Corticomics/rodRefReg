"""
Event processing system for IR sensor events.

This module handles the processing of IR sensor events, including drink
session detection, data aggregation, and database storage.
"""

import logging
import time
from threading import Thread
from queue import Queue, Empty
from datetime import datetime

logger = logging.getLogger(__name__)

class DrinkEventManager:
    """
    Manager for processing drink events from IR sensors.
    
    This class processes raw beam break events into meaningful drinking
    sessions, and handles the storage of these events in the database.
    """
    
    def __init__(self, database_handler=None, animal_relay_mapping=None):
        """
        Initialize the drink event manager.
        
        Args:
            database_handler: Database handler for storing events (optional).
            animal_relay_mapping: Object that maps relay units to animals.
        """
        self.database_handler = database_handler
        self.animal_relay_mapping = animal_relay_mapping
        
        # Queue for thread-safe event processing
        self.event_queue = Queue()
        self.running = True
        
        # Active drinking sessions
        self.active_sessions = {}
        
        # Start the event processing thread
        self.process_thread = Thread(target=self._process_events)
        self.process_thread.daemon = True
        self.process_thread.start()
        
        logger.info("DrinkEventManager initialized")
    
    def queue_event(self, event):
        """
        Queue an event for processing.
        
        Args:
            event (dict): Event data including type, relay_unit_id, and timestamp.
        """
        self.event_queue.put(event)
    
    def _process_events(self):
        """Process events from the queue in a background thread."""
        while self.running:
            try:
                # Get an event with a timeout to allow clean shutdown
                event = self.event_queue.get(timeout=1.0)
                self._handle_event(event)
                self.event_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}")
    
    def _handle_event(self, event):
        """
        Handle a single event.
        
        Args:
            event (dict): Event data to process.
        """
        try:
            event_type = event.get('type')
            relay_unit_id = event.get('relay_unit_id')
            timestamp = event.get('timestamp')
            
            # Get animal ID from mapping
            animal_id = event.get('animal_id')
            if not animal_id and self.animal_relay_mapping:
                animal_id = self.animal_relay_mapping.get_animal_for_relay(relay_unit_id)
            
            # Skip if we can't determine the animal
            if not animal_id:
                logger.warning(f"Could not determine animal for relay unit {relay_unit_id}")
                return
            
            if event_type == 'beam_break':
                self._handle_beam_break(relay_unit_id, animal_id, timestamp)
            elif event_type == 'session_start':
                self._handle_session_start(relay_unit_id, animal_id, timestamp)
            elif event_type == 'session_end':
                self._handle_session_end(
                    relay_unit_id, 
                    animal_id, 
                    event.get('start_time'),
                    event.get('end_time'),
                    event.get('duration_ms')
                )
        except Exception as e:
            logger.error(f"Error handling event: {e}")
    
    def _handle_beam_break(self, relay_unit_id, animal_id, timestamp):
        """
        Handle a beam break event.
        
        Args:
            relay_unit_id (int): ID of the relay unit.
            animal_id (int): ID of the animal.
            timestamp (float): Timestamp of the event.
        """
        # Create a session key for this animal/relay combination
        session_key = f"{animal_id}_{relay_unit_id}"
        
        # Check if a session already exists
        if session_key in self.active_sessions:
            # Update the last activity time
            self.active_sessions[session_key]['last_activity'] = timestamp
            logger.debug(f"Updated active session for animal {animal_id} at {timestamp}")
        else:
            # Start a new session
            self.active_sessions[session_key] = {
                'start_time': timestamp,
                'last_activity': timestamp,
                'animal_id': animal_id,
                'relay_unit_id': relay_unit_id
            }
            logger.info(f"Started new session for animal {animal_id} at {timestamp}")
    
    def _handle_session_start(self, relay_unit_id, animal_id, timestamp):
        """
        Handle a session start event.
        
        Args:
            relay_unit_id (int): ID of the relay unit.
            animal_id (int): ID of the animal.
            timestamp (float): Timestamp of the event.
        """
        session_key = f"{animal_id}_{relay_unit_id}"
        
        # Just create a session if it doesn't exist
        if session_key not in self.active_sessions:
            self.active_sessions[session_key] = {
                'start_time': timestamp,
                'last_activity': timestamp,
                'animal_id': animal_id,
                'relay_unit_id': relay_unit_id
            }
            logger.info(f"Started new session for animal {animal_id} at {timestamp}")
    
    def _handle_session_end(self, relay_unit_id, animal_id, start_time, end_time, duration_ms):
        """
        Handle a session end event.
        
        Args:
            relay_unit_id (int): ID of the relay unit.
            animal_id (int): ID of the animal.
            start_time (float): Start timestamp of the session.
            end_time (float): End timestamp of the session.
            duration_ms (float): Duration of the session in milliseconds.
        """
        session_key = f"{animal_id}_{relay_unit_id}"
        
        # Remove the session from active sessions
        if session_key in self.active_sessions:
            del self.active_sessions[session_key]
        
        # Convert timestamps to datetime objects
        start_dt = datetime.fromtimestamp(start_time / 1000)
        end_dt = datetime.fromtimestamp(end_time / 1000)
        
        # Calculate volume based on duration (simple estimate)
        estimated_volume = (duration_ms / 1000) * 0.1  # 0.1 ml per second
        
        # Log the session
        logger.info(f"Ended session for animal {animal_id}: duration={duration_ms}ms, volume={estimated_volume:.2f}ml")
        
        # Store in database if available
        if self.database_handler:
            try:
                # Check if the required methods exist
                if hasattr(self.database_handler, 'add_drinking_session'):
                    # Create session record
                    session_id = self.database_handler.add_drinking_session(
                        animal_id, 
                        start_dt.isoformat(),
                        end_dt.isoformat(),
                        duration_ms,
                        estimated_volume
                    )
                    
                    # Also log individual event for more detailed analysis
                    if hasattr(self.database_handler, 'add_drinking_event'):
                        self.database_handler.add_drinking_event(
                            animal_id,
                            start_dt.isoformat(),
                            duration_ms,
                            session_id
                        )
                    
                    logger.info(f"Stored drinking session {session_id} for animal {animal_id}")
                else:
                    logger.warning("Database handler does not support drinking sessions")
            except Exception as e:
                logger.error(f"Error storing drinking session: {e}")
    
    def check_sessions(self):
        """
        Check for timed-out sessions.
        
        This method should be called periodically to end sessions that haven't
        seen activity for a while.
        """
        current_time = time.time() * 1000
        session_timeout = 1000  # 1 second timeout
        
        # Find expired sessions
        expired_sessions = []
        for session_key, session in self.active_sessions.items():
            if (current_time - session['last_activity']) > session_timeout:
                expired_sessions.append(session_key)
        
        # End expired sessions
        for session_key in expired_sessions:
            session = self.active_sessions[session_key]
            duration_ms = session['last_activity'] - session['start_time']
            
            self._handle_session_end(
                session['relay_unit_id'],
                session['animal_id'],
                session['start_time'],
                session['last_activity'],
                duration_ms
            )
    
    def shutdown(self):
        """
        Clean shutdown of the event manager.
        
        This method should be called when shutting down the system to ensure
        all events are processed and all sessions are ended.
        """
        logger.info("Shutting down DrinkEventManager")
        
        # Signal the thread to stop
        self.running = False
        
        # End all active sessions
        current_time = time.time() * 1000
        for session_key, session in list(self.active_sessions.items()):
            duration_ms = current_time - session['start_time']
            
            self._handle_session_end(
                session['relay_unit_id'],
                session['animal_id'],
                session['start_time'],
                current_time,
                duration_ms
            )
        
        # Wait for the thread to finish
        if self.process_thread.is_alive():
            self.process_thread.join(timeout=2.0)
        
        logger.info("DrinkEventManager shutdown complete") 