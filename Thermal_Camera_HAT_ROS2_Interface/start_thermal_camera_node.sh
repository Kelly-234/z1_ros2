#!/bin/bash
echo "Starting Thermal Camera HAT ROS2 Interface..."
sudo /bin/chmod 777 /dev/ttyACM0
echo "Permissions set for /dev/ttyACM0"
echo "Starting ROS2 environment..."
source /opt/ros/humble/setup.bash
echo "Sourcing ROS2 setup script..."
source "$(dirname "$0")"/dev_ws/install/setup.bash
echo "Starting thermal camera node..."
ros2 launch "$(dirname "$0")"/dev_ws/src/thermal_camera_node/launch/thermal_camera_launch.py
echo "Thermal camera node ended."