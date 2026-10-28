"""Launch file for Operational Risk Assessment System."""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    """Generate launch description for risk assessment system."""
    
    # Declare launch arguments
    update_rate_arg = DeclareLaunchArgument(
        'update_rate',
        default_value='2.0',
        description='Risk assessment update rate (Hz)'
    )
    
    safe_threshold_arg = DeclareLaunchArgument(
        'safe_threshold',
        default_value='0.4',
        description='Overall risk score threshold for safe operation (0.0-1.0)'
    )
    
    # Launch configuration
    update_rate = LaunchConfiguration('update_rate')
    safe_threshold = LaunchConfiguration('safe_threshold')
    
    # Weather Risk Monitor
    weather_monitor = Node(
        package='operational_risk_assessment',
        executable='weather_risk_monitor.py',
        name='weather_risk_monitor',
        output='screen',
        parameters=[{
            'update_rate': update_rate
        }]
    )
    
    # Sensor Health Monitor
    sensor_monitor = Node(
        package='operational_risk_assessment',
        executable='sensor_health_monitor.py',
        name='sensor_health_monitor',
        output='screen',
        parameters=[{
            'update_rate': update_rate,
            'expected_points': 65536,  # Ouster OS1-64 typical
            'stale_threshold_sec': 2.0
        }]
    )
    
    # Operational Domain Monitor
    operational_monitor = Node(
        package='operational_risk_assessment',
        executable='operational_domain_monitor.py',
        name='operational_domain_monitor',
        output='screen',
        parameters=[{
            'update_rate': update_rate
        }]
    )
    
    # Risk Aggregator
    aggregator = Node(
        package='operational_risk_assessment',
        executable='risk_aggregator.py',
        name='risk_aggregator',
        output='screen',
        parameters=[{
            'update_rate': 5.0,
            'safe_threshold': safe_threshold
        }]
    )
    
    return LaunchDescription([
        update_rate_arg,
        safe_threshold_arg,
        weather_monitor,
        sensor_monitor,
        operational_monitor,
        aggregator
    ])
