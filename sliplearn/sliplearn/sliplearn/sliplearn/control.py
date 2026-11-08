from collections import deque

class AdaptiveGripController:
    """Starter rule-based controller. Tune thresholds only after sensor calibration."""
    def __init__(self, force_threshold=350, slip_delta=45, min_target=20,
                 max_target=90, step=5):
        self.force_threshold = force_threshold
        self.slip_delta = slip_delta
        self.min_target, self.max_target, self.step = min_target, max_target, step
        self.target = min_target
        self.history = deque(maxlen=6)
        self.last_force = None
        self.events = []

    def update(self, force):
        if force is None:
            return self.target, "Waiting for sensor"
        self.history.append(float(force))
        slip = False
        if self.last_force is not None:
            slip = (self.last_force - force) >= self.slip_delta
        self.last_force = float(force)

        if slip and self.target < self.max_target:
            self.target = min(self.max_target, self.target + self.step)
            message = "Possible slip: increasing grip command"
            self.events.append(message)
        elif force >= self.force_threshold:
            self.target = max(0, self.target - self.step)
            message = "Force limit reached: reducing grip command"
            self.events.append(message)
        else:
            message = "Grip stable"
        return self.target, message
