# Copyright 2025 IDRA, University of Trento
# Author: Auto-generated launch file for complete system
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
)
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_path
import os


def launch_setup(context, *args, **kwargs):
    """设置并返回所有需要启动的节点和launch文件"""
    
    # 获取参数值
    sim_ignition = LaunchConfiguration("sim_ignition").perform(context)
    rviz = LaunchConfiguration("rviz").perform(context)
    with_gripper = LaunchConfiguration("with_gripper").perform(context)
    
    # 八叉树参数
    octomap_frame_id = LaunchConfiguration("octomap_frame_id").perform(context)
    octomap_cloud_in = LaunchConfiguration("octomap_cloud_in").perform(context)
    octomap_resolution = LaunchConfiguration("octomap_resolution").perform(context)
    octomap_max_range = LaunchConfiguration("octomap_max_range").perform(context)
    octomap_min_range = LaunchConfiguration("octomap_min_range").perform(context)
    octomap_hit = LaunchConfiguration("octomap_hit").perform(context)
    octomap_miss = LaunchConfiguration("octomap_miss").perform(context)
    octomap_occupancy_min_z = LaunchConfiguration("octomap_occupancy_min_z").perform(context)
    octomap_occupancy_max_z = LaunchConfiguration("octomap_occupancy_max_z").perform(context)
    octomap_filter_ground = LaunchConfiguration("octomap_filter_ground").perform(context)
    
    # 构建八叉树参数字典
    # 注意：filter_ground_plane 是octomap_server使用的参数名
    octomap_parameters = [{
        "frame_id": octomap_frame_id,
        "resolution": float(octomap_resolution),
        "sensor_model.max_range": float(octomap_max_range),
        "sensor_model.min_range": float(octomap_min_range),
        "sensor_model.hit": float(octomap_hit),
        "sensor_model.miss": float(octomap_miss),
        "occupancy_min_z": float(octomap_occupancy_min_z),
        "occupancy_max_z": float(octomap_occupancy_max_z),
        "filter_ground_plane": octomap_filter_ground.lower() == "true",
    }]
    
    nodes_to_start = []
    
    # 1. 启动实体机械臂和MoveIt
    z1_moveit_launch_file = get_package_share_path("z1_moveit") / "launch" / "z1_moveit.launch.py"
    z1_moveit_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(z1_moveit_launch_file)),
        launch_arguments={
            "sim_ignition": sim_ignition,
            "rviz": rviz,
            "with_gripper": with_gripper,
        }.items(),
    )
    nodes_to_start.append(z1_moveit_launch)
    
    # 2. 启动RealSense相机和点云
    # 注意：realsense2_camera包通常安装在系统中，不在工作空间内
    # 使用rs_launch.py而不是rs_pointcloud_launch.py，因为rs_launch.py通常不启动RViz
    # 如果需要点云，可以通过参数启用
    from launch.actions import ExecuteProcess
    realsense_process = ExecuteProcess(
        cmd=["ros2", "launch", "realsense2_camera", "rs_launch.py", 
             "pointcloud.enable:=true", "enable_rgb:=true", "enable_depth:=true"],
        output="screen",
    )
    nodes_to_start.append(realsense_process)
    
    # 3. 启动八叉树服务器
    octomap_node = Node(
        package="octomap_server",
        executable="octomap_server_node",
        name="octomap_server",
        parameters=octomap_parameters,
        remappings=[
            ("cloud_in", octomap_cloud_in),
        ],
        output="screen",
    )
    nodes_to_start.append(octomap_node)
    
    # 4. 启动热感相机
    # 设置USB设备权限（必需，因为热感相机节点需要访问/dev/ttyACM0）
    # 注意：如果通过udev规则配置了权限，可以注释掉这部分
    usb_permission_process = ExecuteProcess(
        cmd=["sudo", "chmod", "777", "/dev/ttyACM0"],
        output="screen",
    )
    nodes_to_start.append(usb_permission_process)
    
    # 直接使用热感相机的launch文件
    # 尝试通过包路径获取，如果失败则使用相对路径
    try:
        thermal_camera_launch_file = get_package_share_path("thermal_camera_node") / "launch" / "thermal_camera_launch.py"
        thermal_camera_launch_path = str(thermal_camera_launch_file)
    except Exception:
        # 如果包未安装，使用相对路径
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        workspace_src_dir = os.path.join(current_file_dir, "..", "..", "..", "..")
        workspace_src_dir = os.path.abspath(workspace_src_dir)
        thermal_camera_launch_path = os.path.join(
            workspace_src_dir,
            "Thermal_Camera_HAT_ROS2_Interface",
            "dev_ws", "src", "thermal_camera_node", "launch", "thermal_camera_launch.py"
        )
    
    if os.path.exists(thermal_camera_launch_path):
        thermal_camera_launch = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(thermal_camera_launch_path),
            launch_arguments={
                "frame_id": "thermal_camera_optical_frame",  # 使用光学坐标系，符合ROS标准
                "hflip": "true",  # 启用水平镜像
            }.items(),
        )
        nodes_to_start.append(thermal_camera_launch)
    
    # 5. 发布热感相机到camera_link的静态TF变换
    # 热感相机位于RGB相机正上方5cm
    thermal_camera_tf_node = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="thermal_camera_tf_publisher",
        arguments=[
            "0", "0", "0.05",  # x, y, z (5cm = 0.05m in z direction)
            "0", "0", "0", "1",  # qx, qy, qz, qw (no rotation)
            "camera_link",
            "thermal_camera_link"
        ],
        output="screen",
    )
    nodes_to_start.append(thermal_camera_tf_node)
    
    # 6. 发布热感相机机械坐标系到光学坐标系的TF变换
    # 遵循REP-103标准：光学坐标系Z轴向前，X轴向右，Y轴向下
    # 与RGB和深度相机使用相同的转换：RPY(-90°, 0°, -90°) = 四元数(-0.500, 0.500, -0.500, 0.500)
    thermal_camera_optical_tf_node = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="thermal_camera_optical_tf_publisher",
        arguments=[
            "0", "0", "0",  # x, y, z (无平移)
            "-0.500", "0.500", "-0.500", "0.500",  # qx, qy, qz, qw (与RGB/深度相机相同的旋转)
            "thermal_camera_link",
            "thermal_camera_optical_frame"
        ],
        output="screen",
    )
    nodes_to_start.append(thermal_camera_optical_tf_node)
    
    return nodes_to_start


