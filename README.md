# SlipLearn software starter

This is the **pre-hardware software foundation** for the SlipLearn robotic gripper.
It runs in simulation mode before the components arrive on Wednesday.

## Included
- OpenCV camera preview and contour-based object localization
- Optional YOLO adapter point (not enabled until a model is selected)
- Serial communication layer with simulation fallback
- Force/slip monitoring logic
- Conservative adaptive-grip state machine
- Streamlit monitoring dashboard

## Important limitations
- Contour detection finds candidate objects; it does not reliably identify semantic classes such as bottle/cup/box.
- Accurate dimensions require camera calibration and a known reference object.
- Force values and slip thresholds must be calibrated with the actual sensor and gripper.
- Servo commands/pins are intentionally not hard-coded until the purchased board and servo model are confirmed.
- Keep `simulation_mode` true until wiring is checked and the mechanism is tested with no object in the fingers.

## Setup (Windows)
1. Install Python 3.10 or newer.
2. Open Command Prompt in this folder.
3. Run `py -m venv .venv`
4. Run `.venv\\Scripts\\activate`
5. Run `pip install -r requirements.txt`
6. Run `streamlit run app.py`

The dashboard starts in simulation mode. Press **Start camera** to test the webcam.
Change camera index in `config.json` if needed.

## Hardware integration after Wednesday
1. Confirm exact board (UNO / Mega / ESP32), force sensor, servo model and wiring.
2. Set `simulation_mode` to false and configure `serial_port` (for example COM3).
3. Upload `firmware/sliplearn_controller.ino` only after selecting the matching board and pin map.
4. Calibrate sensor readings and force limits with the gripper unloaded first.
5. Test at low force with soft, lightweight objects and an emergency stop available.

## Serial protocol (starter)
Python sends one JSON object per line:
`{"cmd":"GRIP","target":35}`
`{"cmd":"RELEASE"}`

Firmware returns one JSON object per line:
`{"force":120,"slip":false,"servo":35,"status":"HOLD"}`

The `target` is a provisional normalized command (0–100), **not a force measurement**.
