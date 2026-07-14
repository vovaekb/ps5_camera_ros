# ps5_camera_ros

A ROS 2 package to interface, stream, and process video from the Sony PlayStation 5 HD Camera. 

Unlike standard UVC webcams, the PS5 HD Camera does not store its operational firmware onboard. Upon connection via USB, it initializes in a bootloader state (`USB BOOT`) and requires a firmware binary to be uploaded dynamically before it can function as a standard video device.

This guide outlines how to prepare your Linux (Ubuntu) environment, configure automated firmware uploading via `udev`, and run the ROS 2 driver.

---

## Prerequisites & Hardware Requirements

1. **Operating System:** Ubuntu Linux (tested on native environments).
2. **ROS 2 Distribution:** Compatible with standard modern distributions (e.g., Humble, Iron, Jazzy).
3. **USB Port:** The camera **must** be connected to a **USB 3.0 (or higher) port** (usually color-coded blue or labeled with an SS/SuperSpeed logo). It will not initiate or stream properly over USB 2.0.

---

## 1. System Preparation & Firmware Setup

### Step 1: Install Dependencies
To fetch, compile, or run the firmware loader utilities, ensure you have the required build tools and `libusb` development headers installed:

```bash
sudo apt update
sudo apt install build-essential git libusb-1.0-0-dev pkg-config
```

### Step 2: Extract the Firmware
Due to copyright restrictions, the proprietary Sony firmware binary (`firmware.bin`) cannot be directly redistributed in this repository. You must obtain it either from an official PlayStation 5 update or use public third-party tools to extract it.

Place your extracted file inside a dedicated directory on your system, for example:
`/usr/local/lib/ps5-camera/firmware.bin`

### Step 3: Install a Firmware Loader
The system needs an application capable of pushing the `firmware.bin` to the device over USB. 
You can use popular open-source loaders such as the Rust-based `PlayStation-Camera-Firmware-Loader` or Python/C-based wrappers available on GitHub (e.g., `ps5_hdcam` utilities). 

Ensure the loader binary is compiled and accessible. For this guide, we assume the command to load firmware is available at `/usr/local/bin/ps5_cam_load`.

---

## 2. Automating Firmware Loading via udev

To prevent having to manually run the upload script every time you plug in the camera or reboot your PC, configure a custom `udev` rule to trigger the upload automatically.

1. Check the default bootloader Vendor ID (VID) and Product ID (PID) by running `lsusb` before the firmware is loaded. It typically registers as `054c:0c45` (Sony Corp. PS5 Camera Bootloader).

2. Create a new udev rule file:
   ```bash
   sudo nano /etc/udev/rules.d/99-ps5-camera.rules
   ```

3. Add the following line (replace `/usr/local/bin/ps5_cam_load` and `/usr/local/lib/ps5-camera/firmware.bin` with the exact absolute paths to your loader script and firmware file):
   ```text
   SUBSYSTEM=="usb", ATTR{idVendor}=="054c", ATTR{idProduct}=="0c45", RUN+="/usr/local/bin/ps5_cam_load /usr/local/lib/ps5-camera/firmware.bin"
   ```

4. Reload the `udev` rules to apply the changes:
   ```bash
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

5. **Verify:** Unplug the camera, plug it back into a USB 3.0 port, and check `lsusb` and `dmesg`. The device ID should switch to the post-firmware mode (typically identifying as an OmniVision-based standard UVC camera chip or `USB Camera-OV580`), and video interfaces should appear under `/dev/video*`.

---

## 3. Video Device & Permissions

Make sure your current Linux user belongs to the `video` group so ROS 2 can capture the video stream without requiring `sudo`:

```bash
sudo usermod -aG video $USER
```
*Note: You may need to log out and log back in for the group changes to take effect.*

Use `v4l-utils` to identify which `/dev/videoX` paths map to the newly initialized stereo camera:
```bash
sudo apt install v4l-utils
v4l2-ctl --list-devices
```
The camera outputs a unified side-by-side combined stereo frame (both left and right sensors packed into a single widescreen image frame).

---

## 4. Installation & Usage in ROS 2

### Building the Package
Clone this repository into your ROS 2 workspace's `src` folder, install standard ROS 2 camera dependencies, and build:

```bash
cd ~/ros2_ws/src
git clone https://github.com/vovaekb/ps5_camera_ros.git
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --packages-select ps5_camera_ros
source install/setup.bash
```

### Running the Node
Launch the driver node by passing the verified video device configuration path:

```bash
ros2 launch ps5_camera_ros ps5_camera.launch.py video_device:=/dev/video0
```