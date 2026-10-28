# Operational Risk Assessment System

> **4utonomy by ASAS Labs** - Production autonomous vehicle safety system (2026)  
> This is a current production implementation, distinct from the historical "buggy" proposal.

A comprehensive real-time risk assessment system for autonomous vehicles, monitoring weather, sensor health, and operational domain compliance.

## Overview

The Operational Risk Assessment (ORA) system provides continuous monitoring and evaluation of risk factors affecting autonomous vehicle operations. It aggregates multiple risk sources into a unified safety score and operational status recommendation.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Operational Risk Assessment System              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Weather    │  │    Sensor    │  │ Operational  │     │
│  │     Risk     │  │    Health    │  │    Domain    │     │
│  │   Monitor    │  │   Monitor    │  │   Monitor    │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │             │
│         └──────────────────┼──────────────────┘             │
│                            │                                │
│                     ┌──────▼───────┐                        │
│                     │     Risk     │                        │
│                     │  Aggregator  │                        │
│                     └──────┬───────┘                        │
│                            │                                │
│                    ┌───────▼────────┐                       │
│                    │  Overall Risk  │                       │
│                    │  Assessment    │                       │
│                    └────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Weather Risk Monitor
Monitors environmental weather conditions and assesses their impact on autonomous operations.

**Risk Factors:**
- **Precipitation**: Rain/snow impact on LiDAR performance
- **Visibility**: Fog, dust, or atmospheric conditions
- **Wind**: Vehicle stability and control challenges

**Input Topics:**
- `/weather/precipitation_rate` (Float32) - mm/hour
- `/weather/visibility` (Float32) - meters
- `/weather/wind_speed` (Float32) - km/h

**Output:**
- `/risk_assessment/weather` (DiagnosticArray)

### 2. Sensor Health Monitor
Monitors sensor performance and reliability.

**Risk Factors:**
- **LiDAR Health**: Point return rate vs expected
- **Localization Confidence**: Position uncertainty
- **Data Staleness**: Sensor data freshness

**Input Topics:**
- `/ouster/points` (PointCloud2)
- `/localization/odometry` (Odometry)

**Output:**
- `/risk_assessment/sensors` (DiagnosticArray)

### 3. Operational Domain Monitor
Monitors operational conditions and ODD compliance.

**Risk Factors:**
- **Speed Appropriateness**: Speed vs conditions
- **Lighting Conditions**: Time of day / visibility
- **Road Conditions**: Surface state (dry/wet/snow/ice)

**Input Topics:**
- `/vehicle/velocity` (TwistStamped)
- `/vehicle/speed_limit` (Float32)
- `/road/conditions` (String)

**Output:**
- `/risk_assessment/operational` (DiagnosticArray)

### 4. Risk Aggregator
Combines all risk factors into overall assessment.

**Aggregation Method:**
- Weighted root mean square (conservative)
- Configurable risk weights
- Confidence-weighted scoring

**Output Topics:**
- `/risk_assessment/overall` (String/JSON)
- `/risk_assessment/diagnostics` (DiagnosticArray)

## Risk Levels

| Level | Score Range | Operational Status | Action |
|-------|-------------|-------------------|--------|
| **NEGLIGIBLE** | 0.0 - 0.2 | SAFE | Normal autonomous operation |
| **LOW** | 0.2 - 0.4 | SAFE | Continue with monitoring |
| **MODERATE** | 0.4 - 0.6 | CAUTION | Heightened awareness |
| **HIGH** | 0.6 - 0.8 | INTERVENTION_ADVISED | Prepare for takeover |
| **CRITICAL** | 0.8 - 1.0 | MANUAL_REQUIRED | Immediate intervention |

## Installation

### Prerequisites
- ROS 2 (Humble or later)
- Python 3.8+
- NumPy

### Build
```bash
cd ~/autoware_ws
colcon build --packages-select operational_risk_assessment
source install/setup.bash
```

## Usage

### Launch Complete System
```bash
ros2 launch operational_risk_assessment risk_assessment.launch.py
```

### Launch with Custom Parameters
```bash
ros2 launch operational_risk_assessment risk_assessment.launch.py \
  update_rate:=5.0 \
  safe_threshold:=0.35
```

### Monitor Overall Risk Assessment
```bash
# JSON output
ros2 topic echo /risk_assessment/overall

# Diagnostics format
ros2 topic echo /risk_assessment/diagnostics
```

### Monitor Individual Risk Categories
```bash
ros2 topic echo /risk_assessment/weather
ros2 topic echo /risk_assessment/sensors
ros2 topic echo /risk_assessment/operational
```

