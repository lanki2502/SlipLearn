import json
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None

class GripperLink:
    def __init__(self, port="AUTO", baud=115200, simulation=True):
        self.port, self.baud, self.simulation = port, baud, simulation
        self.connection = None
        self.sim_force = 0
        self.sim_target = 0
        self.last_update = time.time()

    def connect(self):
        if self.simulation:
            return True, "Simulation mode"
        if serial is None:
            return False, "pyserial is not installed"
        port = self.port
        if port == "AUTO":
            ports = list(list_ports.comports())
            if not ports:
                return False, "No serial port found"
            port = ports[0].device
        try:
            self.connection = serial.Serial(port, self.baud, timeout=0.05)
            time.sleep(2)
            return True, f"Connected to {port}"
        except Exception as exc:
            return False, str(exc)

    def send_grip(self, target):
        target = max(0, min(100, int(target)))
        if self.simulation:
            self.sim_target = target
            return True
        return self._send({"cmd": "GRIP", "target": target})

    def release(self):
        if self.simulation:
            self.sim_target = 0
            return True
        return self._send({"cmd": "RELEASE"})

    def _send(self, payload):
        if self.connection is None or not self.connection.is_open:
            return False
        self.connection.write((json.dumps(payload) + "\\n").encode())
        return True

    def read_status(self):
        if self.simulation:
            dt = min(time.time() - self.last_update, 0.2)
            self.last_update = time.time()
            self.sim_force += (self.sim_target * 3 - self.sim_force) * min(1, dt*2)
            return {"force": round(self.sim_force), "slip": False,
                    "servo": self.sim_target, "status": "SIMULATED"}
        if self.connection is None or not self.connection.is_open:
            return {"force": None, "slip": None, "servo": None, "status": "DISCONNECTED"}
        try:
            line = self.connection.readline().decode(errors="ignore").strip()
            return json.loads(line) if line else None
        except Exception:
            return None

    def close(self):
        if self.connection and self.connection.is_open:
            self.connection.close()
