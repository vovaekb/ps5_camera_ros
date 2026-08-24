import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

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

        # 1. Static TF Publisher (map -> camera_link_optical)
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='camera_to_optical_tf',
            arguments=['0', '0', '0', '-1.5707963', '0', '-1.5707963', 'camera_link', 'camera_link_optical']
        ),

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

        # 3. Image Proc for Left Camera (Produces /left/image_rect)
        Node(
            package='image_proc',
            executable='image_proc',
            name='left_image_proc',
            namespace='left',
            output='screen',
            remappings=[('image', 'image_raw')]
        ),

        # 4. Image Proc for Right Camera (Produces /right/image_rect)
        Node(
            package='image_proc',
            executable='image_proc',
            name='right_image_proc',
            namespace='right',
            output='screen',
            remappings=[('image', 'image_raw')]
        ),

        # 5. Disparity Node (Produces /disparity)
        Node(
            package='stereo_image_proc',
            executable='disparity_node',
            name='disparity_node',
            output='screen',
            parameters=[{
                'approximate_sync': True,
            }]
        ),

        # 6. PointCloud Node (Produces /points2)
        Node(
            package='stereo_image_proc',
            executable='point_cloud_node',
            name='point_cloud_node',
            output='screen',
            parameters=[{
                'approximate_sync': True,
            }],
            remappings=[
                ('left/image_rect_color', 'left/image_rect'),
            ]
        ),
    ])
