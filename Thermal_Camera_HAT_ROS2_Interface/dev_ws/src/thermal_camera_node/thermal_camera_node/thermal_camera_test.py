#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray
import numpy as np
import cv2

class ThermalCameraTestNode(Node):
    def __init__(self):
        super().__init__('thermal_camera_test_node')
        
        # Create publishers
        self.image_pub_ = self.create_publisher(Image, 'thermal_camera/image_raw', 10)
        self.temp_pub_ = self.create_publisher(Float32MultiArray, 'thermal_camera/min_max_temp', 10)
        
        # Create timer for publishing test data
        self.timer = self.create_timer(1.0, self.timer_callback)
        
        self.get_logger().info('Thermal camera test node started successfully.')

    def timer_callback(self):
        try:
            # Create test temperature data
            temp_msg = Float32MultiArray()
            temp_msg.data = [25.5, 35.2]  # fake min/max temperatures
            self.temp_pub_.publish(temp_msg)
            
            # Create test image (80x62 thermal image size)
            test_img = np.random.randint(0, 255, (62, 80), dtype=np.uint8)
            
            # Apply colormap
            img_color = cv2.applyColorMap(test_img, cv2.COLORMAP_JET)
            
            # Create ROS Image message
            msg = Image()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.height = img_color.shape[0]
            msg.width = img_color.shape[1]
            msg.encoding = 'bgr8'
            msg.is_bigendian = 0
            msg.step = img_color.shape[1] * 3
            # Convert to list of integers for ROS2 compatibility
            msg.data = list(img_color.tobytes())
            
            self.image_pub_.publish(msg)
            self.get_logger().info('Published test thermal data')
            
        except Exception as e:
            self.get_logger().error(f'Error in timer_callback: {e}')

def main(args=None):
    rclpy.init(args=args)
    node = ThermalCameraTestNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()