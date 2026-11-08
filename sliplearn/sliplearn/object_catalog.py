
MAX_OBJECT_WEIGHT_G = 50.0

APPROVED_OBJECTS = {
    "bottle": {
        "display_name": "Empty plastic bottle",
        "max_weight_g": 50.0
    },
    "cup": {
        "display_name": "Plastic cup",
        "max_weight_g": 50.0
    },
    "book": {
        "display_name": "Thin booklet",
        "max_weight_g": 50.0
    },
    "plastic block": {
        "display_name": "Plastic block",
        "max_weight_g": 50.0
    },
    "toy car": {
        "display_name": "Mini toy car",
        "max_weight_g": 50.0
    },
    "eraser": {
        "display_name": "Eraser",
        "max_weight_g": 50.0
    },
    "spoon": {
        "display_name": "Plastic spoon",
        "max_weight_g": 50.0
    },
    "marker": {
        "display_name": "Marker pen",
        "max_weight_g": 50.0
    },
    "sports ball": {
        "display_name": "Plastic ball",
        "max_weight_g": 50.0
    },
    "comb": {
        "display_name": "Plastic comb",
        "max_weight_g": 50.0
    }
}


def check_object(label, measured_weight_g=None):

    label = str(label).strip().lower()

    if label not in APPROVED_OBJECTS:
        return False, "Object is not in the approved list."

    if measured_weight_g is None or measured_weight_g <= 0:
        return False, "Valid weight measurement required."

    if measured_weight_g > MAX_OBJECT_WEIGHT_G:
        return False, "Object exceeds the 50 g weight limit."

    return True, "Object approved for simulated gripping."


def get_approved_objects():
    return APPROVED_OBJECTS
