import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, ComposableNodeContainer
from launch_ros.descriptions import ComposableNode

def generate_launch_description():
    default_left_yaml = '/home/vlad/left.yaml'
    default_right_yaml = '/home/vlad/right.yaml'

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

        # 1. PS5 Stereo Camera Driver Node
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

        # 2. Stereo Image Processing Container (Disparity + PointCloud)
        ComposableNodeContainer(
            name='stereo_image_proc_container',
            namespace='',
            package='rclcpp_components',
            executable='component_container',
            composable_node_descriptions=[
                ComposableNode(
                    package='stereo_image_proc',
                    plugin='stereo_image_proc::DisparityNode',
                    name='disparity_node',
                    parameters=[{
                        'approximate_sync': LaunchConfiguration('approximate_sync'),
                    }]
                ),
                ComposableNode(
                    package='stereo_image_proc',
                    plugin='stereo_image_proc::PointCloudNode',
                    name='point_cloud_node',
                    parameters=[{
                        'approximate_sync': LaunchConfiguration('approximate_sync'),
                    }]
                ),
            ],
            output='screen',
        )
    ])
