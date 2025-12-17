#!/usr/bin/env python3
"""
点云过滤器
移除Inf和NaN值，确保点云可以被octomap_server处理
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
import numpy as np


class PointCloudFilter(Node):
    def __init__(self):
        super().__init__('pointcloud_filter')
        
        # 参数
        self.declare_parameter('max_range', 10.0)
        self.declare_parameter('min_range', 0.01)
        
        self.max_range = self.get_parameter('max_range').get_parameter_value().double_value
        self.min_range = self.get_parameter('min_range').get_parameter_value().double_value
        
        # 订阅原始点云
        self.subscription = self.create_subscription(
            PointCloud2,
            '/rgbd_camera/points',
            self.pointcloud_callback,
            10)
        
        # 发布过滤后的点云
        self.publisher = self.create_publisher(
            PointCloud2,
            '/rgbd_camera/points_filtered',
            10)
        
        self.get_logger().info('点云过滤器已启动')
        self.get_logger().info(f'范围: {self.min_range} - {self.max_range}m')

    def pointcloud_callback(self, msg):
        try:
            # 检查点云消息的基本信息
            total_points_expected = msg.width * msg.height
            if total_points_expected == 0:
                if not hasattr(self, '_empty_warn_count'):
                    self._empty_warn_count = 0
                self._empty_warn_count += 1
                if self._empty_warn_count % 30 == 1:  # 每30帧警告一次
                    self.get_logger().warn(
                        f'点云消息为空: width={msg.width}, height={msg.height}, '
                        f'data_size={len(msg.data)} bytes'
                    )
                return
            
            # 从PointCloud2提取点
            # read_points返回的是结构化numpy数组
            try:
                # 直接读取为结构化数组
                points_array = point_cloud2.read_points(
                    msg, field_names=("x", "y", "z"), skip_nans=False)
                
                # 转换为普通数组
                # 结构化数组可以通过字段名访问，如 points_array['x']
                if len(points_array) == 0:
                    if not hasattr(self, '_no_points_warn_count'):
                        self._no_points_warn_count = 0
                    self._no_points_warn_count += 1
                    if self._no_points_warn_count % 30 == 1:
                        self.get_logger().warn('read_points返回空数组')
                    return
                
                # 从结构化数组提取x, y, z
                x = points_array['x']
                y = points_array['y']
                z = points_array['z']
                
                # 组合成Nx3数组
                points_array = np.column_stack((x, y, z)).astype(np.float32)
                
            except Exception as e:
                # 如果直接读取失败，尝试逐点读取
                self.get_logger().warn(f'直接读取失败，尝试逐点读取: {e}')
                points_list = []
                for point in point_cloud2.read_points(
                    msg, field_names=("x", "y", "z"), skip_nans=False):
                    # read_points返回结构化数组，可以通过字段名访问
                    try:
                        if isinstance(point, np.ndarray) and point.dtype.names:
                            # 结构化数组
                            points_list.append([point['x'], point['y'], point['z']])
                        elif hasattr(point, 'x'):
                            points_list.append([point.x, point.y, point.z])
                        elif isinstance(point, (list, tuple)) and len(point) >= 3:
                            points_list.append([point[0], point[1], point[2]])
                        elif isinstance(point, dict):
                            points_list.append([point.get('x', 0), point.get('y', 0), point.get('z', 0)])
                    except Exception as pe:
                        continue
                
                if len(points_list) == 0:
                    if not hasattr(self, '_no_points_warn_count'):
                        self._no_points_warn_count = 0
                    self._no_points_warn_count += 1
                    if self._no_points_warn_count % 30 == 1:
                        self.get_logger().warn('无法从点云中提取点')
                    return
                
                points_array = np.array(points_list, dtype=np.float32)
            
            # 现在 points_array 是 Nx3 的 numpy 数组
            if len(points_array) == 0:
                if not hasattr(self, '_no_points_warn_count'):
                    self._no_points_warn_count = 0
                self._no_points_warn_count += 1
                if self._no_points_warn_count % 30 == 1:  # 每30帧警告一次
                    self.get_logger().warn(
                        f'无法从点云中提取点: 期望点数={total_points_expected}, '
                        f'width={msg.width}, height={msg.height}, '
                        f'data_size={len(msg.data)} bytes, fields={[f.name for f in msg.fields]}'
                    )
                return
            total_points = len(points_array)
            
            # 统计原始数据
            inf_mask = np.isinf(points_array).any(axis=1)
            nan_mask = np.isnan(points_array).any(axis=1)
            inf_count = inf_mask.sum()
            nan_count = nan_mask.sum()
            
            # 过滤无效点
            # 1. 移除Inf和NaN
            valid_mask = np.isfinite(points_array).all(axis=1)
            finite_count = valid_mask.sum()
            
            if finite_count == 0:
                self.get_logger().warn(
                    f'所有点都无效: Inf={inf_count}, NaN={nan_count}, 总数={total_points}'
                )
                return
            
            # 2. 计算距离并过滤范围
            valid_points = points_array[valid_mask]
            distances = np.linalg.norm(valid_points, axis=1)
            
            # 统计距离分布
            too_close = (distances < self.min_range).sum()
            too_far = (distances > self.max_range).sum()
            in_range = ((distances >= self.min_range) & (distances <= self.max_range)).sum()
            
            range_mask = (distances >= self.min_range) & (distances <= self.max_range)
            
            # 获取最终有效的点
            final_valid_points = valid_points[range_mask]
            
            if len(final_valid_points) == 0:
                self.get_logger().warn(
                    f'过滤后点云为空！统计: 总数={total_points}, '
                    f'有限值={finite_count}, 太近={too_close}, 太远={too_far}, '
                    f'范围内={in_range}, 距离范围=[{distances.min():.2f}, {distances.max():.2f}]m'
                )
                return
            
            # 创建新的点云消息
            filtered_msg = point_cloud2.create_cloud_xyz32(msg.header, final_valid_points.tolist())
            
            # 发布过滤后的点云
            self.publisher.publish(filtered_msg)
            
            # 定期输出统计信息（每10帧输出一次，避免日志过多）
            if not hasattr(self, '_frame_count'):
                self._frame_count = 0
            self._frame_count += 1
            
            if self._frame_count % 10 == 0:
                self.get_logger().info(
                    f'过滤统计: {len(final_valid_points)}/{total_points} 有效点 '
                    f'({len(final_valid_points)/total_points*100:.1f}%) | '
                    f'Inf={inf_count}, NaN={nan_count}, 太近={too_close}, 太远={too_far} | '
                    f'距离范围=[{distances.min():.2f}, {distances.max():.2f}]m'
                )
                
        except Exception as e:
            self.get_logger().error(f'处理点云时出错: {e}', exc_info=True)


def main(args=None):
    rclpy.init(args=args)
    node = PointCloudFilter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

