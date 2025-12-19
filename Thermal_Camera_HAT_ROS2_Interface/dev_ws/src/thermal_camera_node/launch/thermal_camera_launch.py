from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_setup(context, *args, **kwargs):
    """设置并返回热感相机节点"""
    frame_id = LaunchConfiguration("frame_id").perform(context)
    hflip = LaunchConfiguration("hflip").perform(context).lower() == "true"
    
    return [
        Node(
            package='thermal_camera_node',
            executable='thermal_camera_publisher',
            name='thermal_camera_node',
            output='screen',
            parameters=[
                {
                    'image_width': 80,
                    'image_height': 62,
                    'frame_rate': 25,
                    'encoding': 'bgr8',
                    'temporal_filter_enable': True,
                    'rolling_average_filter_enable': False,
                    'median_filter_enable': False,
                    'median_filter_ksize5_enable': False,
                    'temporal_filter_strength': 85,
                    'offset_corr': 0.0,
                    'sens_factor': 100,
                    'stream_enable': True,
                    'start_with_header_enable': True,
                    'rolling_average_temperature_minimum_frame_size': 10,
                    'rolling_average_temperature_maximum_frame_size': 10,
                    'use_opencv_filter': True,
                    'frame_id': frame_id,
                    'hflip': hflip,
                }
            ]
        )
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            "frame_id",
            default_value="thermal_camera_link",
            description="Frame ID for thermal camera"
        ),
        DeclareLaunchArgument(
            "hflip",
            default_value="false",
            description="Horizontal flip (mirror) the image (true/false)"
        ),
        OpaqueFunction(function=launch_setup)
    ])
