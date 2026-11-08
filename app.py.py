
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
    page_title="SlipLearn | Robotics Control Centre",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# LANDSCAPE INDUSTRIAL DESIGN
# ============================================================

st.markdown("""
<style>

:root {
    --yellow: #F5C400;
    --dark: #20252B;
    --background: #EDF0F4;
    --white: #FFFFFF;
    --muted: #77818C;
    --border: #DCE2E8;
}

.stApp {
    background: var(--background);
    color: var(--dark);
}

header[data-testid="stHeader"] {
    background: transparent;
}

[data-testid="stSidebar"] {
    display: none;
}

.block-container {
    max-width: 1900px;
    padding-top: 0.7rem;
    padding-bottom: 0.5rem;
    padding-left: 1.2rem;
    padding-right: 1.2rem;
}

h1, h2, h3, h4 {
    color: #20252B !important;
    font-weight: 750 !important;
}

p, label, span {
    color: #56616D;
}

h1 {
    font-size: 2rem !important;
}

h2 {
    font-size: 1.2rem !important;
}

h3 {
    font-size: 1rem !important;
}

[data-testid="stMetric"] {
    background: white;
    border: 1px solid var(--border);
    border-radius: 9px;
    padding: 10px 13px;
    min-height: 85px;
}

[data-testid="stMetricLabel"] {
    color: #687480 !important;
    font-size: 0.8rem;
}

[data-testid="stMetricValue"] {
    color: #20252B !important;
    font-weight: 800;
    font-size: 1.6rem;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    background: white;
    border: 1px solid var(--border);
    border-radius: 9px;
}

.stButton > button {
    background: #F5C400;
    color: #20252B;
    border: 1px solid #D9B000;
    border-radius: 6px;
    font-weight: 700;
    min-height: 36px;
}

.stButton > button:hover {
    background: #FFD633;
    color: #20252B;
}

.stProgress > div > div > div > div {
    background-color: #F5C400;
}

hr {
    margin-top: 0.35rem;
    margin-bottom: 0.5rem;
    border-color: #DCE2E8;
}

[data-testid="stDataFrame"] {
    background: white;
}

[data-testid="stCaptionContainer"] p {
    color: #7A8590;
    font-size: 0.75rem;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# CONFIGURATION
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

if "camera_running" not in st.session_state:
    st.session_state.camera_running = False

if "detections" not in st.session_state:
    st.session_state.detections = []

if "activity" not in st.session_state:
    st.session_state.activity = []

if "grip_target" not in st.session_state:
    st.session_state.grip_target = 20

if "last_message" not in st.session_state:
    st.session_state.last_message = "System initialized"

if "last_frame" not in st.session_state:
    st.session_state.last_frame = None

if "adaptive_target" not in st.session_state:
    st.session_state.adaptive_target = 20


# ============================================================
# OBJECT CATALOGUE
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

    st.session_state.activity = st.session_state.activity[:30]


# ============================================================
# OBJECT APPROVAL
# ============================================================

def verify_object(name, weight):

    try:

        result = check_object(name, weight)

        if isinstance(result, tuple):

            approved = bool(result[0])
            message = str(result[1])

        else:

            approved = bool(result)

            message = (
                "Object approved."
                if approved
                else "Object rejected under current rules."
            )

        return approved, message

    except Exception as error:

        return False, f"Approval error: {error}"


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

        return False, "Camera could not be opened."

    except Exception as error:

        st.session_state.camera_running = False

        return False, str(error)


def stop_camera():

    try:
        st.session_state.vision.stop()
    except Exception:
        pass

    st.session_state.camera_running = False
    st.session_state.last_frame = None

    log_activity("Camera stopped")


def update_camera():

    if not st.session_state.camera_running:
        return None, []

    try:

        frame, detections = st.session_state.vision.read()

        if detections is None:
            detections = []

        st.session_state.detections = detections

        if frame is not None:
            st.session_state.last_frame = frame

        return frame, detections

    except Exception as error:

        st.session_state.last_message = str(error)

        return None, []


def detection_table(detections):

    rows = []

    for number, item in enumerate(detections, start=1):

        bbox = item.get("bbox", [0, 0, 0, 0])
        center = item.get("center_px", [0, 0])

        rows.append({
            "ID": number,
            "Object": item.get("label", "Unknown"),
            "Confidence": item.get("confidence", "N/A"),
            "Centre X": center[0],
            "Centre Y": center[1]
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
# HEADER
# ============================================================

header1, header2, header3 = st.columns([3, 1, 1])

with header1:
    st.markdown("# 🤖 SLIPLEARN")
    st.caption(
        "AI-BASED AUTONOMOUS ROBOTIC GRIPPER | "
        "VISION-GUIDED INTELLIGENT CONTROL"
    )

with header2:

    st.markdown("### SYSTEM STATUS")

    st.success("SOFTWARE ONLINE")

with header3:

    st.markdown("### OPERATING MODE")

    if cfg.get("simulation_mode", True):
        st.warning("SIMULATION MODE")
    else:
        st.error("HARDWARE CONFIGURED")

st.divider()


# ============================================================
# UPDATE CAMERA WHEN RUNNING
# ============================================================

if st.session_state.camera_running:
    current_frame, current_detections = update_camera()


# ============================================================
# TOP METRICS
# ============================================================

m1, m2, m3, m4, m5 = st.columns(5)

m1.metric(
    "AI VISION",
    "RUNNING" if st.session_state.camera_running else "READY"
)

m2.metric(
    "APPROVED OBJECTS",
    len(OBJECT_NAMES)
)

m3.metric(
    "DETECTED OBJECTS",
    len(st.session_state.detections)
)

m4.metric(
    "GRIP COMMAND",
    f'{st.session_state.grip_target}%'
)

m5.metric(
    "OPERATING MODE",
    "SIMULATION"
    if cfg.get("simulation_mode", True)
    else "HARDWARE"
)

st.divider()


# ============================================================
# MAIN LANDSCAPE AREA
# ============================================================

vision_col, control_col, object_col = st.columns(
    [1.65, 1.15, 1.1],
    gap="medium"
)


# ============================================================
# PANEL 1: LIVE AI VISION
# ============================================================

with vision_col:

    with st.container(border=True):

        st.subheader("📷 LIVE AI VISION")

        cam1, cam2 = st.columns(2)

        with cam1:

            if st.button(
                "▶ START CAMERA",
                use_container_width=True
            ):

                success, message = start_camera()

                if success:
                    st.success(message)
                else:
                    st.error(message)

        with cam2:

            if st.button(
                "■ STOP CAMERA",
                use_container_width=True
            ):

                stop_camera()
                st.info("Camera stopped.")

        if st.session_state.camera_running:

            st.success("CAMERA RUNNING")

            if st.session_state.last_frame is not None:

                rgb = cv2.cvtColor(
                    st.session_state.last_frame,
                    cv2.COLOR_BGR2RGB
                )

                st.image(
                    rgb,
                    channels="RGB",
                    use_container_width=True
                )

            else:

                st.info("Waiting for camera frame.")

        else:

            st.info("Camera is stopped.")

            st.image(
                "https://placehold.co/800x450/20252B/F5C400?text=SLIPLEARN+CAMERA+FEED",
                use_container_width=True
            )

        st.markdown("**DETECTION RESULTS**")

        if st.session_state.detections:

            st.dataframe(
                pd.DataFrame(
                    detection_table(st.session_state.detections)
                ),
                use_container_width=True,
                hide_index=True,
                height=135
            )

        else:

            st.caption("No objects detected.")

        st.caption(
            "Vision module: OpenCV candidate detector. "
            "Trained semantic object recognition is not yet implemented."
        )


# ============================================================
# PANEL 2: GRIPPER CONTROL
# ============================================================

with control_col:

    with st.container(border=True):

        st.subheader("🦾 GRIPPER CONTROL")

        st.metric(
            "CURRENT GRIP COMMAND",
            f'{st.session_state.grip_target}%'
        )

        st.progress(
            min(max(st.session_state.grip_target / 100, 0), 1)
        )

        grip_target = st.slider(
            "Grip command (%)",
            0,
            100,
            int(st.session_state.grip_target),
            key="main_grip_slider"
        )

        st.session_state.grip_target = grip_target

        st.markdown("**OBJECT VERIFICATION**")

        if OBJECT_NAMES:

            selected_object = st.selectbox(
                "Select object",
                OBJECT_NAMES,
                key="main_selected_object"
            )

            measured_weight = st.number_input(
                "Measured weight (grams)",
                min_value=0.0,
                max_value=500.0,
                value=10.0,
                step=1.0,
                key="main_measured_weight"
            )

            approved = False

            if measured_weight > 0:

                approved, approval_message = verify_object(
                    selected_object,
                    measured_weight
                )

                if approved:
                    st.success("OBJECT APPROVED")
                else:
                    st.error("OBJECT REJECTED")

            else:

                st.warning("Enter a positive weight.")

        else:

            selected_object = None
            approved = False

            st.error("No approved objects available.")

        grip1, grip2 = st.columns(2)

        with grip1:

            if st.button(
                "APPLY GRIP",
                use_container_width=True,
                disabled=not approved
            ):

                if not cfg.get("simulation_mode", True):

                    st.error(
                        "Physical hardware actuation is disabled "
                        "in this software version."
                    )

                else:

                    try:

                        connected, message = (
                            st.session_state.link.connect()
                        )

                        if connected:

                            st.session_state.link.send_grip(
                                grip_target
                            )

                            st.session_state.last_message = (
                                f"Simulation grip command: {grip_target}%"
                            )

                            log_activity(
                                f"Grip command {grip_target}% "
                                f"for {selected_object}"
                            )

                            st.success("Grip command sent.")

                        else:

                            st.error(message)

                    except Exception as error:

                        st.error(str(error))

        with grip2:

            if st.button(
                "RELEASE",
                use_container_width=True
            ):

                if not cfg.get("simulation_mode", True):

                    st.error(
                        "Physical hardware release is disabled."
                    )

                else:

                    try:

                        st.session_state.link.release()

                        st.session_state.grip_target = 0
                        st.session_state.last_message = "Release command sent"

                        log_activity("Simulation release command")

                        st.success("Release command sent.")

                    except Exception as error:

                        st.error(str(error))

        st.divider()

        st.markdown("**ADAPTIVE GRIP TEST**")

        test_force = st.number_input(
            "Simulated force value",
            min_value=0.0,
            max_value=1000.0,
            value=100.0,
            step=5.0,
            key="main_test_force"
        )

        if st.button(
            "RUN ADAPTIVE TEST",
            use_container_width=True
        ):

            new_target, message = (
                st.session_state.controller.update(test_force)
            )

            st.session_state.adaptive_target = new_target
            st.session_state.grip_target = new_target
            st.session_state.last_message = message

            log_activity(message)

            st.info(message)

        st.caption(
            "Test force is simulated, not a physical sensor reading."
        )


# ============================================================
# PANEL 3: OBJECT LIBRARY
# ============================================================

with object_col:

    with st.container(border=True):

        st.subheader("📦 OBJECT LIBRARY")

        st.metric(
            "TOTAL CATALOGUE ENTRIES",
            len(OBJECT_NAMES)
        )

        object_rows = []

        for number, name in enumerate(OBJECT_NAMES, start=1):

            details = get_object_details(name)

            object_rows.append({
                "No.": number,
                "Object": details.get(
                    "display_name",
                    details.get("name", name)
                ),
                "Max Weight (g)": details.get(
                    "max_weight_g",
                    "N/A"
                )
            })

        if object_rows:

            st.dataframe(
                pd.DataFrame(object_rows),
                use_container_width=True,
                hide_index=True,
                height=235
            )

        else:

            st.warning("Object catalogue is empty.")

        st.divider()

        st.markdown("**OBJECT APPROVAL CHECK**")

        if OBJECT_NAMES:

            library_object = st.selectbox(
                "Test object",
                OBJECT_NAMES,
                key="library_test_object"
            )

            library_weight = st.number_input(
                "Test weight (grams)",
                min_value=0.0,
                max_value=500.0,
                value=10.0,
                step=1.0,
                key="library_test_weight"
            )

            if st.button(
                "CHECK APPROVAL",
                use_container_width=True
            ):

                if library_weight <= 0:

                    st.warning("Enter a positive weight.")

                else:

                    result, message = verify_object(
                        library_object,
                        library_weight
                    )

                    if result:
                        st.success(message)
                    else:
                        st.error(message)


# ============================================================
# BOTTOM LANDSCAPE PANELS
# ============================================================

st.divider()

analytics_col, system_col, activity_col = st.columns(
    [1.1, 1.0, 1.4],
    gap="medium"
)


# ============================================================
# ANALYTICS
# ============================================================

with analytics_col:

    with st.container(border=True):

        st.subheader("📊 ANALYTICS")

        a1, a2 = st.columns(2)

        a1.metric(
            "Detections",
            len(st.session_state.detections)
        )

        a2.metric(
            "Activities",
            len(st.session_state.activity)
        )

        st.markdown("**CURRENT GRIP LEVEL**")

        st.progress(
            min(max(st.session_state.grip_target / 100, 0), 1)
        )

        st.caption(
            f"Grip command: {st.session_state.grip_target}%"
        )

        if st.session_state.detections:

            labels = [
                item.get("label", "Unknown")
                for item in st.session_state.detections
            ]

            counts = pd.Series(labels).value_counts()

            st.bar_chart(counts)

        else:

            st.caption("Detection graph will appear after detection.")

        st.caption(
            "Analytics represent the current software session."
        )


# ============================================================
# SYSTEM STATUS
# ============================================================

with system_col:

    with st.container(border=True):

        st.subheader("⚙️ SYSTEM STATUS")

        st.success("SOFTWARE ONLINE")

        st.write(
            "📷 Camera: "
            + (
                "RUNNING"
                if st.session_state.camera_running
                else "STOPPED"
            )
        )

        st.write("🧠 Vision: INITIALIZED")

        st.write(
            "🦾 Gripper: "
            + (
                "SIMULATION"
                if cfg.get("simulation_mode", True)
                else "HARDWARE CONFIGURED"
            )
        )

        st.write("📦 Object catalogue: LOADED")

        st.write("⚙️ Adaptive controller: READY")

        status = get_gripper_status()

        if status:

            force_value = status.get("force")

            st.metric(
                "Gripper Force",
                force_value if force_value is not None else "N/A"
            )

            st.caption(
                "Gripper status: "
                + str(status.get("status", "Unknown"))
            )

        else:

            st.caption("Gripper status not available.")

        st.caption(
            "Simulated values must not be treated as real sensor readings."
        )


# ============================================================
# ACTIVITY LOG
# ============================================================

with activity_col:

    with st.container(border=True):

        st.subheader("📋 RECENT SYSTEM ACTIVITY")

        if st.session_state.activity:

            st.dataframe(
                pd.DataFrame(st.session_state.activity),
                use_container_width=True,
                hide_index=True,
                height=240
            )

        else:

            st.info("No activity recorded yet.")

        if st.button(
            "CLEAR ACTIVITY LOG",
            use_container_width=True
        ):

            st.session_state.activity = []

            st.rerun()



# ============================================================
# FORCE, SLIP AND LEARNING MONITORING
# ============================================================

st.divider()
st.subheader("📈 GRIP FORCE & ADAPTIVE MONITORING")

status_data = get_gripper_status() or {}
real_force = status_data.get("force")
is_simulation = bool(cfg.get("simulation_mode", True))
hardware_connected = (
    not is_simulation
    and status_data.get("status") not in (None, "DISCONNECTED")
    and real_force is not None
)

force_col, slip_col, servo_col, confidence_col = st.columns(4)

with force_col:
    st.metric(
        "GRIP FORCE",
        f"{real_force}" if real_force is not None else "—",
        help="Value reported by the gripper communication module."
    )
    st.caption(
        "SIMULATION DATA" if is_simulation
        else ("CONNECTED SENSOR DATA" if hardware_connected else "NOT CONNECTED")
    )

with slip_col:
    slip_value = status_data.get("slip")
    st.metric(
        "SLIP STATUS",
        "SLIP DETECTED" if slip_value is True
        else ("STABLE" if slip_value is False else "—")
    )
    st.caption(
        "Simulation status" if is_simulation
        else ("Sensor/controller status" if hardware_connected else "NOT CONNECTED")
    )

with servo_col:
    servo_value = status_data.get("servo")
    st.metric(
        "SERVO COMMAND",
        f"{servo_value}%" if servo_value is not None else "—"
    )
    st.caption("Command feedback; not a measured shaft-angle reading.")

with confidence_col:
    if st.session_state.detections:
        best_confidence = max(
            float(item.get("confidence", 0))
            for item in st.session_state.detections
        )
        st.metric("TOP DETECTION CONFIDENCE", f"{best_confidence:.1f}%")
    else:
        st.metric("TOP DETECTION CONFIDENCE", "—")
    st.caption("YOLO detection confidence, when an object is detected.")

meter1, meter2 = st.columns(2)

with meter1:
    st.markdown("**GRIP COMMAND LEVEL**")
    st.progress(min(max(float(st.session_state.grip_target) / 100, 0), 1))
    st.caption(f"Software grip command: {st.session_state.grip_target}%")

with meter2:
    st.markdown("**FORCE LIMIT UTILIZATION**")
    threshold = float(cfg.get("force_threshold", 350))
    if real_force is not None and threshold > 0:
        utilization = min(max(float(real_force) / threshold, 0), 1)
        st.progress(utilization)
        st.caption(f"{float(real_force):.0f} / {threshold:.0f} configured force units")
    else:
        st.progress(0.0)
        st.caption("NOT CONNECTED — no force reading available")

st.markdown("**SLIP / FORCE HISTORY**")
history_values = list(getattr(st.session_state.controller, "history", []))
if history_values:
    history_df = pd.DataFrame({
        "Sample": list(range(1, len(history_values) + 1)),
        "Force": history_values
    }).set_index("Sample")
    st.line_chart(history_df, height=170)
    st.caption("Controller history from the adaptive grip test or sensor updates.")
else:
    st.info("No force history yet. Run the adaptive test to create a clearly labelled simulated test trace.")

st.caption(
    "DATA INTEGRITY: Finger-specific force, vibration, physical servo angle, "
    "and learned success rate are not available from the current hardware interface. "
    "They are intentionally shown as unavailable rather than fabricated."
)


# ============================================================
# WORKFLOW
# ============================================================

st.divider()

st.markdown("### SLIPLEARN WORKFLOW")

w1, w2, w3, w4, w5 = st.columns(5)

workflow = [
    ("01", "CAMERA INPUT"),
    ("02", "OBJECT DETECTION"),
    ("03", "OBJECT APPROVAL"),
    ("04", "GRIP FORCE ESTIMATION"),
    ("05", "ADAPTIVE GRIP CONTROL")
]

for col, (number, title) in zip(
    [w1, w2, w3, w4, w5],
    workflow
):

    with col:

        with st.container(border=True):

            st.markdown(f"### :orange[{number}]")

            st.caption(title)


# ============================================================
# SAFETY AND FOOTER
# ============================================================

st.divider()

st.warning(
    "SAFETY: Keep simulation mode enabled until the servo motors, "
    "force sensor, wiring, power supply, controller and emergency "
    "stop have been independently verified. Physical actuation "
    "is disabled in this software version."
)

st.caption(
    "SLIPLEARN ROBOTICS | Vision-Guided Identification | "
    "Adaptive Gripping | Self-Learning Grip Control"
)
