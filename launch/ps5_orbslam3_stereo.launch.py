import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # Default Paths
    default_left_calib = '/home/vlad/ps5 calibration/left.yaml'
    default_right_calib = '/home/vlad/ps5 calibration/right.yaml'
    default_config = '/home/vlad/configs/ps5_orbslam3_rectified.yaml'
    default_vocab = '/home/vlad/Software/ORB_SLAM3/Vocabulary/ORBvoc.txt'
    default_rviz_config = '/home/vlad/ros2_ws/src/ps5_camera/config/ps5_vslam.rviz'

    # Launch Configurations
    video_device = LaunchConfiguration('video_device')
    rectify = LaunchConfiguration('rectify')
    vocab_path = LaunchConfiguration('vocab_path')
    config_path = LaunchConfiguration('config_path')
    enable_rviz = LaunchConfiguration('rviz')
    frame_id = LaunchConfiguration('frame_id')

    return LaunchDescription([
        # ---------------- Arguments ----------------
        DeclareLaunchArgument(
            'video_device',
            default_value='/dev/video2',
            description='Path to video device for PS5 HD Camera'
        ),
        DeclareLaunchArgument(
            'rectify',
            default_value='True',
            description='Use ROS 2 image_proc to rectify stereo images before ORB-SLAM3'
        ),
        DeclareLaunchArgument(
            'vocab_path',
            default_value=default_vocab,
            description='Path to ORB Vocabulary file (ORBvoc.txt or orb_vocab.dbow2)'
        ),
        DeclareLaunchArgument(
            'config_path',
            default_value=default_config,
            description='Path to ORB-SLAM3 configuration YAML file'
        ),
        DeclareLaunchArgument(
            'rviz',
            default_value='False',
            description='Launch RViz2 for visualization'
        ),
        DeclareLaunchArgument(
            'frame_id',
            default_value='camera_link_optical',
            description='Frame ID for camera optical center'
        ),

        # ---------------- 1. PS5 Stereo Camera Driver ----------------
        Node(
            package='ps5_camera',
            executable='ps5_stereo_node',
            name='ps5_stereo_node',
            output='screen',
            parameters=[{
                'video_device': video_device,
                'width': 2560,
                'height': 800,
                'fps': 30,
                'frame_id': frame_id,
                'left_camera_info_url': default_left_calib,
                'right_camera_info_url': default_right_calib,
            }]
        ),

        # ---------------- 2. Image Rectification Nodes (image_proc) ----------------
        # Left camera rectification
        Node(
            package='image_proc',
            executable='image_proc',
            name='left_image_proc',
            namespace='left',
            output='screen',
            condition=IfCondition(rectify),
            remappings=[
                ('image', 'image_raw'),
                ('camera_info', 'camera_info'),
            ]
        ),
        # Right camera rectification
        Node(
            package='image_proc',
            executable='image_proc',
            name='right_image_proc',
            namespace='right',
            output='screen',
            condition=IfCondition(rectify),
            remappings=[
                ('image', 'image_raw'),
                ('camera_info', 'camera_info'),
            ]
        ),

        # ---------------- 3. ORB-SLAM3 Stereo Node ----------------
        # Mode A: With pre-rectified images from image_proc (doRectify = false)
        Node(
            package='orbslam3',
            executable='stereo',
            name='orb_slam3_stereo',
            output='screen',
            condition=IfCondition(rectify),
            arguments=[vocab_path, config_path, 'false'],
            remappings=[
                ('camera/left', '/left/image_rect'),
                ('camera/right', '/right/image_rect'),
            ]
        ),

        # Mode B: With raw unrectified images (ORB-SLAM3 node does cv::remap: doRectify = true)
        Node(
            package='orbslam3',
            executable='stereo',
            name='orb_slam3_stereo_raw',
            output='screen',
            condition=UnlessCondition(rectify),
            arguments=[vocab_path, config_path, 'true'],
            remappings=[
                ('camera/left', '/left/image_raw'),
                ('camera/right', '/right/image_raw'),
            ]
        ),

        # ---------------- 4. RViz2 Visualization (Optional) ----------------
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            condition=IfCondition(enable_rviz),
            arguments=['-d', default_rviz_config]
        )
    ])
