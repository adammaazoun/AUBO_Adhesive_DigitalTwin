#!/bin/bash
# AUBO Robot Startup Script
# Run this once after booting the VM

WS=/root/Desktop/aubo_ros2_ws

# Terminal 1 — Robot Driver
xfce4-terminal --title="1. Robot Driver" -e "bash -c '
  source /opt/ros/humble/setup.bash
  source $WS/install/setup.bash
  echo === Starting Robot Driver ===
  ros2 launch aubo_ros2_driver aubo_control.launch.py \
    aubo_type:=aubo_i10 \
    robot_ip:=127.0.0.1 \
    use_fake_hardware:=false 
  exec bash'" &

sleep 5

# Terminal 2 — MoveIt
xfce4-terminal --title="2. MoveIt" -e "bash -c '
  source /opt/ros/humble/setup.bash
  source $WS/install/setup.bash
  echo === Starting MoveIt ===
  ros2 launch aubo_moveit_config aubo_moveit.launch.py aubo_type:=aubo_i10
  exec bash'" &

sleep 5





echo "All terminals launched!"
echo "Phone: ws://192.168.137.1:9091"
