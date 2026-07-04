import sys
from collections import OrderedDict

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from Backend.Config import (
    ENV_PATH,
    SETUP_REQUIRED_CONFIG_KEYS,
    config_needs_setup,
    get_env,
    is_placeholder_value,
    reload_env,
)


_SETUP_APP = None
LINE_EDIT_STYLE = """
QLineEdit {
    background-color: #ffffff;
    color: #111111;
    padding: 8px;
    border-radius: 6px;
    border: 1px solid #d8d8d8;
    font-size: 14px;
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
}
QLineEdit:focus {
    border: 2px solid #72b7ff;
}
QLineEdit:disabled {
    background-color: #e8e8e8;
    color: #777777;
}
"""

CONFIG_SECTIONS = [
    (
        "Profile",
        [
            {
                "name": "Username",
                "label": "Your name",
                "default": "User",
                "required": True,
                "placeholder": "Example: Fahim",
            },
            {
                "name": "Assistantname",
                "label": "Assistant name",
                "default": "SmartVoice",
                "required": True,
                "placeholder": "Example: Mamur Beta",
            },
            {
                "name": "InputLanguage",
                "label": "Input language",
                "default": "bn-BD",
                "placeholder": "bn-BD or en-US",
            },
            {
                "name": "AssistantVoice",
                "label": "Default English voice",
                "default": "en-CA-LiamNeural",
                "placeholder": "Example: en-CA-LiamNeural",
            },
        ],
    ),
    (
        "API Keys",
        [
            {
                "name": "CohereAPIKey",
                "label": "Cohere API key",
                "default": "",
                "required": True,
                "secret": True,
            },
            {
                "name": "GroqAPIKey",
                "label": "Groq API key",
                "default": "",
                "required": True,
                "secret": True,
            },
            {
                "name": "SerperAPIkey",
                "label": "Serper API key",
                "default": "",
                "required": True,
                "secret": True,
            },
            {
                "name": "HuggingFaceAPIKey",
                "label": "Hugging Face API key",
                "default": "",
                "required": True,
                "secret": True,
            },
        ],
    ),
    (
        "Images",
        [
            {
                "name": "HuggingFaceImageModel",
                "label": "Image model",
                "default": "black-forest-labs/FLUX.1-schnell",
            },
            {
                "name": "HuggingFaceProvider",
                "label": "Image provider",
                "default": "auto",
            },
            {
                "name": "HuggingFaceImageTimeoutSeconds",
                "label": "Image timeout seconds",
                "default": "90",
            },
            {
                "name": "HuggingFaceImagesPerPrompt",
                "label": "Images per prompt",
                "default": "1",
            },
        ],
    ),
    (
        "Speech",
        [
            {
                "name": "SpeechRecognitionTimeoutSeconds",
                "label": "Recognition timeout seconds",
                "default": "20",
            },
            {
                "name": "SpeechRecognitionPollSeconds",
                "label": "Recognition poll seconds",
                "default": "0.2",
            },
            {
                "name": "SpeechRecognitionHeadless",
                "label": "Run Chrome headless",
                "default": "False",
                "type": "bool",
            },
            {
                "name": "SpeechRecognitionAutoGrantMic",
                "label": "Auto grant microphone",
                "default": "True",
                "type": "bool",
            },
            {
                "name": "SpeechRecognitionUseFakeMic",
                "label": "Use fake microphone",
                "default": "False",
                "type": "bool",
            },
        ],
    ),
]


def _all_fields():
    for _section, fields in CONFIG_SECTIONS:
        for field in fields:
            yield field


def _field_map():
    return {field["name"]: field for field in _all_fields()}


def _bool_text(value):
    return "True" if value else "False"


def _parse_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _format_env_value(value):
    value = str(value).strip()
    if value == "":
        return ""

    needs_quotes = any(ch.isspace() for ch in value) or any(
        ch in value for ch in ['"', "#", "\\"]
    )
    if not needs_quotes:
        return value

    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _current_value(field):
    default = field.get("default", "")
    value = get_env(field["name"], default)
    if is_placeholder_value(value):
        return default
    return str(value)


def _get_application():
    global _SETUP_APP

    app = QApplication.instance()
    if app is None:
        _SETUP_APP = QApplication(sys.argv)
        app = _SETUP_APP
    return app


