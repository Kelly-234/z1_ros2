#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray
import numpy as np
import sys
import os
import logging
import os.path as osp

script_path = osp.dirname(osp.abspath(__file__))
node_path = osp.dirname(script_path)
sys.path.append(node_path)  # Add the node directory to the path
utils_path = osp.join(node_path, 'utils')
sys.path.append(utils_path)  # Add the utils directory to the path

from senxor.mi48 import MI48, format_header, format_framestats
from senxor.utils import data_to_frame, remap, cv_filter, RollingAverageFilter, connect_senxor

class ThermalCameraNode(Node):
    def __init__(self):
        super().__init__('thermal_camera_node')
        self.image_pub_ = self.create_publisher(Image, 'thermal_camera/image_raw', 10)
        self.temp_pub_ = self.create_publisher(Float32MultiArray, 'thermal_camera/min_max_temp', 10)

        # 声明所有可配置参数，launch文件可覆盖
        self.declare_parameter('image_width', 80)
        self.declare_parameter('image_height', 62)
        self.declare_parameter('frame_rate', 25)
        self.declare_parameter('encoding', 'bgr8')
        self.declare_parameter('temporal_filter_enable', True)
        self.declare_parameter('rolling_average_filter_enable', False)
        self.declare_parameter('median_filter_enable', False)
        self.declare_parameter('median_filter_ksize5_enable', False)
        self.declare_parameter('temporal_filter_strength', 85)
        self.declare_parameter('offset_corr', 0.0)
        self.declare_parameter('sens_factor', 100)
        self.declare_parameter('stream_enable', True)
        self.declare_parameter('start_with_header_enable', True)
        self.declare_parameter('rolling_average_temperature_minimum_frame_size', 10)
        self.declare_parameter('rolling_average_temperature_maximum_frame_size', 10)
        self.declare_parameter('use_opencv_filter', True)
        self.declare_parameter('frame_id', 'thermal_camera_link')
        self.declare_parameter('hflip', True)  # 水平镜像参数
        self.logger = logging.getLogger('thermal_camera_node')
        logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

        self.image_width = self.get_parameter('image_width').value
        self.image_height = self.get_parameter('image_height').value
        self.frame_rate = self.get_parameter('frame_rate').value
        self.encoding = self.get_parameter('encoding').value
        self.temporal_filter_enable = self.get_parameter('temporal_filter_enable').value
        self.rolling_average_filter_enable = self.get_parameter('rolling_average_filter_enable').value
        self.median_filter_enable = self.get_parameter('median_filter_enable').value
        self.median_filter_ksize5_enable = self.get_parameter('median_filter_ksize5_enable').value
        self.temporal_filter_strength = self.get_parameter('temporal_filter_strength').value
        self.offset_corr = self.get_parameter('offset_corr').value
        self.sens_factor = self.get_parameter('sens_factor').value
        self.stream_enable = self.get_parameter('stream_enable').value
        self.start_with_header_enable = self.get_parameter('start_with_header_enable').value
        self.rolling_average_temperature_minimum_frame_size = self.get_parameter('rolling_average_temperature_minimum_frame_size').value
        self.rolling_average_temperature_maximum_frame_size = self.get_parameter('rolling_average_temperature_maximum_frame_size').value
        self.use_opencv_filter = self.get_parameter('use_opencv_filter').value
        self.frame_id = self.get_parameter('frame_id').value
        self.hflip = self.get_parameter('hflip').value
        # 连接热成像相机
        self.mi48, self.connected_port, self.port_names = connect_senxor()
        if self.mi48 is None:
            self.get_logger().error(f"Failed to connect to SenXor device. Tried ports: {self.port_names}")
            raise RuntimeError("No camera found")
        self.logger.info(f'Camera info: {self.mi48.camera_info}')

        # 相机参数设置
        self.mi48.set_fps(self.frame_rate)
        self.mi48.disable_filter(f1=not self.temporal_filter_enable, f2=not self.rolling_average_filter_enable, f3=not self.median_filter_enable)
        self.mi48.set_filter_1(self.temporal_filter_strength)
        self.mi48.enable_filter(f1=self.temporal_filter_enable, f2=self.rolling_average_filter_enable, f3=self.median_filter_enable, f3_ks_5=self.median_filter_ksize5_enable)
        self.mi48.set_offset_corr(self.offset_corr)
        self.mi48.set_sens_factor(self.sens_factor)
        self.mi48.get_sens_factor()

        # 启动连续采集
        self.mi48.start(stream=self.stream_enable, with_header=self.start_with_header_enable)

        # 平滑温度范围
        self.dminav = RollingAverageFilter(N=self.rolling_average_temperature_minimum_frame_size)
        self.dmaxav = RollingAverageFilter(N=self.rolling_average_temperature_maximum_frame_size)

        # 定时器发布ROS图像
        self.timer = self.create_timer(1.0/self.frame_rate, self.timer_callback)

    def timer_callback(self):
        data, header = self.mi48.read()
        if data is None:
            self.get_logger().error('NONE data received instead of GFRA')
            return
        min_temp = self.dminav(data.min())
        max_temp = self.dmaxav(data.max())


        # 只发布原始最高温和最低温
        temp_msg = Float32MultiArray()
        # Ensure proper float32 conversion for NumPy 2.x compatibility
        temp_msg.data = [float(min_temp), float(max_temp)]
        self.temp_pub_.publish(temp_msg)

        frame = data_to_frame(data, (self.image_width, self.image_height), hflip=self.hflip)
        frame = np.clip(frame, min_temp, max_temp)

        img_data = remap(frame)
        if self.use_opencv_filter:
            filt_uint8 = cv_filter(img_data, {'blur_ks':3, 'd':5, 'sigmaColor': 27, 'sigmaSpace': 27}, use_median=True, use_bilat=True, use_nlm=False)
        else:
            filt_uint8 = img_data

        # 彩色伪彩处理并发布bgr8格式，便于rviz2彩色显示
        try:
            import cv2
            img_color = cv2.applyColorMap(filt_uint8, cv2.COLORMAP_JET)
            msg = Image()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = self.frame_id
            msg.height = img_color.shape[0]
            msg.width = img_color.shape[1]
            msg.encoding = self.encoding
            msg.is_bigendian = 0
            msg.step = img_color.shape[1] * 3
            # Convert to list of integers for ROS2 compatibility
            msg.data = list(img_color.tobytes())
            self.image_pub_.publish(msg)
        except Exception as e:
            self.get_logger().warn(f"cv2 colormap failed: {e}, fallback to mono8.")
            msg = Image()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = self.frame_id
            msg.height = img_data.shape[0]
            msg.width = img_data.shape[1]
            msg.encoding = 'mono8'
            msg.is_bigendian = 0
            msg.step = img_data.shape[1]
            # Convert to list of integers for ROS2 compatibility
            msg.data = list(img_data.tobytes())
            self.image_pub_.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = ThermalCameraNode() # Initialize the node
        node.get_logger().info("Thermal camera node started successfully.")
        rclpy.spin(node) # Keep the node running
    except Exception as e:
        print(f"thermal_camera_node failed: {e}")
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()



