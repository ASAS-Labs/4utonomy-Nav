#!/usr/bin/env python3
"""Operational Domain Monitor - Monitors ODD compliance and operational conditions."""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import Float32, String
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from operational_risk_assessment.risk_models import OperationalDomainModel, RiskFactor


class OperationalDomainMonitor(Node):
    """Monitors operational domain compliance."""
    
    def __init__(self):
        super().__init__('operational_domain_monitor')
        
        # Publishers
        self.risk_pub = self.create_publisher(
            DiagnosticArray,
            '/risk_assessment/operational',
            10
        )
        
        # Subscribers
        self.create_subscription(
            TwistStamped,
            '/vehicle/velocity',
            self.velocity_callback,
            10
        )
        self.create_subscription(
            Float32,
            '/vehicle/speed_limit',
            self.speed_limit_callback,
            10
        )
        self.create_subscription(
            String,
            '/road/conditions',
            self.road_conditions_callback,
            10
        )
        
        # State
        self.current_speed = 0.0  # km/h
        self.speed_limit = 50.0  # km/h (default)
        self.road_conditions = "dry"
        
        # Parameters
        self.declare_parameter('update_rate', 2.0)
        update_rate = self.get_parameter('update_rate').value
        
        # Timer
        self.create_timer(1.0 / update_rate, self.assess_and_publish)
        
        self.get_logger().info('Operational Domain Monitor initialized')
    
    def velocity_callback(self, msg: TwistStamped):
        """Update current velocity."""
        # Convert m/s to km/h
        speed_ms = (msg.twist.linear.x ** 2 + msg.twist.linear.y ** 2) ** 0.5
        self.current_speed = speed_ms * 3.6
    
    def speed_limit_callback(self, msg: Float32):
        """Update speed limit."""
        self.speed_limit = msg.data
    
    def road_conditions_callback(self, msg: String):
        """Update road conditions."""
        self.road_conditions = msg.data
    
    def assess_and_publish(self):
        """Assess operational domain compliance."""
        risk_factors = []
        
        # Speed appropriateness
        speed_risk = OperationalDomainModel.assess_speed_appropriateness(
            self.current_speed,
            self.speed_limit,
            self.road_conditions
        )
        risk_factors.append(speed_risk)
        
        # Time of day / lighting
        now = datetime.now()
        hour = now.hour
        
        # Simple lighting model based on time
        if 6 <= hour < 18:
            lighting = "day"
        elif 18 <= hour < 20 or 5 <= hour < 6:
            lighting = "dusk"
        else:
            lighting = "night"
        
        lighting_risk = OperationalDomainModel.assess_time_of_day(hour, lighting)
        risk_factors.append(lighting_risk)
        
        # Create diagnostic message
        msg = DiagnosticArray()
        msg.header.stamp = self.get_clock().now().to_msg()
        
        for risk_factor in risk_factors:
            status = self._risk_to_diagnostic(risk_factor)
            msg.status.append(status)
        
        self.risk_pub.publish(msg)
    
    def _risk_to_diagnostic(self, risk_factor: RiskFactor) -> DiagnosticStatus:
        """Convert RiskFactor to DiagnosticStatus."""
        status = DiagnosticStatus()
        status.name = f"operational/{risk_factor.name}"
        status.hardware_id = "operational_monitor"
        
        level_map = {
            0: DiagnosticStatus.OK,
            1: DiagnosticStatus.OK,
            2: DiagnosticStatus.WARN,
            3: DiagnosticStatus.ERROR,
            4: DiagnosticStatus.ERROR,
        }
        status.level = level_map.get(risk_factor.level.value, DiagnosticStatus.STALE)
        status.message = risk_factor.impact
        
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
    node = OperationalDomainMonitor()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