class SetupWizard(QDialog):
    def __init__(self):
        super().__init__()
        self.inputs = {}
        self.setWindowTitle("SmartVoice Setup")
        self.setMinimumSize(720, 560)
        self.setStyleSheet(
            """
            QDialog { background-color: #101010; color: white; }
            QLabel { color: white; font-size: 14px; }
            QTabWidget::pane { border: 1px solid #333333; }
            QTabBar::tab {
                background-color: #202020;
                color: white;
                padding: 8px 14px;
                border: 1px solid #333333;
            }
            QTabBar::tab:selected { background-color: #333333; }
            QCheckBox { color: white; font-size: 14px; padding: 8px; }
            QPushButton {
                background-color: white;
                color: black;
                padding: 9px 14px;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton#cancelButton {
                background-color: #272727;
                color: white;
                border: 1px solid #444444;
            }
            QPushButton#saveButton {
                background-color: #f4f4f4;
                color: black;
                font-weight: bold;
            }
            """
        )
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        title = QLabel("Set up SmartVoice")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        subtitle = QLabel(
            "Enter your own API keys and assistant details. These values are saved locally in .env."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #d8d8d8; font-size: 14px;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        tabs = QTabWidget()
        for section_name, fields in CONFIG_SECTIONS:
            tabs.addTab(self._build_section(fields), section_name)
        layout.addWidget(tabs, 1)

        note = QLabel(
            "Required: username, assistant name, and all API keys. You can change these later by editing .env."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #c9c9c9;")
        layout.addWidget(note)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("cancelButton")
        save_button = QPushButton("Save and Start")
        save_button.setObjectName("saveButton")
        cancel_button.clicked.connect(self.reject)
        save_button.clicked.connect(self.save_and_accept)
        button_row.addWidget(cancel_button)
        button_row.addWidget(save_button)
        layout.addLayout(button_row)

    def _build_section(self, fields):
        section = QWidget()
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("background-color: #101010; border: none;")

        content = QWidget()
        form = QFormLayout(content)
        form.setContentsMargins(14, 16, 14, 16)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        for field in fields:
            widget = self._create_input(field)
            label = field["label"] + (" *" if field.get("required") else "")
            form.addRow(QLabel(label), widget)
            self.inputs[field["name"]] = widget

        scroll.setWidget(content)
        section_layout.addWidget(scroll)
        return section

    def _create_input(self, field):
        value = _current_value(field)

        if field.get("type") == "bool":
            checkbox = QCheckBox()
            checkbox.setChecked(_parse_bool(value))
            return checkbox

        line_edit = QLineEdit()
        line_edit.setText(value)
        line_edit.setPlaceholderText(field.get("placeholder", ""))
        line_edit.setStyleSheet(LINE_EDIT_STYLE)
        if field.get("secret"):
            line_edit.setEchoMode(QLineEdit.Password)
        return line_edit

    def _input_value(self, name):
        widget = self.inputs[name]
        if isinstance(widget, QCheckBox):
            return _bool_text(widget.isChecked())
        return widget.text().strip()

    def collect_values(self):
        values = OrderedDict()
        for field in _all_fields():
            values[field["name"]] = self._input_value(field["name"])
        return values

    def save_and_accept(self):
        values = self.collect_values()
        missing = []
        fields_by_name = _field_map()

        for key in SETUP_REQUIRED_CONFIG_KEYS:
            if is_placeholder_value(values.get(key)):
                missing.append(fields_by_name.get(key, {}).get("label", key))

        if missing:
            QMessageBox.warning(
                self,
                "Setup incomplete",
                "Please fill these required fields:\n\n" + "\n".join(missing),
            )
            return

        save_config(values)
        self.accept()


def save_config(values):
    lines = [
        "# SmartVoice user configuration.",
        "# Generated by the SmartVoice setup wizard. Do not share API keys.",
        "",
        "# AI service keys",
    ]

    for key in ("CohereAPIKey", "GroqAPIKey", "SerperAPIkey", "HuggingFaceAPIKey"):
        lines.append(f"{key}={_format_env_value(values.get(key, ''))}")

    lines.extend(["", "# Image generation"])
    for key in (
        "HuggingFaceImageModel",
        "HuggingFaceProvider",
        "HuggingFaceImageTimeoutSeconds",
        "HuggingFaceImagesPerPrompt",
    ):
        lines.append(f"{key}={_format_env_value(values.get(key, ''))}")

    lines.extend(["", "# User profile"])
    for key in ("Username", "Assistantname", "InputLanguage", "AssistantVoice"):
        lines.append(f"{key}={_format_env_value(values.get(key, ''))}")

    lines.extend(["", "# Speech recognition options"])
    for key in (
        "SpeechRecognitionTimeoutSeconds",
        "SpeechRecognitionPollSeconds",
        "SpeechRecognitionHeadless",
        "SpeechRecognitionAutoGrantMic",
        "SpeechRecognitionUseFakeMic",
    ):
        lines.append(f"{key}={_format_env_value(values.get(key, ''))}")

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    reload_env()


def ensure_user_config() -> bool:
    reload_env()
    if not config_needs_setup():
        return True

    _get_application()
    dialog = SetupWizard()
    result = dialog.exec_()
    return result == QDialog.Accepted and not config_needs_setup()
