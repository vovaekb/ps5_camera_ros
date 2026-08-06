import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    # Определение путей к launch-файлам левой и правой камеры
    try:
        pkg_dir = get_package_share_directory('ps5_camera')
        left_launch_path = os.path.join(pkg_dir, 'launch', 'left_rectify.launch.py')
        right_launch_path = os.path.join(pkg_dir, 'launch', 'right_rectify.launch.py')
    except Exception:
        current_dir = os.path.dirname(os.path.realpath(__file__))
        left_launch_path = os.path.join(current_dir, 'left_rectify.launch.py')
        right_launch_path = os.path.join(current_dir, 'right_rectify.launch.py')

    return LaunchDescription([
        # Включение launch-файла левой камеры
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(left_launch_path)
        ),
        # Включение launch-файла правой камеры
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(right_launch_path)
        ),
    ])
