#!/usr/bin/env python3
"""
深度图像过滤器
将Inf和NaN值转换为0或最大深度值，以便正确显示
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import numpy as np


class DepthImageFilter(Node):
    def __init__(self):
        super().__init__('depth_image_filter')
        
        # 参数
        self.declare_parameter('max_depth', 10.0)
        self.declare_parameter('replace_inf_with', 0.0)  # 0.0 = 替换为0, -1.0 = 替换为max_depth
        
        self.max_depth = self.get_parameter('max_depth').get_parameter_value().double_value
        self.replace_inf_with = self.get_parameter('replace_inf_with').get_parameter_value().double_value
        
        # 订阅原始深度图像
        self.subscription = self.create_subscription(
            Image,
            '/rgbd_camera/depth_image',
            self.depth_callback,
            10)
        
        # 发布过滤后的深度图像
        self.publisher = self.create_publisher(
            Image,
            '/rgbd_camera/depth_image_filtered',
            10)
        
        self.get_logger().info('深度图像过滤器已启动')
        self.get_logger().info(f'最大深度: {self.max_depth}m')
        self.get_logger().info(f'Inf值替换为: {self.replace_inf_with if self.replace_inf_with >= 0 else self.max_depth}m')

    def depth_callback(self, msg):
        # 转换深度数据
        try:
            depth_array = np.frombuffer(msg.data, dtype=np.float32)
            depth_array = depth_array.reshape((msg.height, msg.width))
            
            # 统计原始数据
            inf_count = np.isinf(depth_array).sum()
            nan_count = np.isnan(depth_array).sum()
            valid_count = (np.isfinite(depth_array) & (depth_array > 0)).sum()
            
            # 过滤Inf和NaN值
            if self.replace_inf_with >= 0:
                # 替换为0（黑色）
                depth_array[np.isinf(depth_array)] = 0.0
                depth_array[np.isnan(depth_array)] = 0.0
            else:
                # 替换为最大深度值
                depth_array[np.isinf(depth_array)] = self.max_depth
                depth_array[np.isnan(depth_array)] = self.max_depth
            
            # 限制在有效范围内
            depth_array[depth_array > self.max_depth] = self.max_depth
            depth_array[depth_array < 0] = 0.0
            
            # 创建新的图像消息
            filtered_msg = Image()
            filtered_msg.header = msg.header
            filtered_msg.height = msg.height
            filtered_msg.width = msg.width
            filtered_msg.encoding = msg.encoding
            filtered_msg.is_bigendian = msg.is_bigendian
            filtered_msg.step = msg.step
            filtered_msg.data = depth_array.astype(np.float32).tobytes()
            
            # 发布过滤后的图像
            self.publisher.publish(filtered_msg)
            
            # 定期输出统计信息
            if inf_count > 0 or nan_count > 0:
                self.get_logger().debug(
                    f'过滤: Inf={inf_count}, NaN={nan_count}, '
                    f'有效={valid_count}/{msg.width*msg.height}'
                )
                
        except Exception as e:
            self.get_logger().error(f'处理深度图像时出错: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = DepthImageFilter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

