
import streamlit as st
import cv2
import pandas as pd
from datetime import datetime

from sliplearn.config import load_config
from sliplearn.vision import VisionSystem
from sliplearn.communication import GripperLink
from sliplearn.control import AdaptiveGripController
from sliplearn.object_catalog import APPROVED_OBJECTS, check_object


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="SlipLearn Robotics",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# INDUSTRIAL DESIGN THEME
# ============================================================

st.markdown("""
<style>

:root {
    --yellow: #F5C400;
    --dark: #20252B;
    --sidebar: #191E24;
    --background: #F2F4F7;
    --white: #FFFFFF;
    --text: #242A31;
    --muted: #77818C;
    --border: #E0E5EA;
}

.stApp {
    background: #F2F4F7;
    color: #242A31;
}

.block-container {
    max-width: 1600px;
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}

[data-testid="stSidebar"] {
    background: #191E24;
    border-right: 1px solid #343A42;
}

[data-testid="stSidebar"] .block-container {
    padding: 1.2rem 1rem;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label {
    color: #D7DDE4;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #FFFFFF !important;
}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    color: #AAB4BE;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label {
    color: #FFFFFF;
}

[data-testid="stSidebar"] hr {
    border-color: #414A54;
}

[data-testid="stHeader"] {
    background: transparent;
}

h1, h2, h3, h4 {
    color: #20252B !important;
    font-weight: 700 !important;
}

p, label {
    color: #56616D;
}

[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E0E5EA;
    border-radius: 9px;
    padding: 16px;
    box-shadow: 0 2px 7px rgba(20,30,40,.04);
}

[data-testid="stMetricLabel"] {
    color: #697580 !important;
}

[data-testid="stMetricValue"] {
    color: #252C34 !important;
    font-weight: 800;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF;
    border: 1px solid #E0E5EA;
    border-radius: 10px;
}

.stButton > button {
    background: #F5C400;
    color: #20252B;
    border: 1px solid #E2B600;
    border-radius: 7px;
    font-weight: 700;
    min-height: 42px;
}

.stButton > button:hover {
    background: #FFD633;
    color: #171B20;
    border-color: #D6A900;
}

hr {
    border-color: #E0E5EA;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# LOAD CONFIGURATION
# ============================================================

cfg = load_config()


# ============================================================
# INITIALIZE SYSTEMS
# ============================================================

if "vision" not in st.session_state:
    st.session_state.vision = VisionSystem(
        cfg.get("camera_index", 0)
    )

if "link" not in st.session_state:
    st.session_state.link = GripperLink(
        cfg.get("serial_port", "AUTO"),
        cfg.get("baud_rate", 115200),
        cfg.get("simulation_mode", True)
    )

if "controller" not in st.session_state:
    st.session_state.controller = AdaptiveGripController(
        cfg.get("force_threshold", 350),
        cfg.get("slip_delta_threshold", 45),
        cfg.get("min_grip_pwm", 20),
        cfg.get("max_grip_pwm", 90),
        cfg.get("grip_step", 5)
    )

if "page" not in st.session_state:
    st.session_state.page = "Overview"

if "camera_running" not in st.session_state:
    st.session_state.camera_running = False

if "detections" not in st.session_state:
    st.session_state.detections = []

if "activity" not in st.session_state:
    st.session_state.activity = []

if "selected_object" not in st.session_state:
    st.session_state.selected_object = None

if "grip_target" not in st.session_state:
    st.session_state.grip_target = 20

if "last_message" not in st.session_state:
    st.session_state.last_message = "System initialized"

if "last_force" not in st.session_state:
    st.session_state.last_force = None

if "adaptive_target" not in st.session_state:
    st.session_state.adaptive_target = 20


# ============================================================
# OBJECT CATALOGUE COMPATIBILITY
# Supports dictionary or list-based catalogues.
# ============================================================

def get_object_names():

    if isinstance(APPROVED_OBJECTS, dict):
        return list(APPROVED_OBJECTS.keys())

    if isinstance(APPROVED_OBJECTS, (list, tuple, set)):
        names = []

        for item in APPROVED_OBJECTS:

            if isinstance(item, dict):
                names.append(
                    item.get("name", item.get("display_name", str(item)))
                )
            else:
                names.append(str(item))

        return names

    return []


def get_object_details(name):

    if isinstance(APPROVED_OBJECTS, dict):

        details = APPROVED_OBJECTS.get(name, {})

        if isinstance(details, dict):
            return details

        return {"display_name": name}

    if isinstance(APPROVED_OBJECTS, (list, tuple, set)):

        for item in APPROVED_OBJECTS:

            if isinstance(item, dict):

                item_name = item.get(
                    "name",
                    item.get("display_name", "")
                )

                if item_name == name:
                    return item

        return {"display_name": name}

    return {"display_name": name}


OBJECT_NAMES = get_object_names()


# ============================================================
# ACTIVITY LOG
# ============================================================

def log_activity(message):

    st.session_state.activity.insert(
        0,
        {
            "Time": datetime.now().strftime("%H:%M:%S"),
            "Activity": str(message)
        }
    )

    st.session_state.activity = (
        st.session_state.activity[:50]
    )


# ============================================================
# CAMERA FUNCTIONS
# ============================================================

def start_camera():

    try:

        result = st.session_state.vision.start()

        st.session_state.camera_running = bool(result)

        if result:
            log_activity("Camera started")
            return True, "Camera started successfully."

        return False, "Camera could not be opened. Check camera connection."

    except Exception as error:

        st.session_state.camera_running = False

        return False, str(error)


def stop_camera():

    try:
        st.session_state.vision.stop()
    except Exception:
        pass

    st.session_state.camera_running = False
    st.session_state.selected_object = None

    log_activity("Camera stopped")


def get_camera_data():

    if not st.session_state.camera_running:
        return None, []

    try:

        frame, detections = st.session_state.vision.read()

        if detections is None:
            detections = []

        st.session_state.detections = detections

        return frame, detections

    except Exception as error:

        st.session_state.last_message = (
            f"Camera read error: {error}"
        )

        return None, []


def format_detection_rows(detections):

    rows = []

    for number, item in enumerate(detections, start=1):

        bbox = item.get("bbox", [0, 0, 0, 0])
        center = item.get("center_px", [0, 0])

        rows.append({
            "ID": number,
            "Object": item.get("label", "Unknown"),
            "Confidence": (
                f'{item["confidence"]}%'
                if item.get("confidence") is not None
                else "Not available"
            ),
            "Centre X": center[0],
            "Centre Y": center[1],
            "Width": bbox[2],
            "Height": bbox[3]
        })

    return rows


# ============================================================
# GRIPPER STATUS
# ============================================================

def get_gripper_status():

    try:
        return st.session_state.link.read_status()
    except Exception:
        return None


# ============================================================
# NAVIGATION SIDEBAR
# ============================================================

NAVIGATION = [
    "Overview",
    "Live AI Vision",
    "Gripper Control",
    "Object Library",
    "Analytics",
    "System Settings"
]

with st.sidebar:

    st.title("SLIPLEARN")

    st.caption("INTELLIGENT ROBOTICS PLATFORM")

    st.divider()

    st.markdown("**MAIN MENU**")

    selected_page = st.radio(
        "Navigation",
        NAVIGATION,
        index=NAVIGATION.index(st.session_state.page),
        label_visibility="collapsed",
        key="sidebar_navigation"
    )

    if selected_page != st.session_state.page:

        st.session_state.page = selected_page
        st.rerun()

    st.divider()

    st.markdown("**SYSTEM STATUS**")

    st.success("SOFTWARE ONLINE")

    st.caption(
        "Operating mode: "
        + (
            "SIMULATION"
            if cfg.get("simulation_mode", True)
            else "HARDWARE CONFIGURED"
        )
    )

    st.caption("AI engine: OpenCV candidate detector")

    st.caption(
        "Camera: "
        + (
            "RUNNING"
            if st.session_state.camera_running
            else "STOPPED"
        )
    )

    st.divider()

    st.caption("SlipLearn Robotics")
    st.caption("Autonomous Gripper Research Project")


# ============================================================
# MAIN HEADER
# ============================================================

header_left, header_right = st.columns([3, 1])

with header_left:

    st.title("SLIPLEARN")

    st.caption(
        "AI-BASED AUTONOMOUS ROBOTIC GRIPPER"
    )

with header_right:

    if cfg.get("simulation_mode", True):
        st.warning("SIMULATION MODE")
    else:
        st.error("HARDWARE CONFIGURED")

st.divider()


# ============================================================
# COMMON CAMERA CONTROLS
# ============================================================

def camera_controls():

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:

        if st.button(
            "Start Camera",
            use_container_width=True
        ):

            success, message = start_camera()

            if success:
                st.success(message)
            else:
                st.error(message)

    with col2:

        if st.button(
            "Stop Camera",
            use_container_width=True
        ):

            stop_camera()

            st.info("Camera stopped.")

    with col3:

        if st.session_state.camera_running:
            st.success("CAMERA RUNNING")
        else:
            st.info("CAMERA STOPPED")


# ============================================================
# PAGE 1: OVERVIEW
# ============================================================

if st.session_state.page == "Overview":

    st.title("Robotics Control Dashboard")

    st.write(
        "Monitor camera input, object identification, "
        "adaptive gripping and system activity."
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("AI Vision", "READY")

    c2.metric(
        "Catalogue Entries",
        len(OBJECT_NAMES)
    )

    c3.metric(
        "Detected Objects",
        len(st.session_state.detections)
    )

    c4.metric(
        "Operating Mode",
        "SIMULATION"
        if cfg.get("simulation_mode", True)
        else "HARDWARE"
    )

    st.divider()

    left, right = st.columns([1.5, 1])

    with left:

        st.subheader("Live Vision Monitoring")

        camera_controls()

        if st.session_state.camera_running:

            frame, detections = get_camera_data()

            if frame is not None:

                rgb = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGR2RGB
                )

                st.image(
                    rgb,
                    channels="RGB",
                    use_container_width=True
                )

            else:

                st.warning("Waiting for camera frame.")

        else:

            st.info(
                "Start the camera from Live AI Vision "
                "to begin monitoring."
            )

    with right:

        st.subheader("Gripper Monitoring")

        st.metric(
            "Grip Command",
            f'{st.session_state.grip_target}%'
        )

        st.progress(
            min(max(st.session_state.grip_target / 100, 0), 1)
        )

        st.write("Controller Status")

        st.info(st.session_state.last_message)

        status = get_gripper_status()

        if status:

            st.metric(
                "Force Reading",
                status.get("force")
                if status.get("force") is not None
                else "—"
            )

            st.caption(
                "Status: " + str(status.get("status", "Unknown"))
            )

        st.warning(
            "Simulated force and grip values are not physical "
            "sensor measurements."
        )

    st.divider()

    st.subheader("System Workflow")

    workflow = st.columns(5)

    workflow_items = [
        ("01", "Camera Input"),
        ("02", "Object Detection"),
        ("03", "Object Approval"),
        ("04", "Grip Estimation"),
        ("05", "Adaptive Control")
    ]

    for col, item in zip(workflow, workflow_items):

        with col:

            with st.container(border=True):

                st.markdown(f"### :orange[{item[0]}]")

                st.write(f"**{item[1]}**")

    st.divider()

    st.subheader("Recent System Activity")

    if st.session_state.activity:

        st.dataframe(
            pd.DataFrame(st.session_state.activity),
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info("No system activity recorded yet.")


# ============================================================
# PAGE 2: LIVE AI VISION
# ============================================================

elif st.session_state.page == "Live AI Vision":

    st.title("Live AI Vision")

    st.write(
        "Monitor the camera and inspect detected object candidates."
    )

    camera_controls()

    st.divider()

    frame, detections = get_camera_data()

    if frame is not None:

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        st.image(
            rgb,
            channels="RGB",
            use_container_width=True
        )

    else:

        st.info("Start the camera to view the live feed.")

    st.divider()

    st.subheader("Detection Results")

    if detections:

        st.dataframe(
            pd.DataFrame(
                format_detection_rows(detections)
            ),
            use_container_width=True,
            hide_index=True
        )

        selected_index = st.selectbox(
            "Select detected object",
            range(len(detections)),
            format_func=lambda i: (
                f'{detections[i].get("label", "Object")} - '
                f'Object {i + 1}'
            )
        )

        st.session_state.selected_object = (
            detections[selected_index]
        )

        selected = detections[selected_index]

        st.write("Selected object details")

        st.json({
            "label": selected.get("label"),
            "bounding_box": selected.get("bbox"),
            "centre_pixels": selected.get("center_px"),
            "area_pixels": selected.get("area_px")
        })

    else:

        st.info("No objects detected yet.")

    st.caption(
        "The included starter vision module detects image contours "
        "as object candidates. It does not perform trained semantic "
        "recognition of all project objects."
    )


# ============================================================
# PAGE 3: GRIPPER CONTROL
# ============================================================

elif st.session_state.page == "Gripper Control":

    st.title("Adaptive Gripper Control")

    st.write(
        "Verify an approved object and configure the grip command."
    )

    st.warning(
        "Simulation mode is recommended. Do not enable physical "
        "actuation until the hardware and safety system are verified."
    )

    st.divider()

    st.subheader("Object Approval")

    if not OBJECT_NAMES:

        st.error("No approved objects found in the catalogue.")

        approved = False
        selected_object = None

    else:

        selected_object = st.selectbox(
            "Select approved object",
            OBJECT_NAMES,
            key="gripper_object"
        )

        weight = st.number_input(
            "Measured object weight (grams)",
            min_value=0.0,
            max_value=500.0,
            value=10.0,
            step=1.0,
            key="gripper_weight"
        )

        approved = False

        if weight > 0:

            try:

                approval_result = check_object(
                    selected_object,
                    weight
                )

                if isinstance(approval_result, tuple):

                    approved = bool(approval_result[0])
                    approval_message = str(approval_result[1])

                else:

                    approved = bool(approval_result)

                    approval_message = (
                        "Object passes approval check."
                        if approved
                        else "Object rejected under current rules."
                    )

                if approved:
                    st.success(approval_message)
                else:
                    st.error(approval_message)

            except Exception as error:

                st.error(
                    f"Approval check error: {error}"
                )

        else:

            st.warning(
                "Enter a positive measured weight before approval."
            )

    st.divider()

    st.subheader("Grip Command")

    target = st.slider(
        "Grip command (%)",
        min_value=0,
        max_value=100,
        value=int(st.session_state.grip_target),
        key="grip_command_slider"
    )

    st.session_state.grip_target = target

    st.progress(target / 100)

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "Apply Grip Command",
            use_container_width=True,
            disabled=not approved
        ):

            if not cfg.get("simulation_mode", True):

                st.error(
                    "Hardware actuation is disabled in this software build."
                )

            else:

                try:

                    connected, message = (
                        st.session_state.link.connect()
                    )

                    if connected:

                        st.session_state.link.send_grip(target)

                        st.session_state.last_message = (
                            f"Simulation grip command: {target}%"
                        )

                        log_activity(
                            f"Grip command {target}% for {selected_object}"
                        )

                        st.success("Simulation grip command sent.")

                    else:

                        st.error(message)

                except Exception as error:

                    st.error(
                        f"Gripper communication error: {error}"
                    )

    with col2:

        if st.button(
            "Release Gripper",
            use_container_width=True
        ):

            if not cfg.get("simulation_mode", True):

                st.error(
                    "Hardware release is disabled in this build."
                )

            else:

                try:

                    st.session_state.link.release()

                    st.session_state.grip_target = 0
                    st.session_state.last_message = "Release command sent"

                    log_activity("Simulation release command")

                    st.success("Simulation release command sent.")

                except Exception as error:

                    st.error(
                        f"Release error: {error}"
                    )

    st.divider()

    st.subheader("Adaptive Grip Controller")

    force = st.number_input(
        "Test force value (simulated)",
        min_value=0.0,
        max_value=1000.0,
        value=100.0,
        step=5.0,
        key="adaptive_force_input"
    )

    if st.button(
        "Run Adaptive Grip Test",
        use_container_width=True
    ):

        new_target, message = (
            st.session_state.controller.update(force)
        )

        st.session_state.adaptive_target = new_target
        st.session_state.grip_target = new_target
        st.session_state.last_message = message

        log_activity(message)

        st.info(message)

        st.metric(
            "Suggested Grip Command",
            f"{new_target}%"
        )

    st.caption(
        "The manually entered force value is simulated. "
        "It is not a real force sensor measurement."
    )


# ============================================================
# PAGE 4: OBJECT LIBRARY
# ============================================================

elif st.session_state.page == "Object Library":

    st.title("Approved Object Library")

    st.write(
        "Review the object catalogue and its configured limits."
    )

    rows = []

    for number, name in enumerate(OBJECT_NAMES, start=1):

        details = get_object_details(name)

        rows.append({
            "Sl. No.": number,
            "Object Name": details.get(
                "display_name",
                details.get("name", name)
            ),
            "Description": details.get(
                "description",
                "Approved catalogue entry"
            ),
            "Maximum Weight (g)": details.get(
                "max_weight_g",
                "Not specified"
            )
        })

    if rows:

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True
        )

        st.metric(
            "Catalogue Entries",
            len(rows)
        )

    else:

        st.warning("No catalogue entries are available.")

    st.divider()

    st.subheader("Object Approval Test")

    if OBJECT_NAMES:

        library_object = st.selectbox(
            "Choose an object",
            OBJECT_NAMES,
            key="library_object"
        )

        library_weight = st.number_input(
            "Object weight (grams)",
            min_value=0.0,
            max_value=500.0,
            value=10.0,
            step=1.0,
            key="library_weight"
        )

        if st.button(
            "Check Object Approval",
            use_container_width=True
        ):

            try:

                result = check_object(
                    library_object,
                    library_weight
                )

                if isinstance(result, tuple):

                    approved_result = bool(result[0])
                    result_message = str(result[1])

                else:

                    approved_result = bool(result)

                    result_message = (
                        "Object approved."
                        if approved_result
                        else "Object rejected."
                    )

                if approved_result:
                    st.success(result_message)
                else:
                    st.error(result_message)

            except Exception as error:

                st.error(
                    f"Approval check error: {error}"
                )


# ============================================================
# PAGE 5: ANALYTICS
# ============================================================

elif st.session_state.page == "Analytics":

    st.title("System Analytics")

    st.write(
        "Review current-session system activity and status."
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Activity Records",
        len(st.session_state.activity)
    )

    c2.metric(
        "Detection Records",
        len(st.session_state.detections)
    )

    c3.metric(
        "Grip Command",
        f'{st.session_state.grip_target}%'
    )

    st.divider()

    st.subheader("Current Detection Summary")

    if st.session_state.detections:

        detection_rows = format_detection_rows(
            st.session_state.detections
        )

        st.dataframe(
            pd.DataFrame(detection_rows),
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No current detection records. Start the camera "
            "from Live AI Vision."
        )

    st.divider()

    st.subheader("Grip Command Status")

    st.progress(
        min(
            max(st.session_state.grip_target / 100, 0.0),
            1.0
        )
    )

    st.caption(
        f'Current grip command: {st.session_state.grip_target}%'
    )

    st.divider()

    st.subheader("Recent System Activity")

    if st.session_state.activity:

        st.dataframe(
            pd.DataFrame(st.session_state.activity),
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info("No activity records available.")

    st.caption(
        "These are current-session records. Historical performance "
        "and grip success rates are not yet implemented."
    )


# ============================================================
# PAGE 6: SYSTEM SETTINGS
# ============================================================

elif st.session_state.page == "System Settings":

    st.title("System Settings")

    st.write(
        "Review configuration and software components."
    )

    st.subheader("Software Configuration")

    st.json(cfg)

    st.divider()

    st.subheader("System Components")

    components = [
        ("Camera", f'Index {cfg.get("camera_index", 0)}'),
        ("Vision System", "OpenCV candidate detection"),
        ("Object Catalogue", "Enabled"),
        ("Adaptive Controller", "Enabled"),
        ("Gripper Communication", "Serial interface"),
        (
            "Operating Mode",
            "Simulation"
            if cfg.get("simulation_mode", True)
            else "Hardware configured"
        )
    ]

    for name, value in components:

        with st.container(border=True):

            col1, col2 = st.columns([2, 1])

            with col1:
                st.write(f"**{name}**")

            with col2:
                st.write(value)

    st.divider()

    st.subheader("Safety Information")

    st.warning(
        "Keep simulation mode enabled until the controller board, "
        "servo motors, force sensor, power supply, wiring and "
        "emergency stop have been checked."
    )

    st.info(
        "Camera coordinates are image pixels. They must not be "
        "sent directly as physical robot movement commands."
    )

    st.caption(
        "The software cannot independently verify physical force, "
        "object weight or hardware safety."
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

footer_left, footer_right = st.columns(2)

with footer_left:

    st.caption(
        "SLIPLEARN ROBOTICS | AI-BASED AUTONOMOUS GRIPPER"
    )

with footer_right:

    st.caption(
        "Vision-Guided Identification | Adaptive Grip Estimation"
    )
