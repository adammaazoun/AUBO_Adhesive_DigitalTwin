# Tunibot — Adhesive Digital Twin

A full-stack web application for controlling and monitoring an Aubo i10 industrial glue-dispensing robot system. Includes role-based access control (Visitor, Operator, Admin, Integrator), a piece catalog, run history, live robot control, and a computer-vision-driven glue pipeline on the Robot PC side.

## Architecture Overview

The system has three parts that run independently and talk to each other over the network:

```
┌─────────────┐      REST (JWT)      ┌─────────────┐      REST / MJPEG      ┌──────────────┐
│  Frontend    │ ───────────────────▶ │  Backend     │ ─────────────────────▶ │  Robot PC     │
│  (React)     │ ◀─────────────────── │  (FastAPI)   │ ◀───────────────────── │  (Flask +     │
│  :5173       │                      │  :8000       │                        │  vision       │
└─────────────┘                      └──────┬───────┘                        │  pipeline)    │
                                              │                                │  :5001        │
                                       PostgreSQL                              │  :8095 (cam)  │
                                       :5432                                   └──────┬───────┘
                                                                                        │ UDP
                                                                                        ▼
                                                                                ┌──────────────┐
                                                                                │  Unity        │
                                                                                │  (belt sim +  │
                                                                                │  ROS TCP)     │
                                                                                └──────┬───────┘
                                                                                        │ TCP
                                                                                        ▼
                                                                                ┌──────────────┐
                                                                                │  ROS2 /       │
                                                                                │  Aubo VM      │
                                                                                │  :10000       │
                                                                                └──────────────┘
```

- **Frontend** talks only to the **Backend** (never directly to the Robot PC).
- **Backend** stores users/pieces/history/settings in PostgreSQL, and proxies robot commands + parameters to the **Robot PC** over REST.
- **Robot PC** runs the live computer-vision pipeline (piece detection, glue-path generation) and talks to the physical/simulated robot via JSON-RPC, and to **Unity** via UDP for belt simulation sync.
- **Unity** connects to **ROS2** (running in the Aubo VM) via the ROS TCP Connector for robot visualization/simulation.

## Tech Stack

**Backend:** FastAPI, PostgreSQL, SQLAlchemy, JWT authentication
**Frontend:** React (Vite), TypeScript, Tailwind CSS, shadcn/ui
**Robot PC:** Python, Flask, OpenCV (computer vision pipeline)
**Simulation:** Unity, ROS2, ROS-TCP-Connector

## Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL (via Docker or local install)
- Unity (with ROS-TCP-Connector package) for simulation work
- Access to the Aubo VM / ROS2 workspace for robot communication

## 1. Backend Setup

```bash
cd backend
python -m venv venv

# Activate the virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

Create a PostgreSQL database (default expected name: `tunibot_db`), then update the connection string in `backend/database.py` to match your credentials:

```python
SQLALCHEMY_DATABASE_URL = "postgresql://<user>:<password>@localhost:5432/tunibot_db"
```

Run the server:

```bash
uvicorn main:app --reload
```

The API is available at `http://127.0.0.1:8000`, with interactive docs at `http://127.0.0.1:8000/docs`.

## 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The app is available at `http://localhost:5173`.

### First-Time Setup

1. Start the backend, then go to `http://127.0.0.1:8000/docs`.
2. Use `POST /users/signup` to create your first account with `"role": "admin"`.
3. Log in through the frontend at `http://localhost:5173` with that account.
4. Go to **Settings** in the app and set the Robot PC's URL (e.g. `http://127.0.0.1:5001`) so the backend can send commands to it.

## 3. Robot PC Setup (Vision + Control Pipeline)

This is the Python application (`stable/` folder) that runs the camera-based piece detection, glue path computation, and robot/Unity communication.

```bash
cd stable
pip install -r requirements.txt   # opencv-python, flask, numpy, etc.
python app.py
```

This starts:
- A Flask server on **port 5001** with `/start`, `/stop`, `/status`, `/parameters` endpoints (called by the backend).
- A live MJPEG debug camera stream on **port 8095** (only active when `config.py` has `DEBUG = True`).
- A UDP listener on **port 9998** for live parameter updates from Unity (speed/acceleration/blend radius/belt encoder).

Key config values to check/update in `config.py` and `robot_controller.py` for your environment:
- `ROBOT_IP` / `ROBOT_PORT` — the Aubo robot controller's JSON-RPC address (default port `30004`).
- `UNITY_IP` — where Unity is running (`127.0.0.1` if on the same machine as this script).

## 4. Unity + ROS2 Setup

The Aubo ROS2 workspace runs inside a VM. From a terminal in the VM:

```bash
cd aubo_ros2_ws
colcon build
source install/setup.bash
./aubo_startup.sh
ros2 service call /set_glue_mode std_srvs/srv/SetBool "{data: true}"
ros2 run ros_tcp_endpoint default_server_endpoint --ros-args -p ROS_IP:=0.0.0.0 -p ROS_TCP_PORT:=10000
```

In Unity, open **Robotics → ROS Settings** and set the IP to the VM's actual network address (find it inside the VM with `hostname -I` — note this is usually **not** the `.1` address of the subnet, which is typically the host machine, not the VM) and port `10000`. Then launch the scene and start the simulation.

## Project Structure

```
tunibot-app/
├── backend/
│   ├── main.py            # App entrypoint
│   ├── database.py        # DB connection
│   ├── models.py          # SQLAlchemy models
│   ├── schemas.py         # Pydantic request/response schemas
│   ├── auth.py             # JWT auth + role-based permissions
│   └── routers/            # API endpoints (users, pieces, history, settings, robot)
├── frontend/
│   ├── src/
│   │   ├── pages/           # Dashboard, Robot View, History, Pieces, Users, Settings, etc.
│   │   ├── components/      # Shared layout and UI components
│   │   ├── context/         # Auth context (JWT session handling)
│   │   └── lib/              # API client, types, mock data
└── stable/                  # Robot PC application
    ├── app.py                # Flask server (start/stop/status/parameters)
    ├── robot_controller.py   # JSON-RPC to Aubo robot + UDP to Unity
    ├── vision_detector.py    # Camera-based piece detection & glue path generation
    ├── pipeline.py            # Orchestrates the continuous scan-and-glue loop
    ├── geometry.py            # Geometry helper functions
    ├── debug_stream.py        # MJPEG debug camera stream
    └── config.py               # Tunable constants (thresholds, corner calibration, etc.)
```

## User Roles

- **Visitor** — view-only access to the dashboard
- **Operator** — can run production, view history and pieces
- **Admin** — manages pieces, users, and settings
- **Integrator** — full access, including manual robot control and calibration

## What's Built vs. What's Next

**Fully working:** authentication, role-based access, piece/history/user CRUD, robot start/stop/parameters (proxied to the Robot PC), live camera feed on the Dashboard, the vision/glue-path pipeline on the Robot PC.

**Next steps / open work:**
- Full Unity WebGL embedding into the frontend (currently a placeholder — the frontend, backend, and Robot PC are all ready for this; Unity needs a WebGL export and a WebSocket-based connector, since browsers can't use the TCP-based ROS connection Unity currently uses).
- Linking the web app's Piece catalog to the Robot PC's live vision pipeline (currently the vision pipeline uses a single hardcoded reference piece in `piece_data.json`, independent of the web app's Piece database).
- PDF import parsing for pieces (currently manual entry only).
- Export summary/report generation from History.
- Real-time joystick jog commands (currently UI-only, not wired to a live control channel).
