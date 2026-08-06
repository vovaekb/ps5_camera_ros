from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # Аргументы запуска
        DeclareLaunchArgument(
            'namespace',
            default_value='right',
            description='Пространство имен для правой камеры'
        ),
        DeclareLaunchArgument(
            'image_topic',
            default_value='image_raw',
            description='Входной топик сырого изображения (относительно namespace)'
        ),
        DeclareLaunchArgument(
            'camera_info_topic',
            default_value='camera_info',
            description='Входной топик информации о камере (относительно namespace)'
        ),

        # Узел ректификации кадров правой камеры (image_proc)
        Node(
            package='image_proc',
            executable='image_proc',
            name='right_image_proc',
            namespace=LaunchConfiguration('namespace'),
            output='screen',
            remappings=[
                ('image', LaunchConfiguration('image_topic')),
                ('camera_info', LaunchConfiguration('camera_info_topic')),
            ]
        ),
    ])
