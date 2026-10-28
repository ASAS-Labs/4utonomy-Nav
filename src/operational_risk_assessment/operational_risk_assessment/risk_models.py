"""Risk assessment models and scoring framework."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
import math


class RiskLevel(Enum):
    """Risk severity levels."""
    NEGLIGIBLE = 0
    LOW = 1
    MODERATE = 2
    HIGH = 3
    CRITICAL = 4


class OperationalStatus(Enum):
    """Autonomous operation status recommendations."""
    SAFE = "SAFE"
    CAUTION = "CAUTION"
    INTERVENTION_ADVISED = "INTERVENTION_ADVISED"
    MANUAL_REQUIRED = "MANUAL_REQUIRED"
    UNSAFE = "UNSAFE"


@dataclass
class RiskFactor:
    """Individual risk factor assessment."""
    name: str
    category: str
    score: float  # 0.0 (no risk) to 1.0 (maximum risk)
    level: RiskLevel
    description: str
    impact: str
    mitigation: Optional[str] = None
    confidence: float = 1.0  # 0.0 to 1.0


@dataclass
class RiskAssessment:
    """Complete operational risk assessment."""
    timestamp: float
    overall_score: float  # 0.0 (no risk) to 1.0 (maximum risk)
    overall_level: RiskLevel
    operational_status: OperationalStatus
    risk_factors: List[RiskFactor]
    recommendations: List[str]
    safe_to_operate: bool


class RiskScorer:
    """Calculate risk scores and levels."""
    
    # Risk level thresholds
    THRESHOLDS = {
        RiskLevel.NEGLIGIBLE: 0.0,
        RiskLevel.LOW: 0.2,
        RiskLevel.MODERATE: 0.4,
        RiskLevel.HIGH: 0.6,
        RiskLevel.CRITICAL: 0.8,
    }
    
    # Operational status mapping
    STATUS_MAPPING = {
        RiskLevel.NEGLIGIBLE: OperationalStatus.SAFE,
        RiskLevel.LOW: OperationalStatus.SAFE,
        RiskLevel.MODERATE: OperationalStatus.CAUTION,
        RiskLevel.HIGH: OperationalStatus.INTERVENTION_ADVISED,
        RiskLevel.CRITICAL: OperationalStatus.MANUAL_REQUIRED,
    }
    
    @staticmethod
    def score_to_level(score: float) -> RiskLevel:
        """Convert numeric score to risk level."""
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
    
    @staticmethod
    def level_to_status(level: RiskLevel) -> OperationalStatus:
        """Map risk level to operational status."""
        return RiskScorer.STATUS_MAPPING.get(level, OperationalStatus.UNSAFE)
    
    @staticmethod
    def aggregate_risks(risk_factors: List[RiskFactor], 
                       weights: Optional[Dict[str, float]] = None) -> float:
        """
        Aggregate multiple risk factors into overall score.
        Uses weighted root mean square for conservative estimation.
        """
        if not risk_factors:
            return 0.0
        
        if weights is None:
            weights = {rf.name: 1.0 for rf in risk_factors}
        
        total_weight = 0.0
        weighted_sum_squares = 0.0
        
        for rf in risk_factors:
            weight = weights.get(rf.name, 1.0) * rf.confidence
            weighted_sum_squares += (rf.score ** 2) * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        # Root mean square for conservative risk estimation
        overall_score = math.sqrt(weighted_sum_squares / total_weight)
        return min(overall_score, 1.0)


class WeatherRiskModel:
    """Weather-based risk assessment model."""
    
    @staticmethod
    def assess_precipitation(rate_mm_per_hour: float) -> RiskFactor:
        """Assess risk from precipitation."""
        # LiDAR performance degrades with rain
        if rate_mm_per_hour >= 10.0:
            score = 0.9
            level = RiskLevel.CRITICAL
            impact = f"Heavy rain ({rate_mm_per_hour:.1f} mm/h): LiDAR range reduced 60-80%"
        elif rate_mm_per_hour >= 5.0:
            score = 0.7
            level = RiskLevel.HIGH
            impact = f"Moderate rain ({rate_mm_per_hour:.1f} mm/h): LiDAR range reduced 40-60%"
        elif rate_mm_per_hour >= 2.0:
            score = 0.4
            level = RiskLevel.MODERATE
            impact = f"Light rain ({rate_mm_per_hour:.1f} mm/h): LiDAR range reduced 20-40%"
        elif rate_mm_per_hour > 0.0:
            score = 0.2
            level = RiskLevel.LOW
            impact = f"Drizzle ({rate_mm_per_hour:.1f} mm/h): Minor LiDAR degradation"
        else:
            score = 0.0
            level = RiskLevel.NEGLIGIBLE
            impact = "No precipitation"
        
        return RiskFactor(
            name="precipitation",
            category="weather",
            score=score,
            level=level,
            description="Precipitation impact on sensors",
            impact=impact,
            mitigation="Reduce speed, increase sensor fusion reliance on cameras/radar"
        )
    
    @staticmethod
    def assess_visibility(visibility_meters: float) -> RiskFactor:
        """Assess risk from reduced visibility (fog, dust, snow)."""
        if visibility_meters < 50:
            score = 0.95
            level = RiskLevel.CRITICAL
            impact = f"Very poor visibility ({visibility_meters}m): All sensors compromised"
        elif visibility_meters < 100:
            score = 0.8
            level = RiskLevel.CRITICAL
            impact = f"Poor visibility ({visibility_meters}m): Severe sensor limitations"
        elif visibility_meters < 200:
            score = 0.6
            level = RiskLevel.HIGH
            impact = f"Reduced visibility ({visibility_meters}m): Limited detection range"
        elif visibility_meters < 500:
            score = 0.3
            level = RiskLevel.MODERATE
            impact = f"Moderate visibility ({visibility_meters}m): Minor sensor constraints"
        else:
            score = 0.0
            level = RiskLevel.NEGLIGIBLE
            impact = f"Good visibility ({visibility_meters}m)"
        
        return RiskFactor(
            name="visibility",
            category="weather",
            score=score,
            level=level,
            description="Atmospheric visibility",
            impact=impact,
            mitigation="Reduce speed, activate hazard lights, consider manual takeover"
        )
    
    @staticmethod
    def assess_wind(wind_speed_kph: float) -> RiskFactor:
        """Assess risk from wind."""
        if wind_speed_kph >= 75:
            score = 0.85
            level = RiskLevel.CRITICAL
            impact = f"Dangerous winds ({wind_speed_kph} km/h): Vehicle stability risk"
        elif wind_speed_kph >= 50:
            score = 0.6
            level = RiskLevel.HIGH
            impact = f"Strong winds ({wind_speed_kph} km/h): Lateral forces affecting control"
        elif wind_speed_kph >= 30:
            score = 0.3
            level = RiskLevel.MODERATE
            impact = f"Moderate winds ({wind_speed_kph} km/h): Minor steering adjustments needed"
        else:
            score = 0.0
            level = RiskLevel.NEGLIGIBLE
            impact = f"Calm to light winds ({wind_speed_kph} km/h)"
        
        return RiskFactor(
            name="wind",
            category="weather",
            score=score,
            level=level,
            description="Wind speed impact",
            impact=impact,
            mitigation="Reduce speed, adjust lateral control gains"
        )


class SensorHealthModel:
    """Sensor health and performance risk model."""
    
    @staticmethod
    def assess_lidar_health(point_return_rate: float, 
                           expected_rate: float = 1.0) -> RiskFactor:
        """Assess LiDAR health based on point return rate."""
        performance = point_return_rate / expected_rate if expected_rate > 0 else 0.0
        
        if performance < 0.3:
            score = 0.95
            level = RiskLevel.CRITICAL
            impact = f"LiDAR severely degraded ({performance*100:.0f}% expected returns)"
        elif performance < 0.5:
            score = 0.7
            level = RiskLevel.HIGH
            impact = f"LiDAR poor performance ({performance*100:.0f}% expected returns)"
        elif performance < 0.7:
            score = 0.4
            level = RiskLevel.MODERATE
            impact = f"LiDAR reduced performance ({performance*100:.0f}% expected returns)"
        elif performance < 0.9:
            score = 0.2
            level = RiskLevel.LOW
            impact = f"LiDAR slight degradation ({performance*100:.0f}% expected returns)"
        else:
            score = 0.0
            level = RiskLevel.NEGLIGIBLE
            impact = f"LiDAR healthy ({performance*100:.0f}% expected returns)"
        
        return RiskFactor(
            name="lidar_health",
            category="sensor",
            score=score,
            level=level,
            description="LiDAR sensor health",
            impact=impact,
            mitigation="Increase camera/radar reliance, reduce speed, manual inspection if critical"
        )
    
    @staticmethod
    def assess_localization_confidence(position_stddev: float) -> RiskFactor:
        """Assess localization uncertainty risk."""
        # Standard deviation in meters
        if position_stddev > 2.0:
            score = 0.9
            level = RiskLevel.CRITICAL
            impact = f"Very poor localization (±{position_stddev:.2f}m uncertainty)"
        elif position_stddev > 1.0:
            score = 0.65
            level = RiskLevel.HIGH
            impact = f"Poor localization (±{position_stddev:.2f}m uncertainty)"
        elif position_stddev > 0.5:
            score = 0.35
            level = RiskLevel.MODERATE
            impact = f"Moderate localization (±{position_stddev:.2f}m uncertainty)"
        elif position_stddev > 0.2:
            score = 0.15
            level = RiskLevel.LOW
            impact = f"Good localization (±{position_stddev:.2f}m uncertainty)"
        else:
            score = 0.0
            level = RiskLevel.NEGLIGIBLE
            impact = f"Excellent localization (±{position_stddev:.2f}m uncertainty)"
        
        return RiskFactor(
            name="localization",
            category="perception",
            score=score,
            level=level,
            description="Position estimation confidence",
            impact=impact,
            mitigation="Slow down, rely on lane keeping, resample particle filter"
        )


class OperationalDomainModel:
    """Operational Design Domain (ODD) compliance risk model."""
    
    @staticmethod
    def assess_speed_appropriateness(current_speed: float,
                                    speed_limit: float,
                                    road_conditions: str = "dry") -> RiskFactor:
        """Assess if speed is appropriate for conditions."""
        # Adjust limits based on conditions
        condition_factors = {
            "dry": 1.0,
            "wet": 0.8,
            "snow": 0.5,
            "ice": 0.3
        }
        safe_speed = speed_limit * condition_factors.get(road_conditions, 1.0)
        
        if current_speed > safe_speed * 1.2:
            score = 0.8
            level = RiskLevel.HIGH
            impact = f"Speed ({current_speed:.0f} km/h) too high for {road_conditions} conditions"
        elif current_speed > safe_speed:
            score = 0.4
            level = RiskLevel.MODERATE
            impact = f"Speed ({current_speed:.0f} km/h) marginally high for conditions"
        else:
            score = 0.0
            level = RiskLevel.NEGLIGIBLE
            impact = f"Speed ({current_speed:.0f} km/h) appropriate"
        
        return RiskFactor(
            name="speed_appropriateness",
            category="operational",
            score=score,
            level=level,
            description="Speed vs conditions assessment",
            impact=impact,
            mitigation="Reduce speed to match conditions"
        )
    
    @staticmethod
    def assess_time_of_day(hour: int, lighting_condition: str = "day") -> RiskFactor:
        """Assess time-of-day and lighting risks."""
        if lighting_condition in ["night", "dark"]:
            if hour >= 22 or hour <= 5:
                score = 0.5
                level = RiskLevel.MODERATE
                impact = "Night operation: reduced camera performance"
            else:
                score = 0.3
                level = RiskLevel.LOW
                impact = "Low light: some camera degradation"
        elif lighting_condition in ["dawn", "dusk"]:
            score = 0.3
            level = RiskLevel.LOW
            impact = "Twilight: challenging lighting conditions"
        else:
            score = 0.0
            level = RiskLevel.NEGLIGIBLE
            impact = "Daylight: optimal visibility"
        
        return RiskFactor(
            name="lighting",
            category="environmental",
            score=score,
            level=level,
            description="Lighting conditions",
            impact=impact,
            mitigation="Increase LiDAR reliance, activate vehicle lights"
        )
