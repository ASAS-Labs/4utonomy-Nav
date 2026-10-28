#!/usr/bin/env python3
"""Weather Risk Monitor - Monitors weather conditions and assesses risk."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from operational_risk_assessment.risk_models import WeatherRiskModel, RiskFactor


class WeatherRiskMonitor(Node):
    """Monitors weather conditions and publishes risk assessments."""
    
    def __init__(self):
        super().__init__('weather_risk_monitor')
        
        # Publishers
        self.risk_pub = self.create_publisher(
            DiagnosticArray,
            '/risk_assessment/weather',
            10
        )
        
        # Subscribers for weather data
        self.create_subscription(
            Float32,
            '/weather/precipitation_rate',
            self.precipitation_callback,
            10
        )
        self.create_subscription(
            Float32,
            '/weather/visibility',
            self.visibility_callback,
            10
        )
        self.create_subscription(
            Float32,
            '/weather/wind_speed',
            self.wind_callback,
            10
        )
        
        # State
        self.precipitation_rate = 0.0  # mm/h
        self.visibility = 10000.0  # meters (default: excellent)
        self.wind_speed = 0.0  # km/h
        
        # Parameters
        self.declare_parameter('update_rate', 1.0)
        update_rate = self.get_parameter('update_rate').value
        
        # Timer for periodic assessment
        self.create_timer(1.0 / update_rate, self.assess_and_publish)
        
        self.get_logger().info('Weather Risk Monitor initialized')
    
    def precipitation_callback(self, msg: Float32):
        """Update precipitation rate."""
        self.precipitation_rate = msg.data
    
    def visibility_callback(self, msg: Float32):
        """Update visibility."""
        self.visibility = msg.data
    
    def wind_callback(self, msg: Float32):
        """Update wind speed."""
        self.wind_speed = msg.data
    
    def assess_and_publish(self):
        """Assess weather risks and publish."""
        # Assess individual weather factors
        precip_risk = WeatherRiskModel.assess_precipitation(self.precipitation_rate)
        visibility_risk = WeatherRiskModel.assess_visibility(self.visibility)
        wind_risk = WeatherRiskModel.assess_wind(self.wind_speed)
        
        # Create diagnostic message
        msg = DiagnosticArray()
        msg.header.stamp = self.get_clock().now().to_msg()
        
        # Add each risk factor as a diagnostic status
        for risk_factor in [precip_risk, visibility_risk, wind_risk]:
            status = self._risk_to_diagnostic(risk_factor)
            msg.status.append(status)
        
        self.risk_pub.publish(msg)
    
    def _risk_to_diagnostic(self, risk_factor: RiskFactor) -> DiagnosticStatus:
        """Convert RiskFactor to DiagnosticStatus."""
        status = DiagnosticStatus()
        status.name = f"weather/{risk_factor.name}"
        status.hardware_id = "weather_monitor"
        
        # Map risk level to diagnostic level
        level_map = {
            0: DiagnosticStatus.OK,      # NEGLIGIBLE
            1: DiagnosticStatus.OK,      # LOW
            2: DiagnosticStatus.WARN,    # MODERATE
            3: DiagnosticStatus.ERROR,   # HIGH
            4: DiagnosticStatus.ERROR,   # CRITICAL
        }
        status.level = level_map.get(risk_factor.level.value, DiagnosticStatus.STALE)
        status.message = risk_factor.impact
        
        # Add detailed values
        status.values = [
            KeyValue(key="score", value=f"{risk_factor.score:.3f}"),
            KeyValue(key="level", value=risk_factor.level.name),
            KeyValue(key="category", value=risk_factor.category),
            KeyValue(key="confidence", value=f"{risk_factor.confidence:.3f}"),
            KeyValue(key="mitigation", value=risk_factor.mitigation or "None")
        ]
        
        return status


def main(args=None):
    rclpy.init(args=args)
    node = WeatherRiskMonitor()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
