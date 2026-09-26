"""Color/font constants shared across the UI. Palette derived from the
app logo's green (#3ede8b) and white."""

from app.core.job import STATUS_PENDING, STATUS_CONVERTING, STATUS_DONE, STATUS_ERROR

BG = "#0a1512"
BG_PANEL = "#0f201a"
BG_ROW = "#142a22"
BG_ROW_HOVER = "#19332a"

ACCENT = "#3ede8b"
ACCENT_HOVER = "#31c974"
ACCENT_SOFT = "#123423"

TEXT = "#f4fbf7"
TEXT_MUTED = "#87a99a"

SUCCESS = "#3ede8b"
ERROR = "#e5566b"
WARNING = "#e6b155"

FONT_FAMILY = "Segoe UI"

STATUS_COLORS = {
    STATUS_PENDING: TEXT_MUTED,
    STATUS_CONVERTING: WARNING,
    STATUS_DONE: SUCCESS,
    STATUS_ERROR: ERROR,
}
