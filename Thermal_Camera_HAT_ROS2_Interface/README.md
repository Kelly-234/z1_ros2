# Thermal Camera HAT ROS2 Interface

本项目是基于微雪的 Thermal Camera HAT 的 USB 版本的 ROS2 接口，支持在 ARM64 平台上进行热像仪数据采集和处理。

## 📋 测试平台
- ✅ Jetson Orin NX 
- ✅ Dell Latitude 3450 (Linux)
- 🔧 支持其他 ARM64/x86_64 Linux 平台

## 🚀 功能特性
1. **实时热像图发布** - Topic: `/thermal_camera/image_raw` (sensor_msgs/Image)
2. **温度范围数据** - Topic: `/thermal_camera/min_max_temp` (std_msgs/Float32MultiArray)
3. **多种滤波算法** - 时域滤波、中值滤波、滑动平均等
4. **可配置参数** - 分辨率、帧率、滤波参数等
5. **自动权限管理** - 自动设置USB设备权限

## 📊 硬件信息
- **相机型号**: Waveshare Thermal Camera HAT (USB版本)
- **分辨率**: 80x62 像素
- **最大帧率**: 25.5 FPS
- **接口**: USB (通常为 /dev/ttyACM0)

## 🛠 安装与配置

### 1. 系统依赖
确保已安装 ROS2 Humble：
```bash
# Ubuntu 22.04
sudo apt update
sudo apt install ros-humble-desktop
```

### 2. Python依赖安装
```bash
# 安装项目依赖
pip install -r requirements.txt

# 或参考官方文档
# https://www.waveshare.net/wiki/Thermal_Camera_HAT
```

### 3. 构建 ROS2 工作空间
```bash
cd dev_ws
colcon build --packages-select thermal_camera_node
source install/setup.bash
```

## 🚀 快速启动

### 方法1：使用启动脚本（推荐）
```bash
# 赋予执行权限
chmod +x start_thermal_camera_node.sh

# 启动节点（会自动设置USB权限）
./start_thermal_camera_node.sh
```

### 方法2：使用 launch 文件
```bash
cd dev_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch src/thermal_camera_node/launch/thermal_camera_launch.py
```

### 方法3：直接运行节点
```bash
cd dev_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run thermal_camera_node thermal_camera_publisher
```

## 📡 话题验证

启动节点后，可以通过以下命令验证：

```bash
# 检查话题列表
ros2 topic list

# 查看温度数据
ros2 topic echo /thermal_camera/min_max_temp

# 查看图像话题信息
ros2 topic info /thermal_camera/image_raw

# 检查节点状态
ros2 node list
ros2 node info /thermal_camera_node
```

## ⚙️ 参数配置

可在 [`launch/thermal_camera_launch.py`](dev_ws/src/thermal_camera_node/launch/thermal_camera_launch.py) 文件中修改以下参数：

| 参数名                                      | 默认值    | 说明                       |
|---------------------------------------------|----------|----------------------------|
| image_width                                | 80       | 图像宽度                   |
| image_height                               | 62       | 图像高度                   |
| frame_rate                                 | 25       | 帧率（Hz）                 |
| encoding                                   | bgr8     | ROS图像编码格式            |
| temporal_filter_enable                     | True     | 是否启用时域滤波           |
| rolling_average_filter_enable              | False    | 是否启用滑动平均滤波       |
| median_filter_enable                       | False    | 是否启用中值滤波           |
| median_filter_ksize5_enable                | False    | 是否启用5x5中值滤波        |
| temporal_filter_strength                   | 85       | 时域滤波强度               |
| offset_corr                                | 0.0      | 温度偏移修正（单位K）      |
| sens_factor                                | 100      | 灵敏度因子                 |
| stream_enable                              | True     | 是否连续采集               |
| start_with_header_enable                   | True     | 是否带帧头                 |
| rolling_average_temperature_minimum_frame_size | 10   | 最小温度滑动窗口帧数       |
| rolling_average_temperature_maximum_frame_size | 10   | 最大温度滑动窗口帧数       |
| use_opencv_filter                          | True     | 是否使用OpenCV滤波         |

## 🔍 数据可视化

### 使用 rviz2 查看热像图
```bash
# 启动 rviz2
rviz2

# 在 rviz2 中：
# 1. Add -> By Topic -> /thermal_camera/image_raw -> Image
# 2. 设置 Fixed Frame 为 "thermal_camera_frame"
```

### 实时温度监控
```bash
# 持续监控温度范围
ros2 topic echo /thermal_camera/min_max_temp

# 输出示例：
# data: [23.703125, 32.3125]  # [最低温度(°C), 最高温度(°C)]
```

## 🐛 故障排除

### 常见问题及解决方案

1. **权限问题**
```bash
# 手动设置USB设备权限
sudo chmod 777 /dev/ttyACM0
```

2. **ROS2 daemon 问题**
```bash
# 重启 ROS2 daemon
ros2 daemon stop
ros2 daemon start
```

3. **缺少依赖**
```bash
# 安装缺少的 cmapy 模块（可选，用于更好的颜色映射）
pip install cmapy
```

4. **设备未检测到**
```bash
# 检查USB设备
lsusb
ls /dev/ttyACM*

# 确认设备连接并重新插拔
```

## 📝 开发状态

- ✅ 基本功能完成
- ✅ 多平台测试通过
- ✅ 参数配置完善
- ⚠️ cmapy 模块为可选依赖
- 🔧 持续优化中

## 📁 项目结构

```
Thermal_Camera_HAT_ROS2_Interface/
├── dev_ws/                          # ROS2 工作空间
│   ├── src/thermal_camera_node/     # 热像仪节点源码
│   │   ├── thermal_camera_node/     # Python 包
│   │   ├── launch/                  # Launch 文件
│   │   ├── utils/                   # 工具函数
│   │   ├── package.xml              # 包描述文件
│   │   └── setup.py                 # 安装配置
│   ├── build/                       # 构建输出
│   └── install/                     # 安装文件
├── start_thermal_camera_node.sh     # 启动脚本
├── requirements.txt                 # Python 依赖
└── README.md                        # 项目文档
```

## 🤝 贡献指南

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目遵循 MIT 许可证。详情请查看 [LICENSE](LICENSE) 文件。

## 📞 联系方式

- 作者：JINGERGER
- 项目链接：[https://github.com/JINGERGER/Thermal_Camera_HAT_ROS2_Interface](https://github.com/JINGERGER/Thermal_Camera_HAT_ROS2_Interface)

## rviz2 测试截图

![rviz2 测试](https://imgbed.yesord.top/file/github/1753774880194_微信截图_20250729153847.png)

---

💡 **提示**: 如果在使用过程中遇到问题，请查看故障排除部分或提交 Issue。
