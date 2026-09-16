import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from stereo_msgs.msg import DisparityImage
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np

class DisparityColorNode(Node):
    def __init__(self):
        super().__init__('disparity_color_node')

        self.declare_parameter('colormap', 'TURBO')
        colormap_name = self.get_parameter('colormap').value.upper()

        colormap_dict = {
            'TURBO': cv2.COLORMAP_TURBO if hasattr(cv2, 'COLORMAP_TURBO') else cv2.COLORMAP_JET,
            'JET': cv2.COLORMAP_JET,
            'VIRIDIS': cv2.COLORMAP_VIRIDIS if hasattr(cv2, 'COLORMAP_VIRIDIS') else cv2.COLORMAP_JET,
            'INFERNO': cv2.COLORMAP_INFERNO if hasattr(cv2, 'COLORMAP_INFERNO') else cv2.COLORMAP_JET,
            'MAGMA': cv2.COLORMAP_MAGMA if hasattr(cv2, 'COLORMAP_MAGMA') else cv2.COLORMAP_JET,
            'PLASMA': cv2.COLORMAP_PLASMA if hasattr(cv2, 'COLORMAP_PLASMA') else cv2.COLORMAP_JET,
        }
        self.colormap = colormap_dict.get(colormap_name, cv2.COLORMAP_JET)

        self.bridge = CvBridge()

        # Best effort subscriber matches both Reliable and Best Effort publishers
        sub_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=5
        )

        # Reliable publisher matches RViz2 default Image display
        pub_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=5
        )

        self.sub = self.create_subscription(
            DisparityImage,
            'disparity',
            self.disparity_callback,
            sub_qos
        )

        self.pub = self.create_publisher(
            Image,
            'disparity_color',
            pub_qos
        )

        self.get_logger().info(
            f"Disparity Color Node started. Subscribing to 'disparity', publishing to 'disparity_color' (Colormap: {colormap_name})"
        )

    def disparity_callback(self, msg: DisparityImage):
        try:
            # Convert float32 ROS Image to OpenCV numpy array
            disp = self.bridge.imgmsg_to_cv2(msg.image, desired_encoding='32FC1')

            # Mask out invalid disparities (negative or <= min_disparity)
            min_disp = max(0.0, float(msg.min_disparity))
            max_disp = float(msg.max_disparity)
            if max_disp <= min_disp:
                max_disp = min_disp + 128.0

            valid_mask = (disp > min_disp) & (disp <= max_disp) & (~np.isnan(disp))

            # Normalize valid disparity values to [0, 255]
            disp_range = max_disp - min_disp
            disp_scaled = np.zeros(disp.shape, dtype=np.uint8)

            if disp_range > 0:
                disp_scaled[valid_mask] = np.clip(
                    ((disp[valid_mask] - min_disp) / disp_range) * 255.0,
                    0,
                    255
                ).astype(np.uint8)

            # Apply colormap
            color_img = cv2.applyColorMap(disp_scaled, self.colormap)

            # Set invalid / zero regions to pure black
            color_img[~valid_mask] = [0, 0, 0]

            # Convert to ROS Image and publish
            out_msg = self.bridge.cv2_to_imgmsg(color_img, encoding='bgr8')
            out_msg.header = msg.header
            self.pub.publish(out_msg)

        except Exception as e:
            self.get_logger().error(f"Error converting disparity image: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = DisparityColorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
