#!/usr/bin/env python3
"""Sensor Health Monitor - Monitors sensor performance and health."""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Odometry
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from operational_risk_assessment.risk_models import SensorHealthModel, RiskFactor


class SensorHealthMonitor(Node):
    """Monitors sensor health and publishes risk assessments."""
    
    def __init__(self):
        super().__init__('sensor_health_monitor')
        
        # Publishers
        self.risk_pub = self.create_publisher(
            DiagnosticArray,
            '/risk_assessment/sensors',
            10
        )
        
        # Subscribers
        self.create_subscription(
            PointCloud2,
            '/ouster/points',
            self.pointcloud_callback,
            10
        )
        self.create_subscription(
            Odometry,
            '/localization/odometry',
            self.localization_callback,
            10
        )
        
        # State
        self.lidar_point_count = 0
        self.expected_points = 65536  # Typical for Ouster OS1-64
        self.position_stddev = 0.1  # meters
        self.last_pointcloud_time = None
        self.last_localization_time = None
        
        # Moving averages
        self.point_count_history = []
        self.history_size = 10
        
        # Parameters
        self.declare_parameter('update_rate', 2.0)
        self.declare_parameter('expected_points', 65536)
        self.declare_parameter('stale_threshold_sec', 2.0)
        
        update_rate = self.get_parameter('update_rate').value
        self.expected_points = self.get_parameter('expected_points').value
        self.stale_threshold = self.get_parameter('stale_threshold_sec').value
        
        # Timer
        self.create_timer(1.0 / update_rate, self.assess_and_publish)
        
        self.get_logger().info('Sensor Health Monitor initialized')
    
    def pointcloud_callback(self, msg: PointCloud2):
        """Process incoming point cloud data."""
        # Estimate point count from message size
        point_step = msg.point_step
        if point_step > 0:
            self.lidar_point_count = len(msg.data) // point_step
            self.point_count_history.append(self.lidar_point_count)
            
            if len(self.point_count_history) > self.history_size:
                self.point_count_history.pop(0)
        
        self.last_pointcloud_time = self.get_clock().now()
    
    def localization_callback(self, msg: Odometry):
        """Process localization data."""
        # Extract position covariance
        cov = msg.pose.covariance
        # Assuming covariance is [x, y, z, roll, pitch, yaw]
        # Take 2D position uncertainty (x, y)
        var_x = cov[0]  # variance in x
        var_y = cov[7]  # variance in y
        
        # Combined standard deviation
        self.position_stddev = np.sqrt((var_x + var_y) / 2.0)
        self.last_localization_time = self.get_clock().now()
    
    def assess_and_publish(self):
        """Assess sensor health and publish."""
        current_time = self.get_clock().now()
        risk_factors = []
        
        # Check LiDAR health
        if self.last_pointcloud_time is not None:
            age_sec = (current_time - self.last_pointcloud_time).nanoseconds / 1e9
            
            if age_sec > self.stale_threshold:
                # LiDAR data is stale
                lidar_risk = RiskFactor(
                    name="lidar_stale",
                    category="sensor",
                    score=0.95,
                    level=self.get_risk_level(0.95),
                    description="LiDAR data staleness",
                    impact=f"No LiDAR data for {age_sec:.1f}s",
                    mitigation="Check sensor connection and power",
                    confidence=1.0
                )
            else:
                # Assess based on point return rate
                avg_points = np.mean(self.point_count_history) if self.point_count_history else 0
                return_rate = avg_points / self.expected_points if self.expected_points > 0 else 0
                lidar_risk = SensorHealthModel.assess_lidar_health(
                    return_rate,
                    expected_rate=1.0
                )
        else:
            # No LiDAR data received yet
            lidar_risk = RiskFactor(
                name="lidar_no_data",
                category="sensor",
                score=1.0,
                level=self.get_risk_level(1.0),
                description="LiDAR no data",
                impact="No LiDAR data received",
                mitigation="Check sensor connection and drivers",
                confidence=1.0
            )
        
        risk_factors.append(lidar_risk)
        
        # Check localization health
        if self.last_localization_time is not None:
            age_sec = (current_time - self.last_localization_time).nanoseconds / 1e9
            
            if age_sec > self.stale_threshold:
                loc_risk = RiskFactor(
                    name="localization_stale",
                    category="perception",
                    score=0.9,
                    level=self.get_risk_level(0.9),
                    description="Localization data staleness",
                    impact=f"No localization for {age_sec:.1f}s",
                    mitigation="Check localization system",
                    confidence=1.0
                )
            else:
                loc_risk = SensorHealthModel.assess_localization_confidence(
                    self.position_stddev
                )
        else:
            loc_risk = RiskFactor(
                name="localization_no_data",
                category="perception",
                score=1.0,
                level=self.get_risk_level(1.0),
                description="Localization no data",
                impact="No localization data received",
                mitigation="Check localization system initialization",
                confidence=1.0
            )
        
        risk_factors.append(loc_risk)
        
        # Create and publish diagnostic message
        msg = DiagnosticArray()
        msg.header.stamp = self.get_clock().now().to_msg()
        
        for risk_factor in risk_factors:
            status = self._risk_to_diagnostic(risk_factor)
            msg.status.append(status)
        
        self.risk_pub.publish(msg)
    
    def get_risk_level(self, score):
        """Convert score to RiskLevel enum."""
        from operational_risk_assessment.risk_models import RiskLevel
        if score >= 0.8:
            return RiskLevel.CRITICAL
        elif score >= 0.6:
            return RiskLevel.HIGH
        elif score >= 0.4:
            return RiskLevel.MODERATE
        elif score >= 0.2:
            return RiskLevel.LOW
        else:
            return RiskLevel.NEGLIGIBLE
    
    def _risk_to_diagnostic(self, risk_factor: RiskFactor) -> DiagnosticStatus:
        """Convert RiskFactor to DiagnosticStatus."""
        status = DiagnosticStatus()
        status.name = f"sensor/{risk_factor.name}"
        status.hardware_id = "sensor_monitor"
        
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
    node = SensorHealthMonitor()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
