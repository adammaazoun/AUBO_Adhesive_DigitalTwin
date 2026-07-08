# ── config.py ─────────────────────────────────────────────
IMAGE_PATH      = "photos/piece.png"
PIECE_DATA_JSON = "piece_data.json"
OUTPUT_JSON     = "glue_path.json"
Z_HOVER         = 110.7
ARC_EPSILON_PX  = 8.0
LINE_TOL_MM     = 0.8
ARC_RMSE_MM     = 0.7
MIN_ARC_DEG     = 12.0
SHAPE_THRESH    = 3.0
MIN_AREA        = 500 
DEBUG           = False
PAPER_CORNERS_ROBOT = {
    "top_right": (-1019, 829.37),
    "top_left": (-727, 831.32),   # unchanged
    "bottom_right": (-1019, 623),
    "bottom_left": (-727, 627),
}

ROBOT_CORNERS = {
    1: (-742.00, 642.00),    
    3: (-742.00, 816.37),    
    0: (-1004.00, 638.00),   
    2: (-1004.00, 814.32),   
}