from PySide6.QtGui import QColor
from PySide6.QtWidgets import QStyledItemDelegate, QStyle

class EligibilityRowDelegate(QStyledItemDelegate):
    ELIGIBLE_BACKGROUND = QColor(213, 245, 220)
    INELIGIBLE_BACKGROUND = QColor(252, 220, 220)
    ELIGIBLE_TEXT = QColor(20, 80, 35)
    INELIGIBLE_TEXT = QColor(120, 25, 25)

    def paint(self, painter, option, index):
        model = index.model()
        row_data = None
        for attr in ("rows", "_rows"):
            if hasattr(model, attr):
                try:
                    row_data = getattr(model, attr)[index.row()]
                    break
                except Exception:
                    pass
        if isinstance(row_data, dict):
            eligible = bool(row_data.get("eligible"))
            if not (option.state & QStyle.State_Selected):
                option.backgroundBrush = (
                    self.ELIGIBLE_BACKGROUND if eligible
                    else self.INELIGIBLE_BACKGROUND
                )
                option.palette.setColor(
                    option.palette.Text,
                    self.ELIGIBLE_TEXT if eligible else self.INELIGIBLE_TEXT
                )
        super().paint(painter, option, index)

def eligibility_color_name(eligible: bool) -> str:
    return "green" if eligible else "red"
