"""
Data model for drinking events and sessions.

This module provides a data model for drinking events and sessions,
with methods for retrieving and analyzing data for visualization.
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DrinkingDataModel:
    """
    Data model for drinking events and sessions.
    
    This class provides methods for retrieving and analyzing drinking data
    for visualization and analysis.
    """
    
    def __init__(self, database_handler):
        """
        Initialize the drinking data model.
        
        Args:
            database_handler: Database handler for retrieving data.
        """
        self.database_handler = database_handler
        logger.info("DrinkingDataModel initialized")
    
    def get_drinking_data_for_animal(self, animal_id, start_date=None, end_date=None):
        """
        Get drinking data for an animal, optionally within a date range.
        
        Args:
            animal_id (int): ID of the animal.
            start_date (str, optional): Start date in ISO format.
            end_date (str, optional): End date in ISO format.
            
        Returns:
            list: List of drinking sessions for the animal.
        """
        if not hasattr(self.database_handler, 'get_drinking_data_for_animal'):
            logger.warning("Database handler does not support get_drinking_data_for_animal")
            return []
        
        return self.database_handler.get_drinking_data_for_animal(
            animal_id, 
            start_date, 
            end_date
        )
    
    def get_circadian_pattern(self, animal_id, days=7, bin_minutes=5):
        """
        Get circadian drinking pattern for an animal.
        
        Args:
            animal_id (int): ID of the animal.
            days (int): Number of days to include in the analysis.
            bin_minutes (int): Size of time bins in minutes.
            
        Returns:
            dict: Circadian pattern data with time bins and counts.
        """
        if not hasattr(self.database_handler, 'get_circadian_drinking_pattern'):
            logger.warning("Database handler does not support get_circadian_drinking_pattern")
            return {
                'time_bins': [],
                'counts': [],
                'durations': [],
                'volumes': []
            }
        
        return self.database_handler.get_circadian_drinking_pattern(
            animal_id, 
            days, 
            bin_minutes
        )
    
    def get_daily_totals(self, animal_id, days=7):
        """
        Get daily drinking totals for an animal.
        
        Args:
            animal_id (int): ID of the animal.
            days (int): Number of days to include.
            
        Returns:
            dict: Daily totals data with dates and values.
        """
        try:
            # Get raw drinking data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            sessions = self.get_drinking_data_for_animal(
                animal_id,
                start_date.isoformat(),
                end_date.isoformat()
            )
            
            # Process into daily totals
            daily_data = {}
            for session in sessions:
                # Extract date from session start time
                start_time = session[1]  # Assuming index 1 is start_time
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                date_key = start_dt.date().isoformat()
                
                # Get duration and volume
                duration = session[3]  # Assuming index 3 is total_duration_ms
                volume = session[4]    # Assuming index 4 is estimated_volume_ml
                
                # Add to daily totals
                if date_key not in daily_data:
                    daily_data[date_key] = {
                        'total_duration': 0,
                        'total_volume': 0,
                        'count': 0
                    }
                
                daily_data[date_key]['total_duration'] += duration
                daily_data[date_key]['total_volume'] += volume
                daily_data[date_key]['count'] += 1
            
            # Prepare result
            dates = sorted(daily_data.keys())
            result = {
                'dates': dates,
                'volumes': [daily_data[d]['total_volume'] for d in dates],
                'durations': [daily_data[d]['total_duration'] for d in dates],
                'counts': [daily_data[d]['count'] for d in dates]
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting daily totals: {e}")
            return {
                'dates': [],
                'volumes': [],
                'durations': [],
                'counts': []
            }
    
    def compare_animals(self, animal_ids, days=7):
        """
        Compare drinking patterns across multiple animals.
        
        Args:
            animal_ids (list): List of animal IDs to compare.
            days (int): Number of days to include.
            
        Returns:
            dict: Comparison data for the animals.
        """
        result = {
            'animals': {},
            'daily_averages': {}
        }
        
        for animal_id in animal_ids:
            # Get daily totals for this animal
            daily_data = self.get_daily_totals(animal_id, days)
            
            # Calculate averages
            if daily_data['dates']:
                avg_volume = sum(daily_data['volumes']) / len(daily_data['dates'])
                avg_duration = sum(daily_data['durations']) / len(daily_data['dates'])
                avg_count = sum(daily_data['counts']) / len(daily_data['dates'])
            else:
                avg_volume = 0
                avg_duration = 0
                avg_count = 0
            
            # Store results
            result['animals'][animal_id] = daily_data
            result['daily_averages'][animal_id] = {
                'avg_volume': avg_volume,
                'avg_duration': avg_duration,
                'avg_count': avg_count
            }
        
        return result 