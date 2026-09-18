import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, ComposableNodeContainer
from launch_ros.descriptions import ComposableNode

def generate_launch_description():
    pkg_share = get_package_share_directory('ps5_camera')
    default_left_yaml = os.path.join(pkg_share, 'config', 'left.yaml')
    default_right_yaml = os.path.join(pkg_share, 'config', 'right.yaml')

    return LaunchDescription([
        # Launch Arguments
        DeclareLaunchArgument(
            'video_device',
            default_value='/dev/video2',
            description='Path to video device'
        ),
        DeclareLaunchArgument(
            'left_camera_info_url',
            default_value=default_left_yaml,
            description='Path to Left camera calibration YAML file'
        ),
        DeclareLaunchArgument(
            'right_camera_info_url',
            default_value=default_right_yaml,
            description='Path to Right camera calibration YAML file'
        ),
        DeclareLaunchArgument(
            'approximate_sync',
            default_value='True',
            description='Use approximate sync for stereo_image_proc'
        ),

        # 1. Static TF Publisher (отключен прямой map -> camera_link_optical во избежание конфликта двух родителей в TF, используется цепочка map -> camera_link -> camera_link_optical ниже)
        # Node(
        #     package='tf2_ros',
        #     executable='static_transform_publisher',
        #     name='static_tf_pub',
        #     arguments=['0', '0', '0', '0', '0', '0', 'map', 'camera_link_optical']
        # ),

        # 2. PS5 Stereo Camera Driver Node
        Node(
            package='ps5_camera',
            executable='ps5_stereo_node',
            name='ps5_stereo_node',
            output='screen',
            parameters=[{
                'video_device': LaunchConfiguration('video_device'),
                'width': 2560,
                'height': 800,
                'fps': 30,
                'frame_id': 'camera_link_optical',
                'left_camera_info_url': LaunchConfiguration('left_camera_info_url'),
                'right_camera_info_url': LaunchConfiguration('right_camera_info_url'),
            }]
        ),

        # 3. Stereo Processing Container (Rectification, Disparity, PointCloud)
        ComposableNodeContainer(
            name='stereo_processing_container',
            namespace='',
            package='rclcpp_components',
            executable='component_container_mt',
            composable_node_descriptions=[
                # Rectify Left Camera
                ComposableNode(
                    package='image_proc',
                    plugin='image_proc::RectifyNode',
                    name='rectify_mono_left',
                    namespace='left',
                    remappings=[
                        ('image', 'image_raw'),
                        ('camera_info', 'camera_info'),
                        ('image_rect', 'image_rect')
                    ]
                ),
                # Rectify Right Camera
                ComposableNode(
                    package='image_proc',
                    plugin='image_proc::RectifyNode',
                    name='rectify_mono_right',
                    namespace='right',
                    remappings=[
                        ('image', 'image_raw'),
                        ('camera_info', 'camera_info'),
                        ('image_rect', 'image_rect')
                    ]
                ),
                # Disparity Node
                ComposableNode(
                    package='stereo_image_proc',
                    plugin='stereo_image_proc::DisparityNode',
                    name='disparity_node',
                    namespace='',
                    parameters=[{
                        'stereo_algorithm': 0,          # 0 = StereoBM (30 FPS), 1 = StereoSGBM
                        'approximate_sync': True,
                        'queue_size': 30,
                        'correlation_window_size': 15,
                        'min_disparity': 0,
                        'disparity_range': 128,
                        'uniqueness_ratio': 15.0,
                    }]
                ),
                # PointCloud Node
                ComposableNode(
                    package='stereo_image_proc',
                    plugin='stereo_image_proc::PointCloudNode',
                    name='point_cloud_node',
                    namespace='',
                    parameters=[{
                        'approximate_sync': True,
                        'queue_size': 30,
                        'avoid_point_cloud_padding': True,
                    }],
                    remappings=[
                        ('left/image_rect_color', 'left/image_rect'),
                    ]
                ),
            ],
            output='screen'
        ),

        # 4. Disparity Color Visualizer Node (for RViz2 Image display)
        Node(
            package='ps5_camera',
            executable='disparity_color_node',
            name='disparity_color_node',
            output='screen',
            respawn=True,
            respawn_delay=2.0,
            parameters=[{
                'colormap': 'TURBO',
            }]
        ),

        # 5. TF
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='world_to_camera_base',
            arguments=['0', '0', '0', '0', '0', '0', 'map', 'camera_link']
        ),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='camera_base_to_optical',
            arguments=[
                '0', '0', '0',          # x, y, z (смещение)
                '-1.5707', '0', '-1.5707', # Roll, Pitch, Yaw в радианах (-90° и -90°)
                'camera_link',          # Родительский фрейм
                'camera_link_optical'   # Дочерний оптический фрейм
            ]
        ),
    ])
