#!/usr/bin/env python3
"""
诊断点云数据问题的脚本
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
import numpy as np


class PointCloudDiagnostic(Node):
    def __init__(self):
        super().__init__('pointcloud_diagnostic')
        
        self.subscription = self.create_subscription(
            PointCloud2,
            '/rgbd_camera/points',
            self.pointcloud_callback,
            10)
        
        self.get_logger().info('点云诊断工具已启动，等待点云数据...')

    def pointcloud_callback(self, msg):
        self.get_logger().info('=' * 60)
        self.get_logger().info('收到点云消息')
        self.get_logger().info(f'  Header: frame_id={msg.header.frame_id}, stamp={msg.header.stamp}')
        self.get_logger().info(f'  尺寸: width={msg.width}, height={msg.height}')
        self.get_logger().info(f'  总点数(期望): {msg.width * msg.height}')
        self.get_logger().info(f'  数据大小: {len(msg.data)} bytes')
        self.get_logger().info(f'  点步长: {msg.point_step} bytes')
        self.get_logger().info(f'  行步长: {msg.row_step} bytes')
        self.get_logger().info(f'  是否为稠密: {msg.is_dense}')
        self.get_logger().info(f'  字段: {[f"{f.name}({f.datatype})" for f in msg.fields]}')
        
        # 尝试读取点
        try:
            points = list(point_cloud2.read_points(
                msg, field_names=("x", "y", "z"), skip_nans=False))
            self.get_logger().info(f'  实际读取点数: {len(points)}')
            
            if len(points) > 0:
                # 转换为numpy数组分析
                # read_points 返回的是结构化数组或命名元组，需要正确提取
                points_list = []
                for point in points:
                    if hasattr(point, 'x'):
                        points_list.append([point.x, point.y, point.z])
                    elif isinstance(point, (list, tuple)) and len(point) >= 3:
                        points_list.append([point[0], point[1], point[2]])
                    elif isinstance(point, dict):
                        points_list.append([point.get('x', 0), point.get('y', 0), point.get('z', 0)])
                    else:
                        # 尝试作为结构化数组访问
                        try:
                            points_list.append([point['x'], point['y'], point['z']])
                        except:
                            pass
                
                if len(points_list) > 0:
                    points_array = np.array(points_list, dtype=np.float32)
                    
                    # 统计
                    inf_count = np.isinf(points_array).any(axis=1).sum()
                    nan_count = np.isnan(points_array).any(axis=1).sum()
                    finite_count = np.isfinite(points_array).all(axis=1).sum()
                    
                    self.get_logger().info(f'  统计: Inf={inf_count}, NaN={nan_count}, 有限值={finite_count}')
                    
                    if finite_count > 0:
                        valid_points = points_array[np.isfinite(points_array).all(axis=1)]
                        distances = np.linalg.norm(valid_points, axis=1)
                        self.get_logger().info(f'  距离范围: [{distances.min():.3f}, {distances.max():.3f}]m')
                        self.get_logger().info(f'  坐标范围: x=[{valid_points[:, 0].min():.3f}, {valid_points[:, 0].max():.3f}], '
                                             f'y=[{valid_points[:, 1].min():.3f}, {valid_points[:, 1].max():.3f}], '
                                             f'z=[{valid_points[:, 2].min():.3f}, {valid_points[:, 2].max():.3f}]')
                else:
                    self.get_logger().warn('  无法提取点坐标！')
            else:
                self.get_logger().warn('  无法读取任何点！')
                
        except Exception as e:
            self.get_logger().error(f'  读取点云时出错: {e}')
        
        self.get_logger().info('=' * 60)


def main(args=None):
    rclpy.init(args=args)
    node = PointCloudDiagnostic()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

