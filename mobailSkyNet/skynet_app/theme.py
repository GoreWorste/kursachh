from kivy.metrics import dp


def rgba(hex_color, alpha=1):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        raise ValueError("Expected a 6-character hex color.")
    return [
        int(hex_color[0:2], 16) / 255,
        int(hex_color[2:4], 16) / 255,
        int(hex_color[4:6], 16) / 255,
        alpha,
    ]


PRIMARY = rgba("#1976D2")
PRIMARY_DARK = rgba("#1565C0")
PRIMARY_LIGHT = rgba("#E3F2FD")
BACKGROUND = rgba("#F5F5F5")
SURFACE = rgba("#FFFFFF")
SURFACE_ALT = rgba("#FAFAFA")
SURFACE_SOFT = rgba("#F3F8FF")
TEXT = rgba("#111111")
TEXT_MUTED = rgba("#4F4F4F")
INPUT_TEXT = rgba("#000000")
INPUT_HINT = rgba("#5F5F5F")
OUTLINE = rgba("#E0E0E0")
SUCCESS = rgba("#4CAF50")
SUCCESS_BG = rgba("#e8f5e9")
ERROR = rgba("#F44336")
ERROR_BG = rgba("#ffebee")
INFO = rgba("#1565c0")
INFO_BG = rgba("#e3f2fd")
WARNING = rgba("#FF9800")
WARNING_BG = rgba("#fff3e0")
DANGER = rgba("#D32F2F")
DANGER_DARK = rgba("#b71c1c")
DANGER_BG = rgba("#ffebee")
OVERLAY = [0, 0, 0, 0.35]

APP_PADDING = dp(18)
APP_PADDING_SM = dp(12)
APP_GAP = dp(14)
APP_GAP_LG = dp(22)
APP_RADIUS = dp(16)
INPUT_RADIUS = dp(24)
BUTTON_RADIUS = dp(24)
CARD_RADIUS = [APP_RADIUS, APP_RADIUS, APP_RADIUS, APP_RADIUS]
BUTTON_HEIGHT = dp(48)
INPUT_HEIGHT = dp(48)
HEADER_HEIGHT = dp(72)
DRAWER_WIDTH = dp(308)
AVATAR_SIZE = dp(52)


ROLE_LABELS = {
    "guest": "Гость",
    "client": "Клиент",
    "operator": "Оператор",
    "admin": "Администратор",
}


STATUS_COLORS = {
    "draft": (rgba("#424242"), rgba("#eeeeee")),
    "new": (rgba("#ffffff"), rgba("#1976d2")),
    "in_progress": (rgba("#ffffff"), rgba("#f57c00")),
    "resolved": (rgba("#ffffff"), rgba("#2e7d32")),
    "closed": (rgba("#ffffff"), rgba("#757575")),
}


STATUS_LABELS = {
    "new": "Новая",
    "in_progress": "В работе",
    "resolved": "Решена",
    "closed": "Закрыта",
}


PRIORITY_LABELS = {
    "low": "Низкий",
    "medium": "Средний",
    "high": "Высокий",
}