def generate_launch_description():
    """生成launch描述"""
    
    declared_arguments = []
    
    # 机械臂相关参数
    declared_arguments.append(
        DeclareLaunchArgument(
            "sim_ignition",
            default_value="false",
            description="Launch simulation in Ignition Gazebo? (false for real robot)"
        )
    )
    
    declared_arguments.append(
        DeclareLaunchArgument(
            "rviz",
            default_value="true",
            description="Launch RViz?"
        )
    )
    
    declared_arguments.append(
        DeclareLaunchArgument(
            "with_gripper",
            default_value="false",
            description="Use the gripper? (should be false if gripper is removed from URDF)"
        )
    )
    
    # 八叉树相关参数
    declared_arguments.append(
        DeclareLaunchArgument(
            "octomap_frame_id",
            default_value="camera_link",
            description="Frame ID for octomap"
        )
    )
    
    declared_arguments.append(
        DeclareLaunchArgument(
            "octomap_cloud_in",
            default_value="/camera/camera/depth/color/points",
            description="Input point cloud topic for octomap"
        )
    )
    
    declared_arguments.append(
        DeclareLaunchArgument(
            "octomap_resolution",
            default_value="0.02",
            description="Resolution of octomap (in meters)"
        )
    )
    
    declared_arguments.append(
        DeclareLaunchArgument(
            "octomap_max_range",
            default_value="1.0",
            description="Maximum range for sensor model (in meters)"
        )
    )
    
    declared_arguments.append(
        DeclareLaunchArgument(
            "octomap_min_range",
            default_value="0.05",
            description="Minimum range for sensor model (in meters)"
        )
    )
    
    declared_arguments.append(
        DeclareLaunchArgument(
            "octomap_hit",
            default_value="0.7",
            description="Hit probability (0-1)"
        )
    )
    
    declared_arguments.append(
        DeclareLaunchArgument(
            "octomap_miss",
            default_value="0.4",
            description="Miss probability (0-1)"
        )
    )
    
    declared_arguments.append(
        DeclareLaunchArgument(
            "octomap_occupancy_min_z",
            default_value="0.0",
            description="Minimum Z height for occupancy (in meters)"
        )
    )
    
    declared_arguments.append(
        DeclareLaunchArgument(
            "octomap_occupancy_max_z",
            default_value="1.0",
            description="Maximum Z height for occupancy (in meters)"
        )
    )
    
    declared_arguments.append(
        DeclareLaunchArgument(
            "octomap_filter_ground",
            default_value="false",
            description="Filter ground plane? (true/false)"
        )
    )
    
    return LaunchDescription(
        declared_arguments + [OpaqueFunction(function=launch_setup)]
    )