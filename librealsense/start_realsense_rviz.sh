#!/bin/bash

# RealSense相机在RViz中查看的启动脚本

echo "=========================================="
echo "启动RealSense相机和RViz"
echo "=========================================="

# Source ROS2环境
if [ -f /opt/ros/humble/setup.bash ]; then
    source /opt/ros/humble/setup.bash
    echo "✓ ROS2 Humble环境已加载"
else
    echo "✗ 错误: 未找到ROS2 Humble环境"
    echo "请确保已安装ROS2 Humble: sudo apt install ros-humble-desktop"
    exit 1
fi

# 检查是否安装了realsense2-camera包
if ! ros2 pkg list | grep -q realsense2_camera; then
    echo ""
    echo "⚠ 警告: 未检测到realsense2-camera包"
    echo "正在尝试安装..."
    sudo apt update
    sudo apt install -y ros-humble-realsense2-camera
    if [ $? -ne 0 ]; then
        echo "✗ 安装失败，请手动运行: sudo apt install ros-humble-realsense2-camera"
        exit 1
    fi
    echo "✓ realsense2-camera包安装成功"
fi

# 检查相机是否连接
echo ""
echo "检查相机连接..."
if [ -f /home/qianhai/z1_ws/src/librealsense/build/Release/rs-enumerate-devices ]; then
    /home/qianhai/z1_ws/src/librealsense/build/Release/rs-enumerate-devices > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✓ 相机已连接"
    else
        echo "⚠ 警告: 未检测到相机，但将继续启动节点"
    fi
else
    echo "⚠ 无法检查相机连接状态"
fi

# 启动RealSense相机节点（后台运行）
echo ""
echo "启动RealSense相机节点..."
ros2 launch realsense2_camera rs_launch.py > /tmp/realsense_node.log 2>&1 &
REALSENSE_PID=$!

# 等待相机节点启动
echo "等待相机节点初始化（3秒）..."
sleep 3

# 检查节点是否正常运行
if ps -p $REALSENSE_PID > /dev/null; then
    echo "✓ 相机节点已启动 (PID: $REALSENSE_PID)"
else
    echo "✗ 相机节点启动失败，请查看日志: /tmp/realsense_node.log"
    exit 1
fi

# 显示可用的话题
echo ""
echo "可用的话题:"
ros2 topic list | grep camera | head -10

# 启动RViz
echo ""
echo "启动RViz..."
echo "=========================================="
echo "在RViz中配置:"
echo "1. Add -> By topic -> /camera/color/image_raw -> Image"
echo "2. Add -> By topic -> /camera/depth/image_rect_raw -> Image"
echo "3. Add -> By topic -> /camera/depth/color/points -> PointCloud2"
echo "4. 设置 Fixed Frame 为 'camera_link'"
echo "=========================================="
echo ""

rviz2

# 当RViz关闭时，也关闭相机节点
echo ""
echo "关闭相机节点..."
kill $REALSENSE_PID 2>/dev/null
wait $REALSENSE_PID 2>/dev/null
echo "✓ 已退出"




