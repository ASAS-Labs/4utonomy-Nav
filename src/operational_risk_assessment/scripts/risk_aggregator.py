#!/usr/bin/env python3
"""Risk Aggregator - Combines all risk factors into overall assessment."""

import rclpy
from rclpy.node import Node
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from std_msgs.msg import String
import json
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from operational_risk_assessment.risk_models import (
    RiskFactor, RiskAssessment, RiskScorer, RiskLevel, OperationalStatus
)


class RiskAggregator(Node):
    """Aggregates all risk factors into comprehensive assessment."""
    
    def __init__(self):
        super().__init__('risk_aggregator')
        
        # Publishers
        self.assessment_pub = self.create_publisher(
            String,
            '/risk_assessment/overall',
            10
        )
        self.diagnostics_pub = self.create_publisher(
            DiagnosticArray,
            '/risk_assessment/diagnostics',
            10
        )
        
        # Subscribers for all risk categories
        self.create_subscription(
            DiagnosticArray,
            '/risk_assessment/weather',
            self.weather_callback,
            10
        )
        self.create_subscription(
            DiagnosticArray,
            '/risk_assessment/sensors',
            self.sensors_callback,
            10
        )
        self.create_subscription(
            DiagnosticArray,
            '/risk_assessment/operational',
            self.operational_callback,
            10
        )
        
        # State - store latest risk factors
        self.risk_factors: Dict[str, RiskFactor] = {}
        
        # Risk weights for aggregation
        self.risk_weights = {
            # Weather risks
            "weather/precipitation": 1.5,
            "weather/visibility": 2.0,
            "weather/wind": 1.0,
            # Sensor risks
            "sensor/lidar_health": 2.0,
            "sensor/lidar_stale": 2.5,
            "sensor/lidar_no_data": 3.0,
            "sensor/localization": 2.5,
            "sensor/localization_stale": 2.5,
            "sensor/localization_no_data": 3.0,
            # Operational risks
            "operational/speed_appropriateness": 1.5,
            "operational/lighting": 1.0,
        }
        
        # Parameters
        self.declare_parameter('update_rate', 5.0)
        self.declare_parameter('safe_threshold', 0.4)
        
        update_rate = self.get_parameter('update_rate').value
        self.safe_threshold = self.get_parameter('safe_threshold').value
        
        # Timer for aggregation
        self.create_timer(1.0 / update_rate, self.aggregate_and_publish)
        
        self.get_logger().info('Risk Aggregator initialized')
    
    def weather_callback(self, msg: DiagnosticArray):
        """Update weather risk factors."""
        self._update_risks_from_diagnostics(msg)
    
    def sensors_callback(self, msg: DiagnosticArray):
        """Update sensor risk factors."""
        self._update_risks_from_diagnostics(msg)
    
    def operational_callback(self, msg: DiagnosticArray):
        """Update operational risk factors."""
        self._update_risks_from_diagnostics(msg)
    
    def _update_risks_from_diagnostics(self, msg: DiagnosticArray):
        """Convert diagnostic messages back to risk factors."""
        for status in msg.status:
            risk_factor = self._diagnostic_to_risk(status)
            self.risk_factors[status.name] = risk_factor
    
    def _diagnostic_to_risk(self, status: DiagnosticStatus) -> RiskFactor:
        """Convert DiagnosticStatus to RiskFactor."""
        # Extract values from key-value pairs
        values = {kv.key: kv.value for kv in status.values}
        
        score = float(values.get("score", 0.0))
        level_name = values.get("level", "NEGLIGIBLE")
        category = values.get("category", "unknown")
        confidence = float(values.get("confidence", 1.0))
        mitigation = values.get("mitigation", "None")
        
        # Convert level name to enum
        level = RiskLevel[level_name]
        
        # Extract name from status.name (format: "category/name")
        name = status.name.split('/')[-1] if '/' in status.name else status.name
        
        return RiskFactor(
            name=name,
            category=category,
            score=score,
            level=level,
            description=status.name,
            impact=status.message,
            mitigation=mitigation if mitigation != "None" else None,
            confidence=confidence
        )
    
    def aggregate_and_publish(self):
        """Aggregate all risks and publish overall assessment."""
        if not self.risk_factors:
            self.get_logger().warn('No risk factors available yet', throttle_duration_sec=5.0)
            return
        
        # Get all current risk factors
        risk_list = list(self.risk_factors.values())
        
        # Aggregate using weighted scoring
        weights = {rf.description: self.risk_weights.get(rf.description, 1.0) 
                  for rf in risk_list}
        
        overall_score = RiskScorer.aggregate_risks(risk_list, weights)
        overall_level = RiskScorer.score_to_level(overall_score)
        operational_status = RiskScorer.level_to_status(overall_level)
        
        # Determine if safe to operate
        safe_to_operate = overall_score < self.safe_threshold
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            risk_list, overall_level, operational_status
        )
        
        # Create assessment
        assessment = RiskAssessment(
            timestamp=self.get_clock().now().nanoseconds / 1e9,
            overall_score=overall_score,
            overall_level=overall_level,
            operational_status=operational_status,
            risk_factors=risk_list,
            recommendations=recommendations,
            safe_to_operate=safe_to_operate
        )
        
        # Publish as JSON
        assessment_json = self._assessment_to_json(assessment)
        msg = String()
        msg.data = assessment_json
        self.assessment_pub.publish(msg)
        
        # Also publish as diagnostics for visualization
        self._publish_diagnostics(assessment)
        
        # Log critical situations
        if overall_level.value >= RiskLevel.HIGH.value:
            self.get_logger().warn(
                f"HIGH RISK: {operational_status.value} - Score: {overall_score:.3f}",
                throttle_duration_sec=2.0
            )
    
    def _generate_recommendations(self, risk_factors: List[RiskFactor],
                                 level: RiskLevel,
                                 status: OperationalStatus) -> List[str]:
        """Generate actionable recommendations based on risk assessment."""
        recommendations = []
        
        # Status-based recommendations
        if status == OperationalStatus.MANUAL_REQUIRED:
            recommendations.append("⚠️ MANUAL CONTROL REQUIRED - Autonomous operation unsafe")
        elif status == OperationalStatus.INTERVENTION_ADVISED:
            recommendations.append("⚠️ Prepare for manual intervention - High risk detected")
        elif status == OperationalStatus.CAUTION:
            recommendations.append("⚠️ Continue with caution - Moderate risk present")
        
        # Factor-specific recommendations (only high-impact ones)
        high_risk_factors = [rf for rf in risk_factors 
                            if rf.level.value >= RiskLevel.MODERATE.value]
        
        for rf in sorted(high_risk_factors, key=lambda x: x.score, reverse=True)[:3]:
            if rf.mitigation:
                recommendations.append(f"• {rf.category.upper()}: {rf.mitigation}")
        
        # Generic safety recommendations
        if level.value >= RiskLevel.HIGH.value:
            recommendations.append("• Reduce speed immediately")
            recommendations.append("• Increase following distance")
            recommendations.append("• Activate hazard indicators")
        
        return recommendations
    
    def _assessment_to_json(self, assessment: RiskAssessment) -> str:
        """Convert assessment to JSON string."""
        data = {
            "timestamp": assessment.timestamp,
            "overall_score": round(assessment.overall_score, 3),
            "overall_level": assessment.overall_level.name,
            "operational_status": assessment.operational_status.value,
            "safe_to_operate": assessment.safe_to_operate,
            "risk_factors": [
                {
                    "name": rf.name,
                    "category": rf.category,
                    "score": round(rf.score, 3),
                    "level": rf.level.name,
                    "impact": rf.impact,
                    "mitigation": rf.mitigation
                }
                for rf in assessment.risk_factors
            ],
            "recommendations": assessment.recommendations
        }
        return json.dumps(data, indent=2)
    
    def _publish_diagnostics(self, assessment: RiskAssessment):
        """Publish overall assessment as diagnostics."""
        msg = DiagnosticArray()
        msg.header.stamp = self.get_clock().now().to_msg()
        
        status = DiagnosticStatus()
        status.name = "risk_assessment/overall"
        status.hardware_id = "risk_aggregator"
        
        # Map to diagnostic level
        if assessment.overall_level.value >= RiskLevel.HIGH.value:
            status.level = DiagnosticStatus.ERROR
        elif assessment.overall_level.value >= RiskLevel.MODERATE.value:
            status.level = DiagnosticStatus.WARN
        else:
            status.level = DiagnosticStatus.OK
        
        status.message = f"{assessment.operational_status.value} (Score: {assessment.overall_score:.3f})"
        
        status.values = [
            KeyValue(key="overall_score", value=f"{assessment.overall_score:.3f}"),
            KeyValue(key="overall_level", value=assessment.overall_level.name),
            KeyValue(key="operational_status", value=assessment.operational_status.value),
            KeyValue(key="safe_to_operate", value=str(assessment.safe_to_operate)),
            KeyValue(key="num_risk_factors", value=str(len(assessment.risk_factors))),
            KeyValue(key="recommendations", value="; ".join(assessment.recommendations[:3]))
        ]
        
        msg.status.append(status)
        self.diagnostics_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = RiskAggregator()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
