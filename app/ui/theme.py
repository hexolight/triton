"""Design tokens. Emerald ink surfaces, champagne as the single action colour.

Champagne is reserved for the one thing the user should do next (the primary
button, the save action, progress). Emerald only ever means "ready"; terracotta
only ever means "failed". Everything else is ink and ivory.
"""

from app.core.job import STATUS_PENDING, STATUS_CONVERTING, STATUS_DONE, STATUS_ERROR

# surfaces, darkest to lightest
INK = "#08130F"            # window
INK_RAISED = "#0E1E17"     # list rows
INK_HOVER = "#142A21"      # secondary controls, hover
INK_LINE = "#1F3A2E"       # hairlines, scrollbar, progress track

# champagne
CHAMPAGNE = "#E9D8A6"
CHAMPAGNE_HOVER = "#F4E7BE"
CHAMPAGNE_DIM = "#A99A6E"

# emerald
EMERALD = "#1F8F6B"        # logo field
EMERALD_SOFT = "#123A2C"   # tinted disc behind the empty-state icon
EMERALD_TEXT = "#56C29A"   # "ready" text and dots, readable on ink

# text
TEXT = "#F2EBDA"
TEXT_MUTED = "#93A99B"

# state
ERROR = "#E27D68"
WARNING = "#D9A441"

FONT_FAMILY = "Segoe UI"
FONT_STRONG = "Segoe UI Semibold"
FONT_BRAND = "Georgia"

STATUS_COLORS = {
    STATUS_PENDING: TEXT_MUTED,
    STATUS_CONVERTING: CHAMPAGNE_DIM,
    STATUS_DONE: CHAMPAGNE,
    STATUS_ERROR: ERROR,
}
