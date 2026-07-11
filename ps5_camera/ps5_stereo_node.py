import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge
import cv2
import yaml
import threading
import time
import os

class PS5StereoNode(Node):
    def __init__(self):
        super().__init__('ps5_stereo_node')
        
        # Declare parameters
        self.declare_parameter('video_device', '/dev/video2')
        self.declare_parameter('width', 2560)  # Total width (e.g. 2560 for 2x 1280x800)
        self.declare_parameter('height', 800)   # Total height (e.g. 800)
        self.declare_parameter('fps', 30)
        self.declare_parameter('frame_id', 'camera_link_optical')
        self.declare_parameter('left_camera_info_url', '')
        self.declare_parameter('right_camera_info_url', '')
        
        # Get parameters
        self.video_device = self.get_parameter('video_device').value
        self.total_width = int(self.get_parameter('width').value)
        self.height = int(self.get_parameter('height').value)
        self.fps = int(self.get_parameter('fps').value)
        self.frame_id = self.get_parameter('frame_id').value
        self.left_info_url = self.get_parameter('left_camera_info_url').value
        self.right_info_url = self.get_parameter('right_camera_info_url').value
        
        self.single_width = self.total_width // 2
        
        self.get_logger().info(f"Starting PS5 Stereo Camera node.")
        self.get_logger().info(f"Device: {self.video_device}, Resolution: {self.total_width}x{self.height} (Split: {self.single_width}x{self.height} per eye)")
        
        # Create publishers
        self.left_pub = self.create_publisher(Image, 'left/image_raw', 10)
        self.left_info_pub = self.create_publisher(CameraInfo, 'left/camera_info', 10)
        self.right_pub = self.create_publisher(Image, 'right/image_raw', 10)
        self.right_info_pub = self.create_publisher(CameraInfo, 'right/camera_info', 10)
        
        self.br = CvBridge()
        
        # Load Camera Info
        self.left_info = self.load_camera_info(self.left_info_url, self.frame_id, is_right=False)
        self.right_info = self.load_camera_info(self.right_info_url, self.frame_id, is_right=True)
        
        # Initialize OpenCV VideoCapture
        self.cap = cv2.VideoCapture(self.video_device, cv2.CAP_V4L2)
        if not self.cap.isOpened():
            self.get_logger().error(f"Failed to open video device {self.video_device}!")
            raise RuntimeError(f"Could not open device {self.video_device}")
            
        # Set parameters
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.total_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        
        # Verify resolution
        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if actual_w != self.total_width or actual_h != self.height:
            self.get_logger().warn(f"Requested {self.total_width}x{self.height}, but got {actual_w}x{actual_h} from camera.")
            self.total_width = actual_w
            self.height = actual_h
            self.single_width = actual_w // 2
            
            # Recalculate camera infos
            if not self.left_info_url:
                self.left_info = self.get_default_camera_info(self.single_width, self.height, self.frame_id, is_right=False)
            if not self.right_info_url:
                self.right_info = self.get_default_camera_info(self.single_width, self.height, self.frame_id, is_right=True)

        # Start thread
        self.running = True
        self.thread = threading.Thread(target=self.capture_loop)
        self.thread.start()
        
    def load_camera_info(self, url, frame_id, is_right):
        if url and os.path.exists(url):
            try:
                with open(url, 'r') as f:
                    calib = yaml.safe_load(f)
                
                info = CameraInfo()
                info.header.frame_id = frame_id
                info.width = calib['image_width']
                info.height = calib['image_height']
                info.distortion_model = calib['distortion_model']
                info.d = list(map(float, calib['distortion_coefficients']['data']))
                info.k = list(map(float, calib['camera_matrix']['data']))
                info.r = list(map(float, calib['rectification_matrix']['data']))
                info.p = list(map(float, calib['projection_matrix']['data']))
                self.get_logger().info(f"Loaded calibration for {'right' if is_right else 'left'} camera from {url}")
                return info
            except Exception as e:
                self.get_logger().error(f"Failed to parse calibration YAML from {url}: {e}. Using default.")
        
        # Return default if file not provided or failed to load
        return self.get_default_camera_info(self.single_width, self.height, frame_id, is_right)

    def get_default_camera_info(self, width, height, frame_id, is_right=False):
        info = CameraInfo()
        info.header.frame_id = frame_id
        info.width = width
        info.height = height
        info.distortion_model = "plumb_bob"
        info.d = [0.0, 0.0, 0.0, 0.0, 0.0]
        
        # Default pinhole approximations (focal length ~ width)
        f = float(width)
        cx = float(width) / 2.0
        cy = float(height) / 2.0
        
        info.k = [
            f,   0.0, cx,
            0.0, f,   cy,
            0.0, 0.0, 1.0
        ]
        info.r = [
            1.0, 0.0, 0.0,
            0.0, 1.0, 0.0,
            0.0, 0.0, 1.0
        ]
        
        # Translation baseline (e.g. 50mm = 0.05m)
        tx = 0.0
        if is_right:
            tx = -f * 0.05
            
        info.p = [
            f,   0.0, cx,  tx,
            0.0, f,   cy,  0.0,
            0.0, 0.0, 1.0, 0.0
        ]
        return info

    def capture_loop(self):
        # Calculate target sleep to match frame rate
        sleep_time = 1.0 / self.fps
        
        while self.running and rclpy.ok():
            start_t = time.time()
            ret, frame = self.cap.read()
            
            if not ret or frame is None:
                self.get_logger().warn("Failed to capture image frame from PS5 camera.")
                time.sleep(0.01)
                continue
                
            # Get current stamp
            stamp = self.get_clock().now().to_msg()
            
            # Split frame
            left_frame = frame[:, :self.single_width]
            right_frame = frame[:, self.single_width:]
            
            # Convert to ROS Image messages
            try:
                left_msg = self.br.cv2_to_imgmsg(left_frame, encoding='bgr8')
                right_msg = self.br.cv2_to_imgmsg(right_frame, encoding='bgr8')
                
                left_msg.header.stamp = stamp
                left_msg.header.frame_id = self.frame_id
                
                right_msg.header.stamp = stamp
                right_msg.header.frame_id = self.frame_id
                
                # Publish images
                self.left_pub.publish(left_msg)
                self.right_pub.publish(right_msg)
                
                # Publish camera info with matching timestamp
                self.left_info.header.stamp = stamp
                self.right_info.header.stamp = stamp
                
                self.left_info_pub.publish(self.left_info)
                self.right_info_pub.publish(self.right_info)
            except Exception as e:
                self.get_logger().error(f"Error publishing frames: {e}")
            
            # Control frame rate
            elapsed = time.time() - start_t
            if elapsed < sleep_time:
                time.sleep(sleep_time - elapsed)

    def destroy_node(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join()
        if self.cap.isOpened():
            self.cap.release()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = PS5StereoNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
