#!/usr/bin/env python3
"""Main Risk Assessment Node - Launches all monitoring components."""

import rclpy
from rclpy.executors import MultiThreadedExecutor
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from weather_risk_monitor import WeatherRiskMonitor
from sensor_health_monitor import SensorHealthMonitor
from operational_domain_monitor import OperationalDomainMonitor
from risk_aggregator import RiskAggregator


def main(args=None):
    """Launch all risk assessment components."""
    rclpy.init(args=args)
    
    # Create all nodes
    weather_monitor = WeatherRiskMonitor()
    sensor_monitor = SensorHealthMonitor()
    operational_monitor = OperationalDomainMonitor()
    aggregator = RiskAggregator()
    
    # Use multi-threaded executor
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(weather_monitor)
    executor.add_node(sensor_monitor)
    executor.add_node(operational_monitor)
    executor.add_node(aggregator)
    
    try:
        print("Operational Risk Assessment System started")
        print("  - Weather Risk Monitor")
        print("  - Sensor Health Monitor")
        print("  - Operational Domain Monitor")
        print("  - Risk Aggregator")
        print("\nPublishing to /risk_assessment/overall")
        executor.spin()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        executor.shutdown()
        weather_monitor.destroy_node()
        sensor_monitor.destroy_node()
        operational_monitor.destroy_node()
        aggregator.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