## Output Format

### Overall Assessment (JSON)
```json
{
  "timestamp": 1698432000.123,
  "overall_score": 0.456,
  "overall_level": "MODERATE",
  "operational_status": "CAUTION",
  "safe_to_operate": false,
  "risk_factors": [
    {
      "name": "precipitation",
      "category": "weather",
      "score": 0.4,
      "level": "MODERATE",
      "impact": "Light rain (3.5 mm/h): LiDAR range reduced 20-40%",
      "mitigation": "Reduce speed, increase sensor fusion reliance on cameras/radar"
    }
  ],
  "recommendations": [
    "⚠️ Continue with caution - Moderate risk present",
    "• WEATHER: Reduce speed, increase sensor fusion reliance on cameras/radar",
    "• SENSOR: Increase camera/radar reliance, reduce speed, manual inspection if critical"
  ]
}
```

## Configuration

### Risk Weights
Edit `config/risk_weights.yaml` to adjust the relative importance of each risk factor:

```yaml
risk_aggregator:
  ros__parameters:
    weather/precipitation: 1.5
    weather/visibility: 2.0      # Higher = more important
    sensor/lidar_health: 2.0
    safe_threshold: 0.4          # Overall score threshold
```

### Integration with Weather APIs

To integrate with Google Weather API or other sources:

1. Create a weather data bridge node that publishes to the expected topics
2. Map API responses to ROS messages:

```python
# Example weather bridge
class WeatherAPIBridge(Node):
    def __init__(self):
        super().__init__('weather_api_bridge')
        
        # Publishers
        self.precip_pub = self.create_publisher(Float32, '/weather/precipitation_rate', 10)
        self.vis_pub = self.create_publisher(Float32, '/weather/visibility', 10)
        self.wind_pub = self.create_publisher(Float32, '/weather/wind_speed', 10)
        
        # Fetch from Google Weather API
        self.create_timer(30.0, self.fetch_and_publish)  # Update every 30s
    
    def fetch_and_publish(self):
        weather_data = self.fetch_from_google_api()
        
        # Publish
        self.precip_pub.publish(Float32(data=weather_data['precipitation_mm_h']))
        self.vis_pub.publish(Float32(data=weather_data['visibility_m']))
        self.wind_pub.publish(Float32(data=weather_data['wind_kph']))
```

## Testing

### Simulate Risk Conditions
```bash
# Simulate heavy rain
ros2 topic pub /weather/precipitation_rate std_msgs/Float32 "data: 12.0"

# Simulate poor visibility
ros2 topic pub /weather/visibility std_msgs/Float32 "data: 80.0"

# Simulate high wind
ros2 topic pub /weather/wind_speed std_msgs/Float32 "data: 60.0"
```

### View Real-Time Risk Score
```bash
ros2 run rqt_robot_monitor rqt_robot_monitor
```

## Integration with Autoware

Add to your Autoware launch file:

```python
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

# Include risk assessment
risk_assessment_launch = IncludeLaunchDescription(
    PythonLaunchDescriptionSource([
        PathJoinSubstitution([
            FindPackageShare('operational_risk_assessment'),
            'launch',
            'risk_assessment.launch.py'
        ])
    ]),
    launch_arguments={
        'update_rate': '3.0',
        'safe_threshold': '0.4'
    }.items()
)
```

## Safety Considerations

⚠️ **IMPORTANT**: This system provides **advisory information only**. 

- It does NOT automatically control the vehicle
- Human operators/safety drivers must make final decisions
- System should be validated for your specific ODD
- Thresholds should be tuned for your vehicle and conditions
- Always maintain appropriate safety margins

## Future Enhancements

- [ ] Machine learning-based risk prediction
- [ ] Historical risk pattern analysis
- [ ] Real-time weather API integration
- [ ] Camera-based weather detection
- [ ] Road surface classification
- [ ] Traffic density risk assessment
- [ ] Construction zone detection
- [ ] Emergency vehicle proximity alerts

## License

MIT License - See LICENSE file for details

## Project Information

**4utonomy by ASAS Labs** (2026)  
Production autonomous vehicle navigation and safety systems

This is a current production implementation developed by ASAS Labs. This project is independent and distinct from any historical academic proposals, research projects, or NYU-affiliated work that may have used similar naming.

## Contact

4utonomy Development Team - ASAS Labs
- Repository: https://github.com/ASAS-Labs/4utonomy-Nav
- Issues: https://github.com/ASAS-Labs/4utonomy-Nav/issues
- Email: dev@4utonomy.com
