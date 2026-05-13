"""
Session detector module for IR sensor events.

This module handles the detection of drinking sessions from raw beam break events,
applying filtering and aggregation to identify meaningful behavioral patterns.
"""

import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SessionDetector:
    """
    Detector for drinking sessions from IR beam break events.
    
    This class applies filtering and aggregation to raw IR beam break events
    to identify meaningful drinking sessions.
    """
    
    def __init__(self, session_timeout_ms=None):
        """
        Initialize the session detector.
        
        Args:
            session_timeout_ms (int, optional): Time after which a session is considered completed.
        """
        self.session_timeout_ms = session_timeout_ms or 1000  # 1 second default
        
        # Session state tracking
        self.active_sessions = {}
        self.completed_sessions = []
        
        logger.info("SessionDetector initialized with timeout: {} ms", self.session_timeout_ms)
    
    def process_event(self, event):
        """
        Process a beam break event.
        
        Args:
            event (dict): Event data including animal_id, timestamp, etc.
            
        Returns:
            dict or None: Session data if a session was completed, None otherwise.
        """
        animal_id = event.get('animal_id')
        relay_unit_id = event.get('relay_unit_id')
        timestamp = event.get('timestamp')
        
        if not animal_id or not relay_unit_id or not timestamp:
            logger.warning("Incomplete event data")
            return None
        
        # Create a unique key for this animal/relay combination
        session_key = f"{animal_id}_{relay_unit_id}"
        
        # Check if a session already exists
        if session_key in self.active_sessions:
            session = self.active_sessions[session_key]
            
            # Check if this is a new session due to timeout
            if (timestamp - session['last_activity']) > self.session_timeout_ms:
                # Complete the previous session
                completed_session = self._complete_session(session_key, session['last_activity'])
                
                # Start a new session
                self.active_sessions[session_key] = {
                    'animal_id': animal_id,
                    'relay_unit_id': relay_unit_id,
                    'start_time': timestamp,
                    'last_activity': timestamp,
                    'events': [timestamp]
                }
                
                return completed_session
            else:
                # Update the existing session
                session['last_activity'] = timestamp
                session['events'].append(timestamp)
                return None
        else:
            # Start a new session
            self.active_sessions[session_key] = {
                'animal_id': animal_id,
                'relay_unit_id': relay_unit_id,
                'start_time': timestamp,
                'last_activity': timestamp,
                'events': [timestamp]
            }
            return None
    
    def _complete_session(self, session_key, end_time):
        """
        Complete a session and add it to the completed sessions list.
        
        Args:
            session_key (str): Key of the session to complete.
            end_time (float): End timestamp for the session.
            
        Returns:
            dict: Completed session data.
        """
        session = self.active_sessions.pop(session_key)
        
        # Calculate session statistics
        duration_ms = end_time - session['start_time']
        events_count = len(session['events'])
        
        # Create a session record
        completed_session = {
            'animal_id': session['animal_id'],
            'relay_unit_id': session['relay_unit_id'],
            'start_time': session['start_time'],
            'end_time': end_time,
            'duration_ms': duration_ms,
            'events_count': events_count
        }
        
        # Add to completed sessions
        self.completed_sessions.append(completed_session)
        
        logger.info(
            f"Completed session for animal {session['animal_id']}: "
            f"duration={duration_ms}ms, events={events_count}"
        )
        
        return completed_session
    
    def check_timeouts(self):
        """
        Check for timed-out sessions and complete them.
        
        Returns:
            list: List of completed sessions.
        """
        current_time = time.time() * 1000
        completed = []
        
        # Find sessions that have timed out
        timed_out_keys = []
        for session_key, session in self.active_sessions.items():
            if (current_time - session['last_activity']) > self.session_timeout_ms:
                timed_out_keys.append(session_key)
        
        # Complete timed out sessions
        for session_key in timed_out_keys:
            session = self.active_sessions[session_key]
            completed_session = self._complete_session(session_key, session['last_activity'])
            completed.append(completed_session)
        
        return completed
    
    def get_completed_sessions(self, clear=False):
        """
        Get the list of completed sessions.
        
        Args:
            clear (bool): Whether to clear the list after returning it.
            
        Returns:
            list: List of completed sessions.
        """
        sessions = self.completed_sessions[:]
        
        if clear:
            self.completed_sessions = []
        
        return sessions
    
    def clear(self):
        """Clear all session data."""
        self.active_sessions = {}
        self.completed_sessions = []
        logger.info("Session detector cleared") 