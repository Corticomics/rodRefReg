#!/usr/bin/env python3
"""
Valve & Sensor Characterization Test Suite
===========================================

Purpose: Measure actual valve behavior to inform delivery strategy implementation

Tests Performed:
1. Valve response time (opening lag)
2. Valve closing lag 
3. Flow rate during continuous operation
4. Flow rate stability over time
5. Minimum stable pulse width
6. Sensor saturation detection
7. Settling time after valve closure

Best Practices:
- Empirical data drives design decisions
- Multiple measurements for statistical validity
- Clear output format for human analysis
- Safety checks (max open time limits)

Author: System
Date: 2025-10-27
"""

import sys
import time
import json
import statistics
import argparse
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# Add Project directory to path
sys.path.insert(0, '/Users/zes/Documents/GitHub/rodRefReg/Project')

try:
    from drivers.uart_flow_sensor import UARTFlowSensor
    from drivers.solenoid_controller import SolenoidController
    from gpio.gpio_handler import RelayHandler
    from models.relay_unit_manager import RelayUnitManager
    from controllers.system_controller import SystemController
    from models.database_handler import DatabaseHandler
except ImportError as e:
    print(f"ERROR: Failed to import required modules: {e}")
    print("Make sure you're running from the Project directory")
    sys.exit(1)


class ValveCharacterizationTest:
    """
    Comprehensive valve characterization test suite.
    
    Best Practices:
    - Statistical validation (5+ samples per test)
    - Clear result presentation
    - Safety limits (max open time)
    - Error handling
    """
    
    def __init__(self, cage_id: int, sensor_port: str = '/dev/teensy_flow'):
        self.cage_id = cage_id
        self.sensor_port = sensor_port
        self.sensor = None
        self.controller = None
        self.relay_handler = None
        
        # Results storage
        self.results = {
            'cage_id': cage_id,
            'timestamp': datetime.now().isoformat(),
            'tests': {}
        }
    
    def setup(self):
        """Initialize hardware connections."""
        print("\n" + "="*70)
        print("VALVE CHARACTERIZATION TEST SUITE")
        print("="*70)
        print(f"\nCage ID: {self.cage_id}")
        print(f"Sensor Port: {self.sensor_port}")
        print("\nInitializing hardware...")
        
        try:
            # Initialize system controller
            db_handler = DatabaseHandler()
            system_controller = SystemController(db_handler)
            settings = system_controller.settings
            
            # Initialize relay handler
            relay_unit_manager = RelayUnitManager(settings)
            self.relay_handler = RelayHandler(relay_unit_manager, settings['num_hats'])
            
            # Initialize solenoid controller
            master_id = int(settings.get('global_master_relay_id', 16))
            cage_relays = settings.get('cage_relays', {})
            if not cage_relays:
                # Auto-generate sequential mapping
                cage_relays = {str(i): i for i in range(1, 16)}
            
            self.controller = SolenoidController(self.relay_handler, master_id, cage_relays)
            
            # Initialize flow sensor
            # Use 20 Hz instead of 50 Hz to prevent serial buffer overflow
            # at high flow rates (prevents firmware hang)
            self.sensor = UARTFlowSensor(
                port=self.sensor_port,
                sampling_hz=20.0,  # Reduced from 50 Hz
                baud_rate=115200
            )
            self.sensor.start()
            
            print("✓ Hardware initialized successfully")
            time.sleep(2)  # Allow sensor to stabilize
            
            return True
            
        except Exception as e:
            print(f"✗ Hardware initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def cleanup(self):
        """Safely close all hardware connections."""
        print("\nCleaning up...")
        try:
            # Close all valves via controller
            if self.controller:
                try:
                    self.controller.close_master()
                except Exception:
                    pass
                # Close all cage valves (assuming cage_id is valid)
                try:
                    self.controller.close_cage(self.cage_id)
                except Exception:
                    pass
            
            # Stop sensor
            if self.sensor:
                self.sensor.stop()
            
            # Turn off all relays as final safety
            if self.relay_handler:
                self.relay_handler.set_all_relays(0)
            
            print("✓ Cleanup complete")
        except Exception as e:
            print(f"⚠ Cleanup warning: {e}")
    
    def ensure_sensor_streaming(self, timeout_s: float = 5.0) -> bool:
        """
        Ensure sensor is actively streaming measurements.
        
        Best Practices:
        - Fail-fast: Verify streaming before valve operations
        - Clear diagnostics: Report specific failure modes
        
        Returns:
            True if sensor streaming, False otherwise
        """
        print("  Verifying sensor stream...", end=" ", flush=True)
        
        # Clear stale data
        if hasattr(self.sensor, 'clear_queue'):
            self.sensor.clear_queue()
        
        # Wait for fresh measurements
        if hasattr(self.sensor, 'wait_for_frames'):
            if self.sensor.wait_for_frames(min_frames=5, timeout_s=timeout_s):
                print("✓ Streaming")
                return True
            else:
                print("✗ NOT streaming")
                return False
        else:
            # Fallback: try to read a few samples
            samples_received = 0
            start_time = time.perf_counter()
            while (time.perf_counter() - start_time) < timeout_s:
                sample = self.sensor.read_one()
                if sample:
                    samples_received += 1
                    if samples_received >= 3:
                        print("✓ Streaming")
                        return True
                time.sleep(0.02)
            
            print(f"✗ NOT streaming (only {samples_received} samples)")
            return False
    
    def restart_sensor(self) -> bool:
        """
        Stop and restart sensor for clean state between tests.
        
        Best Practices:
        - Idempotent operations: Known-good state for each test
        - Firmware reset: Clear any hung state
        """
        print("  Restarting sensor...", end=" ", flush=True)
        
        try:
            # Stop sensor
            if hasattr(self.sensor, 'stop'):
                self.sensor.stop()
                time.sleep(0.5)
            
            # Restart sensor
            if hasattr(self.sensor, 'start'):
                self.sensor.start()
                time.sleep(1.0)  # Allow firmware to initialize
                print("✓")
                return True
            else:
                print("✗ (no start method)")
                return False
                
        except Exception as e:
            print(f"✗ {e}")
            return False
    
    def read_flow_samples(self, duration_s: float, sample_rate_hz: float = 20.0) -> List[Dict]:
        """
        Read flow sensor samples for specified duration.
        
        Returns list of samples with timestamp and flow rate.
        """
        samples = []
        start_time = time.perf_counter()
        sample_interval = 1.0 / sample_rate_hz
        
        while (time.perf_counter() - start_time) < duration_s:
            try:
                sample = self.sensor.read_one()
                if sample:
                    elapsed = time.perf_counter() - start_time
                    flow_ul_min, temp_c, _ = sample
                    samples.append({
                        'time_s': elapsed,
                        'flow_ul_min': flow_ul_min,
                        'flow_ml_min': flow_ul_min / 1000.0,
                        'temp_c': temp_c
                    })
            except Exception as e:
                print(f"  Warning: Sample read failed: {e}")
            
            time.sleep(sample_interval)
        
        return samples
    
    def test_1_valve_opening_lag(self) -> Dict:
        """
        TEST 1: Measure time from valve open signal to flow detected.
        
        Methodology:
        - Open cage valve with master already open
        - Record time to first significant flow (> 0.1 mL/min)
        - Repeat 5 times for statistical validity
        """
        print("\n" + "-"*70)
        print("TEST 1: Valve Opening Lag Measurement")
        print("-"*70)
        print("Purpose: Measure time from valve open signal to flow detection")
        print("Method: 5 trials, measure time to flow > 0.1 mL/min")
        print()
        
        # Restart sensor for clean state
        if not self.restart_sensor():
            return {'test_name': 'valve_opening_lag', 'success': False, 'error': 'Sensor restart failed'}
        
        # Verify streaming
        if not self.ensure_sensor_streaming():
            return {'test_name': 'valve_opening_lag', 'success': False, 'error': 'Sensor not streaming'}
        
        opening_lags = []
        
        for trial in range(1, 6):
            print(f"Trial {trial}/5:", end=" ", flush=True)
            
            try:
                # Ensure valves closed
                try:
                    self.controller.close_cage(self.cage_id)
                    self.controller.close_master()
                except Exception:
                    pass
                time.sleep(1.0)
                
                # Open master first
                self.controller.open_master()
                time.sleep(0.5)
                
                # Clear sensor queue
                if hasattr(self.sensor, 'clear_queue'):
                    self.sensor.clear_queue()
                
                # Open cage valve and start timing
                start_time = time.perf_counter()
                self.controller.open_cage(self.cage_id)
                
                # Wait for flow to be detected
                flow_detected = False
                timeout_s = 5.0
                threshold_ml_min = 0.1
                
                while (time.perf_counter() - start_time) < timeout_s and not flow_detected:
                    sample = self.sensor.read_one()
                    if sample:
                        flow_ml_min = sample[0] / 1000.0
                        if flow_ml_min > threshold_ml_min:
                            lag_ms = (time.perf_counter() - start_time) * 1000.0
                            opening_lags.append(lag_ms)
                            flow_detected = True
                            print(f"✓ {lag_ms:.1f}ms")
                    time.sleep(0.005)  # 5ms sampling
                
                if not flow_detected:
                    print(f"TIMEOUT (no flow detected after {timeout_s}s)")
                
                # Close valve
                self.controller.close_cage(self.cage_id)
                time.sleep(2.0)  # Wait between trials
                
            except Exception as e:
                print(f"FAILED: {e}")
        
        # Calculate statistics
        if opening_lags:
            result = {
                'test_name': 'valve_opening_lag',
                'unit': 'milliseconds',
                'samples': opening_lags,
                'mean': statistics.mean(opening_lags),
                'stdev': statistics.stdev(opening_lags) if len(opening_lags) > 1 else 0,
                'min': min(opening_lags),
                'max': max(opening_lags),
                'success': True
            }
        else:
            result = {
                'test_name': 'valve_opening_lag',
                'success': False,
                'error': 'No successful measurements'
            }
        
        # Print results (with defensive check for success)
        if result.get('success'):
            print(f"\nResults: {result['mean']:.1f} ± {result['stdev']:.1f}ms (n={len(opening_lags)})")
        else:
            print(f"\n✗ Test failed: {result.get('error', 'Unknown error')}")
        
        self.results['tests']['test_1_opening_lag'] = result
        return result
    
    def test_2_valve_closing_lag(self) -> Dict:
        """
        TEST 2: Measure system equilibrium time (NOT cage delivery cutoff).
        
        CRITICAL NOTE:
        - When cage solenoid closes, flow to cage STOPS IMMEDIATELY
        - Flow sensor continues reading manifold/tubing pressure equalization
        - This test measures SYSTEM SETTLING, not delivery endpoint
        - For delivery strategy: Use TIME-BASED CUTOFF, not flow detection
        
        Methodology:
        - Open cage valve until flow stabilizes
        - Close valve and measure time to flow < 0.05 mL/min
        - Repeat 5 times
        """
        print("\n" + "-"*70)
        print("TEST 2: System Equilibrium Time (NOT Delivery Cutoff)")
        print("-"*70)
        print("Purpose: Measure manifold/tubing settling time after cage close")
        print("Method: 5 trials, measure time to flow < 0.05 mL/min")
        print("⚠ NOTE: Flow after cage close is NOT delivered to cage!")
        print()
        
        # Restart sensor for clean state
        if not self.restart_sensor():
            return {'test_name': 'valve_closing_lag', 'success': False, 'error': 'Sensor restart failed'}
        
        # Verify streaming
        if not self.ensure_sensor_streaming():
            return {'test_name': 'valve_closing_lag', 'success': False, 'error': 'Sensor not streaming'}
        
        closing_lags = []
        
        for trial in range(1, 6):
            print(f"Trial {trial}/5:", end=" ", flush=True)
            
            try:
                # Open valves and wait for stable flow
                self.controller.open_master()
                time.sleep(0.5)
                self.controller.open_cage(self.cage_id)
                time.sleep(1.0)  # Allow flow to stabilize
                
                # Clear sensor queue
                if hasattr(self.sensor, 'clear_queue'):
                    self.sensor.clear_queue()
                
                # Close cage valve and start timing
                start_time = time.perf_counter()
                self.controller.close_cage(self.cage_id)
                
                # Wait for flow to stop
                flow_stopped = False
                timeout_s = 5.0
                threshold_ml_min = 0.05
                
                while (time.perf_counter() - start_time) < timeout_s and not flow_stopped:
                    sample = self.sensor.read_one()
                    if sample:
                        flow_ml_min = abs(sample[0] / 1000.0)  # Use absolute value (handle negative transients)
                        if flow_ml_min < threshold_ml_min:
                            lag_ms = (time.perf_counter() - start_time) * 1000.0
                            closing_lags.append(lag_ms)
                            flow_stopped = True
                            print(f"✓ {lag_ms:.1f}ms")
                    time.sleep(0.005)  # 5ms sampling
                
                if not flow_stopped:
                    print(f"TIMEOUT (flow still detected after {timeout_s}s)")
                
                # Ensure valves closed
                try:
                    self.controller.close_cage(self.cage_id)
                    self.controller.close_master()
                except Exception:
                    pass
                time.sleep(2.0)  # Wait between trials
                
            except Exception as e:
                print(f"✗ FAILED: {e}")
        
        # Calculate statistics
        if closing_lags:
            result = {
                'test_name': 'valve_closing_lag',
                'unit': 'milliseconds',
                'samples': closing_lags,
                'mean': statistics.mean(closing_lags),
                'stdev': statistics.stdev(closing_lags) if len(closing_lags) > 1 else 0,
                'min': min(closing_lags),
                'max': max(closing_lags),
                'success': True
            }
        else:
            result = {
                'test_name': 'valve_closing_lag',
                'success': False,
                'error': 'No successful measurements'
            }
        
        # Print results (with defensive check for success)
        if result.get('success'):
            print(f"\nResults: {result['mean']:.1f} ± {result['stdev']:.1f}ms (n={len(closing_lags)})")
        else:
            print(f"\nTest failed: {result.get('error', 'Unknown error')}")
        
        self.results['tests']['test_2_closing_lag'] = result
        return result
    
    def test_3_continuous_flow_rate(self) -> Dict:
        """
        TEST 3: Measure flow rate during continuous operation.
        
        Methodology:
        - Open valve for 3 seconds
        - Sample flow continuously
        - Calculate mean, std dev, peak
        - Detect sensor saturation (flow = 3.25 mL/min)
        """
        print("\n" + "-"*70)
        print("TEST 3: Continuous Flow Rate Measurement")
        print("-"*70)
        print("Purpose: Measure steady-state flow rate")
        print("Method: 3-second open, sample at 20 Hz")
        print()
        
        # Restart sensor for clean state
        if not self.restart_sensor():
            return {'test_name': 'continuous_flow_rate', 'success': False, 'error': 'Sensor restart failed'}
        
        # Verify streaming
        if not self.ensure_sensor_streaming():
            return {'test_name': 'continuous_flow_rate', 'success': False, 'error': 'Sensor not streaming'}
        
        try:
            # Open valves
            self.controller.open_master()
            time.sleep(0.5)
            
            # Clear sensor queue
            if hasattr(self.sensor, 'clear_queue'):
                self.sensor.clear_queue()
            
            # Open cage valve and start measuring
            self.controller.open_cage(self.cage_id)
            print("Valve opened, measuring for 3 seconds...")
            
            samples = self.read_flow_samples(duration_s=3.0, sample_rate_hz=20.0)
            
            # Close valve
            self.controller.close_cage(self.cage_id)
            self.controller.close_master()
            
            # Analyze samples
            if samples:
                flow_rates_ml_min = [s['flow_ml_min'] for s in samples]
                
                # Detect saturation (sensor reports max value)
                saturated_samples = [f for f in flow_rates_ml_min if f >= 3.2]
                saturation_pct = (len(saturated_samples) / len(flow_rates_ml_min)) * 100
                
                result = {
                    'test_name': 'continuous_flow_rate',
                    'unit': 'mL/min',
                    'duration_s': 3.0,
                    'sample_count': len(samples),
                    'flow_mean': statistics.mean(flow_rates_ml_min),
                    'flow_stdev': statistics.stdev(flow_rates_ml_min) if len(flow_rates_ml_min) > 1 else 0,
                    'flow_min': min(flow_rates_ml_min),
                    'flow_max': max(flow_rates_ml_min),
                    'flow_median': statistics.median(flow_rates_ml_min),
                    'saturated_samples': len(saturated_samples),
                    'saturation_pct': saturation_pct,
                    'sensor_saturated': saturation_pct > 50,
                    'success': True
                }
                
                print(f"\nResults:")
                print(f"  Samples: {result['sample_count']}")
                print(f"  Flow rate: {result['flow_mean']:.3f} ± {result['flow_stdev']:.3f} mL/min")
                print(f"  Range: {result['flow_min']:.3f} - {result['flow_max']:.3f} mL/min")
                print(f"  Saturation: {result['saturation_pct']:.1f}% of samples")
                
                if result['sensor_saturated']:
                    print(f"  ⚠ WARNING: Sensor appears SATURATED (actual flow likely higher!)")
                
            else:
                result = {
                    'test_name': 'continuous_flow_rate',
                    'success': False,
                    'error': 'No samples collected'
                }
                print(f"✗ FAILED: No samples collected")
            
            self.results['tests']['test_3_continuous_flow'] = result
            return result
            
        except Exception as e:
            print(f"✗ FAILED: {e}")
            result = {
                'test_name': 'continuous_flow_rate',
                'success': False,
                'error': str(e)
            }
            self.results['tests']['test_3_continuous_flow'] = result
            return result
    
    def test_4_pulse_width_sweep(self) -> Dict:
        """
        TEST 4: Test multiple pulse widths to find minimum stable width.
        
        Methodology:
        - Test pulse widths: 10ms, 20ms, 50ms, 100ms, 200ms, 500ms
        - For each width: 3 trials
        - Measure volume delivered (integrate flow)
        - Calculate volume per pulse and coefficient of variation
        """
        print("\n" + "-"*70)
        print("TEST 4: Pulse Width Sweep")
        print("-"*70)
        print("Purpose: Find minimum stable pulse width per datasheet")
        print("Method: Test 10ms, 20ms, 50ms, 100ms, 200ms, 500ms (3 trials each)")
        print()
        
        # Restart sensor for clean state
        if not self.restart_sensor():
            return {'test_name': 'pulse_width_sweep', 'success': False, 'error': 'Sensor restart failed'}
        
        # Verify streaming
        if not self.ensure_sensor_streaming():
            return {'test_name': 'pulse_width_sweep', 'success': False, 'error': 'Sensor not streaming'}
        
        pulse_widths_ms = [10, 20, 50, 100, 200, 500]
        pulse_results = {}
        
        for pulse_ms in pulse_widths_ms:
            print(f"\nTesting {pulse_ms}ms pulse width:")
            volumes = []
            
            for trial in range(1, 4):
                print(f"  Trial {trial}/3:", end=" ", flush=True)
                
                try:
                    # Prepare - ensure valves closed
                    try:
                        self.controller.close_cage(self.cage_id)
                        self.controller.close_master()
                    except Exception:
                        pass
                    time.sleep(1.0)
                    self.controller.open_master()
                    time.sleep(0.3)
                    
                    # Clear sensor queue
                    if hasattr(self.sensor, 'clear_queue'):
                        self.sensor.clear_queue()
                    
                    # Execute pulse with flow measurement
                    start_time = time.perf_counter()
                    self.controller.open_cage(self.cage_id)
                    
                    # Measure during pulse + settling
                    samples = []
                    measurement_duration_s = (pulse_ms / 1000.0) + 0.5  # Pulse + 500ms settling
                    
                    while (time.perf_counter() - start_time) < measurement_duration_s:
                        sample = self.sensor.read_one()
                        if sample:
                            elapsed = time.perf_counter() - start_time
                            # Only start integrating after valve opens
                            if elapsed >= (pulse_ms / 1000.0):
                                # This is after valve closed, measuring residual/settling
                                pass
                            samples.append({
                                'time_s': elapsed,
                                'flow_ml_min': sample[0] / 1000.0
                            })
                        
                        # Close valve at specified time
                        if (time.perf_counter() - start_time) >= (pulse_ms / 1000.0):
                            if (time.perf_counter() - start_time) < (pulse_ms / 1000.0) + 0.01:
                                self.controller.close_cage(self.cage_id)
                        
                        time.sleep(0.01)  # 100 Hz sampling
                    
                    # Integrate flow to get volume
                    volume_ml = 0.0
                    for i in range(1, len(samples)):
                        dt_min = (samples[i]['time_s'] - samples[i-1]['time_s']) / 60.0
                        avg_flow = (samples[i]['flow_ml_min'] + samples[i-1]['flow_ml_min']) / 2.0
                        volume_ml += avg_flow * dt_min
                    
                    volumes.append(volume_ml)
                    print(f"✓ {volume_ml:.4f} mL")
                    
                    # Wait between trials
                    try:
                        self.controller.close_cage(self.cage_id)
                        self.controller.close_master()
                    except Exception:
                        pass
                    time.sleep(2.0)
                    
                except Exception as e:
                    print(f"✗ FAILED: {e}")
            
            # Calculate statistics for this pulse width
            if volumes:
                mean_vol = statistics.mean(volumes)
                stdev_vol = statistics.stdev(volumes) if len(volumes) > 1 else 0
                cv_pct = (stdev_vol / mean_vol * 100) if mean_vol > 0 else 999
                
                pulse_results[pulse_ms] = {
                    'pulse_width_ms': pulse_ms,
                    'samples': volumes,
                    'volume_mean_ml': mean_vol,
                    'volume_stdev_ml': stdev_vol,
                    'coefficient_of_variation_pct': cv_pct,
                    'is_stable': cv_pct < 10.0  # Consider stable if CV < 10%
                }
                
                print(f"  Summary: {mean_vol:.4f} ± {stdev_vol:.4f} mL (CV: {cv_pct:.1f}%)")
                if cv_pct < 10.0:
                    print(f"  STABLE (CV < 10%)")
                else:
                    print(f"  UNSTABLE (CV ≥ 10%)")
        
        # Find minimum stable pulse width
        stable_widths = [pw for pw, res in pulse_results.items() if res['is_stable']]
        min_stable_width_ms = min(stable_widths) if stable_widths else None
        
        result = {
            'test_name': 'pulse_width_sweep',
            'pulse_results': pulse_results,
            'min_stable_pulse_width_ms': min_stable_width_ms,
            'success': True
        }
        
        print(f"\n{'='*70}")
        if min_stable_width_ms:
            print(f"Minimum stable pulse width: {min_stable_width_ms}ms")
        else:
            print(f"⚠ WARNING: No stable pulse width found (all CV ≥ 10%)")
        print(f"{'='*70}")
        
        self.results['tests']['test_4_pulse_sweep'] = result
        return result
    
    def test_5_settling_time(self) -> Dict:
        """
        TEST 5: Measure settling time after valve closure.
        
        Methodology:
        - Open valve for 1 second (establish steady flow)
        - Close valve
        - Measure time until flow < 0.01 mL/min (near baseline)
        - Repeat 3 times
        """
        print("\n" + "-"*70)
        print("TEST 5: Flow Settling Time After Valve Closure")
        print("-"*70)
        print("Purpose: Measure time for flow to return to baseline")
        print("Method: 3 trials, measure time to flow < 0.01 mL/min")
        print()
        
        # Restart sensor for clean state
        if not self.restart_sensor():
            return {'test_name': 'settling_time', 'success': False, 'error': 'Sensor restart failed'}
        
        # Verify streaming
        if not self.ensure_sensor_streaming():
            return {'test_name': 'settling_time', 'success': False, 'error': 'Sensor not streaming'}
        
        settling_times = []
        
        for trial in range(1, 4):
            print(f"Trial {trial}/3:", end=" ", flush=True)
            
            try:
                # Open and establish steady flow
                self.controller.open_master()
                time.sleep(0.3)
                self.controller.open_cage(self.cage_id)
                time.sleep(1.0)  # Establish steady flow
                
                # Clear sensor queue
                if hasattr(self.sensor, 'clear_queue'):
                    self.sensor.clear_queue()
                
                # Close valve and measure settling
                start_time = time.perf_counter()
                self.controller.close_cage(self.cage_id)
                
                flow_settled = False
                timeout_s = 10.0
                threshold_ml_min = 0.01
                
                samples = []
                while (time.perf_counter() - start_time) < timeout_s:
                    sample = self.sensor.read_one()
                    if sample:
                        elapsed = time.perf_counter() - start_time
                        flow_ml_min = abs(sample[0] / 1000.0)
                        samples.append({'time_s': elapsed, 'flow_ml_min': flow_ml_min})
                        
                        if flow_ml_min < threshold_ml_min and not flow_settled:
                            settling_ms = elapsed * 1000.0
                            settling_times.append(settling_ms)
                            flow_settled = True
                            print(f"✓ {settling_ms:.1f}ms")
                            break
                    
                    time.sleep(0.01)
                
                if not flow_settled:
                    print(f" TIMEOUT (flow > {threshold_ml_min} mL/min after {timeout_s}s)")
                
                # Cleanup
                try:
                    self.controller.close_cage(self.cage_id)
                    self.controller.close_master()
                except Exception:
                    pass
                time.sleep(2.0)
                
            except Exception as e:
                print(f"✗ FAILED: {e}")
        
        # Calculate statistics
        if settling_times:
            result = {
                'test_name': 'settling_time',
                'unit': 'milliseconds',
                'samples': settling_times,
                'mean': statistics.mean(settling_times),
                'stdev': statistics.stdev(settling_times) if len(settling_times) > 1 else 0,
                'min': min(settling_times),
                'max': max(settling_times),
                'success': True
            }
        else:
            result = {
                'test_name': 'settling_time',
                'success': False,
                'error': 'No successful measurements'
            }
        
        # Print results (with defensive check for success)
        if result.get('success'):
            print(f"\nResults: {result['mean']:.1f} ± {result['stdev']:.1f}ms (n={len(settling_times)})")
        else:
            print(f"\n Test failed: {result.get('error', 'Unknown error')}")
        
        self.results['tests']['test_5_settling_time'] = result
        return result
    
    def run_all_tests(self):
        """Execute complete test suite."""
        if not self.setup():
            print("\n Hardware setup failed - cannot proceed")
            return False
        
        try:
            # Test 1: Opening lag
            self.test_1_valve_opening_lag()
            time.sleep(2)
            
            # Test 2: Closing lag
            self.test_2_valve_closing_lag()
            time.sleep(2)
            
            # Test 3: Continuous flow
            self.test_3_continuous_flow_rate()
            time.sleep(2)
            
            # Test 4: Pulse width sweep
            self.test_4_pulse_width_sweep()
            time.sleep(2)
            
            # Test 5: Settling time
            self.test_5_settling_time()
            
            # Generate summary report
            self.print_summary()
            
            # Save results to file
            self.save_results()
            
            return True
            
        except KeyboardInterrupt:
            print("\n\n Test interrupted by user")
            return False
        except Exception as e:
            print(f"\n Test suite failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.cleanup()
    
    def print_summary(self):
        """Print comprehensive summary of all test results."""
        print("\n\n" + "="*70)
        print("TEST SUITE SUMMARY")
        print("="*70)
        print(f"\nCage ID: {self.results['cage_id']}")
        print(f"Timestamp: {self.results['timestamp']}")
        print("\n" + "-"*70)
        
        # Test 1: Opening lag
        if 'test_1_opening_lag' in self.results['tests']:
            t1 = self.results['tests']['test_1_opening_lag']
            if t1['success']:
                print(f"Opening Lag: {t1['mean']:.1f} ± {t1['stdev']:.1f}ms (n={len(t1['samples'])})")
            else:
                print(f"Opening Lag: FAILED")
        
        # Test 2: Closing lag
        if 'test_2_closing_lag' in self.results['tests']:
            t2 = self.results['tests']['test_2_closing_lag']
            if t2['success']:
                print(f"Closing Lag: {t2['mean']:.1f} ± {t2['stdev']:.1f}ms (n={len(t2['samples'])})")
            else:
                print(f"Closing Lag: FAILED")
        
        # Test 3: Continuous flow
        if 'test_3_continuous_flow' in self.results['tests']:
            t3 = self.results['tests']['test_3_continuous_flow']
            if t3['success']:
                print(f"Continuous Flow: {t3['flow_mean']:.3f} ± {t3['flow_stdev']:.3f} mL/min")
                print(f"  Range: {t3['flow_min']:.3f} - {t3['flow_max']:.3f} mL/min")
                print(f"  Saturation: {t3['saturation_pct']:.1f}%")
                if t3['sensor_saturated']:
                    print(f"  WARNING: Sensor SATURATED (actual flow unknown!)")
            else:
                print(f"Continuous Flow: FAILED")
        
        # Test 4: Pulse width sweep
        if 'test_4_pulse_sweep' in self.results['tests']:
            t4 = self.results['tests']['test_4_pulse_sweep']
            if t4['success']:
                print(f"\nPulse Width Sweep:")
                for pw_ms, res in t4['pulse_results'].items():
                    stable_mark = "✓" if res['is_stable'] else "✗"
                    print(f"  {pw_ms:4d}ms: {res['volume_mean_ml']:.4f} mL (CV: {res['coefficient_of_variation_pct']:.1f}%) {stable_mark}")
                
                if t4['min_stable_pulse_width_ms']:
                    print(f"\n  → Minimum stable: {t4['min_stable_pulse_width_ms']}ms")
                else:
                    print(f"\n  → No stable pulse width found!")
        
        # Test 5: Settling time
        if 'test_5_settling_time' in self.results['tests']:
            t5 = self.results['tests']['test_5_settling_time']
            if t5['success']:
                print(f"\nSettling Time: {t5['mean']:.1f} ± {t5['stdev']:.1f}ms (n={len(t5['samples'])})")
            else:
                print(f"\nSettling Time: FAILED")
        
        print("\n" + "="*70)
    
    def save_results(self):
        """Save results to JSON file."""
        filename = f"valve_characterization_cage{self.cage_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(filename, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"\n✓ Results saved to: {filename}")
        except Exception as e:
            print(f"\n⚠ Failed to save results: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Valve & Sensor Characterization Test Suite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test cage 15 (default)
  python3 test_valve_characterization.py
  
  # Test cage 1
  python3 test_valve_characterization.py --cage 1
  
  # Custom sensor port
  python3 test_valve_characterization.py --cage 15 --port /dev/ttyACM0

Output:
  - Terminal: Real-time test progress and summary
  - JSON file: Complete results saved to valve_characterization_cageX_TIMESTAMP.json
        """
    )
    
    parser.add_argument(
        '--cage',
        type=int,
        default=15,
        help='Cage ID to test (default: 15)'
    )
    
    parser.add_argument(
        '--port',
        type=str,
        default='/dev/teensy_flow',
        help='Sensor serial port (default: /dev/teensy_flow)'
    )
    
    args = parser.parse_args()
    
    # Run tests
    tester = ValveCharacterizationTest(cage_id=args.cage, sensor_port=args.port)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

