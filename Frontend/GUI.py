from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QStackedWidget, QWidget, QLineEdit, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QLabel, QSizePolicy, QScrollArea, QFileDialog
from PyQt5.QtGui import QIcon, QPainter, QMovie, QColor, QTextCharFormat, QFont, QPixmap, QTextBlockFormat
from PyQt5.QtCore import Qt, QSize, QTimer
from Backend.Config import ROOT_DIR, get_env
import sys
import os
import shutil

Assistantname = get_env("Assistantname", "SmartVoice")
old_chat_message = ""
TempDirPath = str(ROOT_DIR / "Frontend" / "Files")
GraphicsDirPath = str(ROOT_DIR / "Frontend" / "Graphics")

DEFAULT_TEMP_FILES = {
    "Mic.data": "False",
    "Status.data": "Available...",
    "Responses.data": "",
    "Database.data": "",
    "TextQuery.data": "",
    "GeneratedImages.data": "",
}

def EnsureTempFiles():
    os.makedirs(TempDirPath, exist_ok=True)
    for filename, default_value in DEFAULT_TEMP_FILES.items():
        path = TempDirectoryPath(filename)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as file:
                file.write(default_value)

def ReadTempFile(filename, default=""):
    EnsureTempFiles()
    path = TempDirectoryPath(filename)
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        with open(path, "w", encoding="utf-8") as file:
            file.write(default)
        return default

def WriteTempFile(filename, value):
    EnsureTempFiles()
    with open(TempDirectoryPath(filename), "w", encoding="utf-8") as file:
        file.write(value)

def AnswerModifier(Answer):
    lines = Answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    modified_answer = '\n'.join(non_empty_lines)
    return modified_answer

def QueryModifier(Query):

    new_query = Query.lower().strip()
    query_words = new_query.split()
    question_words = ["how", "what", "who", "where", "when", "why", "which", "whose", "whom", "can you", "what's", "where's", "how's"]

    if any(word + " " in new_query for word in question_words):
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + '?'
        else:
            new_query = new_query + "?"
        
    else:
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + '.'
        else:
            new_query = new_query + "."

    return new_query.capitalize()

def SetMicrophoneStatus(Command):
    WriteTempFile("Mic.data", Command)

def GetMicrophoneStatus():
    return ReadTempFile("Mic.data", "False")

def SetMicInactive():
    SetMicrophoneStatus("False")

def SetMicActive():
    SetMicrophoneStatus("True")

def SetAssistantStatus(Status):
    WriteTempFile("Status.data", Status)

def GetAssistantStatus():
    return ReadTempFile("Status.data", "Available...")

def MicButtonInitialed():
    SetMicInactive()

def MicButtonClosed():
    SetMicActive()

def GraphicsDirectoryPath(Filename):
    Path = rf'{GraphicsDirPath}\{Filename}'
    return Path

def TempDirectoryPath(Filename):
    Path = rf'{TempDirPath}\{Filename}'
    return Path

def ShowTextToScreen(Text):
    WriteTempFile("Responses.data", Text)

def SetTextQuery(Query):
    WriteTempFile("TextQuery.data", Query.strip())

def GetTextQuery():
    return ReadTempFile("TextQuery.data", "")

def ClearTextQuery():
    WriteTempFile("TextQuery.data", "")

def GetGeneratedImages():
    return ReadTempFile("GeneratedImages.data", "")

def ClearGeneratedImages():
    WriteTempFile("GeneratedImages.data", "")

def ChatLogFilePath():
    data_dir = ROOT_DIR / "Data"
    os.makedirs(data_dir, exist_ok=True)
    for filename in ("ChatLog.json", "Chatlog.json"):
        path = data_dir / filename
        if path.exists():
            return path
    return data_dir / "ChatLog.json"

def ClearPersistentChats():
    global old_chat_message

    with open(ChatLogFilePath(), "w", encoding="utf-8") as file:
        file.write("[]")
    WriteTempFile("Database.data", "")
    WriteTempFile("Responses.data", "")
    ClearGeneratedImages()
    ClearTextQuery()
    old_chat_message = ""

EnsureTempFiles()

class ChatSection(QWidget):

    def __init__(self):
        super(ChatSection, self).__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(-10, 40, 40, 100)
        layout.setSpacing(8)
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameStyle(QFrame.NoFrame)
        self.chat_scroll.setStyleSheet("background-color: black; border: none;")
        self.messages_widget = QWidget()
        self.messages_widget.setStyleSheet("background-color: black;")
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setContentsMargins(20, 10, 20, 10)
        self.messages_layout.setSpacing(12)
        self.messages_layout.setAlignment(Qt.AlignTop)
        self.chat_scroll.setWidget(self.messages_widget)
        layout.addWidget(self.chat_scroll)
        self.setStyleSheet("background-color: black;")
        layout.setSizeConstraint(QVBoxLayout.SetDefaultConstraint)
        layout.setStretch(1, 1)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.gif_label = QLabel()
        self.gif_label.setStyleSheet("border: none;")
        movie = QMovie(GraphicsDirectoryPath('Mamur_Beta.gif'))
        max_gif_size_W = 480
        max_gif_size_H = 270
        movie.setScaledSize(QSize(max_gif_size_W, max_gif_size_H))
        self.gif_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        self.gif_label.setMovie(movie)
        movie.start()
        layout.addWidget(self.gif_label)
        self.label = QLabel("")
        self.label.setStyleSheet("color: white; font-size:16px; margin-right: 195px; border: none; margin-top: -30px;")
        self.label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.label)
        self.chat_icon_label = QLabel()
        chat_pixmap = QPixmap(GraphicsDirectoryPath('Chats.png'))
        new_chat_pixmap = chat_pixmap.scaled(44, 44)
        self.chat_icon_label.setPixmap(new_chat_pixmap)
        self.chat_icon_label.setFixedSize(90, 60)
        self.chat_icon_label.setAlignment(Qt.AlignCenter)
        self.chat_icon_label.mousePressEvent = self.show_text_input
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Type a message...")
        self.text_input.setFixedWidth(520)
        self.text_input.setStyleSheet(
            "background-color: white; color: black; font-size:16px; padding:10px; border-radius:8px;"
        )
        self.text_input.returnPressed.connect(self.submit_text_input)
        self.text_input.hide()
        self.clear_chat_button = QPushButton("Delete Chats")
        self.clear_chat_button.setStyleSheet(
            "background-color:#2b1010; color:white; font-size:14px; "
            "padding:9px 12px; border-radius:8px; border:1px solid #6b2222;"
        )
        self.clear_chat_button.clicked.connect(self.clear_chats)
        input_layout = QHBoxLayout()
        input_layout.addStretch(1)
        input_layout.addWidget(self.chat_icon_label)
        input_layout.addWidget(self.text_input)
        input_layout.addWidget(self.clear_chat_button)
        input_layout.addStretch(1)
        layout.addLayout(input_layout)
        layout.setSpacing(8)
        layout.addWidget(self.gif_label)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.loadMessages)
        self.timer.timeout.connect(self.loadGeneratedImages)
        self.timer.timeout.connect(self.SpeechRecogText)
        self.timer.start(100)
        self.setStyleSheet("""
            QScrollBar:vertical {
                border: none;
                background: black;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
                           
            QScrollBar::handle:vertical {
                background: white;
                min-height: 20px;
            }
                           
            QScrollBar::add-line:vertical {
                background: black;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
                height: 10px;
            }
                           
            QScrollBar::sub-line:vertical {
                background: black;
                subcontrol-position: top;
                subcontrol-origin: margin;
                height: 10px;
            }
                           
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                border: none;
                background: none;
                color: none;
            }
                           
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

    def loadMessages(self):

        global old_chat_message

        messages = ReadTempFile("Responses.data")

        if None==messages:
            pass

        elif len(messages) < 1:
            pass

        elif str(old_chat_message)==str(messages):
            pass

        else:
            self.addMessage(message=messages,color='White')
            old_chat_message = messages

    def loadGeneratedImages(self):
        images = GetGeneratedImages().strip()
        if not images:
            return

        ClearGeneratedImages()
        for image_path in images.splitlines():
            image_path = image_path.strip()
            if image_path:
                self.addImage(image_path)

    def SpeechRecogText(self):
        messages = ReadTempFile("Status.data", "Available...")
        self.label.setText(messages)

    def load_icon(self, path, width=60, height=60):
        pixmap = QPixmap(path)
        new_pixmap = pixmap.scaled(width, height)
        self.icon_label.setPixmap(new_pixmap)

    def toggle_icon(self, event=None):

        if self.toggled:
            self.load_icon(GraphicsDirectoryPath('voice.png'), 60, 60)
            MicButtonInitialed()

        else:
            self.load_icon(GraphicsDirectoryPath('mic.png'), 60, 60)
            MicButtonClosed()

        self.toggled = not self.toggled

    def addMessage(self, message, color):
        if self.isCopyableArtifact(message):
            self.addCopyableArtifact(message)
            return

        label = QLabel(message)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setStyleSheet(
            "color: white; background-color: #101010; font-size:15px; "
            "padding:10px; border-radius:8px;"
        )
        self.appendChatWidget(label)

    def appendChatWidget(self, widget):
        self.messages_layout.addWidget(widget)
        QTimer.singleShot(0, self.scrollToBottom)

    def clearChatWidgets(self):
        while self.messages_layout.count():
            item = self.messages_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def clear_chats(self):
        ClearPersistentChats()
        self.clearChatWidgets()
        self.clear_chat_button.setText("Deleted")
        QTimer.singleShot(1200, lambda: self.clear_chat_button.setText("Delete Chats"))

    def scrollToBottom(self):
        scrollbar = self.chat_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def assistantBody(self, message):
        prefix = f"{Assistantname} :"
        if message.startswith(prefix):
            return message[len(prefix):].strip()
        return message.strip()

    def isCopyableArtifact(self, message):
        if not message.startswith(f"{Assistantname} :"):
            return False

        body = self.assistantBody(message)
        body_lower = body.lower()
        code_markers = [
            "```", "#include", "int main", "using namespace", "public static",
            "def ", "class ", "function ", "import ", "console.log", "return ",
        ]
        doc_markers = [
            "subject:", "dear ", "sincerely", "regards", "application",
            "cover letter", "mail", "email", "letter", "resume", "cv",
            "বিষয়", "বিষয়", "প্রিয়", "শুভেচ্ছা", "ইতি", "ধন্যবাদ",
            "আবেদন", "ইমেইল", "মেইল", "চিঠি",
        ]
        return (
            any(marker in body_lower for marker in code_markers)
            or any(marker in body_lower for marker in doc_markers)
            or body.count("\n") >= 4
        )

    def artifactTitle(self, body):
        body_lower = body.lower()
        if any(marker in body_lower for marker in ["```", "#include", "int main", "def ", "class ", "function "]):
            return "Code"
        return "Document"

    def addCopyableArtifact(self, message):
        body = self.assistantBody(message)
        title = self.artifactTitle(body)

        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background-color: #111111; border: 1px solid #333333; border-radius: 8px; }"
        )
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(10, 10, 10, 10)
        frame_layout.setSpacing(8)

        header_layout = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("color: white; font-size:14px; font-weight: bold; border: none;")
        copy_button = QPushButton("Copy")
        copy_button.setStyleSheet(
            "background-color:white; color:black; padding:6px 12px; border-radius:6px;"
        )
        copy_button.clicked.connect(lambda: self.copyText(body, copy_button))
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)
        header_layout.addWidget(copy_button)

        text_box = QTextEdit()
        text_box.setReadOnly(True)
        text_box.setPlainText(body)
        text_box.setMinimumHeight(180)
        text_box.setStyleSheet(
            "background-color: #050505; color: white; font-size:14px; "
            "padding:8px; border: 1px solid #2b2b2b; border-radius:6px;"
        )

        frame_layout.addLayout(header_layout)
        frame_layout.addWidget(text_box)
        self.appendChatWidget(frame)

    def copyText(self, text, button):
        QApplication.clipboard().setText(text)
        button.setText("Copied")
        QTimer.singleShot(1200, lambda: button.setText("Copy"))

    def addImage(self, image_path):
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.addMessage(f"{Assistantname} : Image saved, but could not load preview: {image_path}", "White")
            return

        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background-color: #111111; border: 1px solid #333333; border-radius: 8px; }"
        )
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(10, 10, 10, 10)
        frame_layout.setSpacing(8)

        max_width = 520
        preview = QLabel()
        preview.setAlignment(Qt.AlignCenter)
        preview.setStyleSheet("border: none; background-color: #050505;")
        preview_width = min(max_width, pixmap.width())
        preview.setPixmap(pixmap.scaledToWidth(preview_width, Qt.SmoothTransformation))

        button_layout = QHBoxLayout()
        copy_button = QPushButton("Copy Image")
        download_button = QPushButton("Download")
        for button in (copy_button, download_button):
            button.setStyleSheet(
                "background-color:white; color:black; padding:6px 12px; border-radius:6px;"
            )
        copy_button.clicked.connect(lambda: self.copyImage(image_path, copy_button))
        download_button.clicked.connect(lambda: self.downloadImage(image_path, download_button))
        button_layout.addStretch(1)
        button_layout.addWidget(copy_button)
        button_layout.addWidget(download_button)

        frame_layout.addWidget(preview)
        frame_layout.addLayout(button_layout)
        self.appendChatWidget(frame)

    def copyImage(self, image_path, button):
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            button.setText("Failed")
            QTimer.singleShot(1200, lambda: button.setText("Copy Image"))
            return

        QApplication.clipboard().setPixmap(pixmap)
        button.setText("Copied")
        QTimer.singleShot(1200, lambda: button.setText("Copy Image"))

    def downloadImage(self, image_path, button):
        default_name = os.path.basename(image_path)
        target_path, _ = QFileDialog.getSaveFileName(
            self,
            "Download image",
            default_name,
            "JPEG Images (*.jpg);;PNG Images (*.png);;All Files (*)"
        )
        if not target_path:
            return

        try:
            if os.path.abspath(image_path) != os.path.abspath(target_path):
                shutil.copyfile(image_path, target_path)
            button.setText("Downloaded")
        except Exception:
            button.setText("Failed")
        QTimer.singleShot(1200, lambda: button.setText("Download"))

    def show_text_input(self, event=None):
        self.chat_icon_label.hide()
        self.text_input.show()
        self.text_input.setFocus()

    def submit_text_input(self):
        query = self.text_input.text().strip()
        if not query:
            self.text_input.hide()
            self.chat_icon_label.show()
            return

        SetTextQuery(query)
        self.text_input.clear()
        self.text_input.hide()
        self.chat_icon_label.show()

class InitialScreen(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        desktop = QApplication.desktop()
        screen_width = desktop.screenGeometry().width()
        screen_height = desktop.screenGeometry().height()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        gif_label = QLabel()
        movie = QMovie(GraphicsDirectoryPath('Mamur_Beta.gif'))
        gif_label.setMovie(movie)
        max_gif_size_H = int(screen_width / 16 * 9)
        movie.setScaledSize(QSize(screen_width, max_gif_size_H))
        gif_label.setAlignment(Qt.AlignCenter)
        movie.start()
        gif_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.icon_label = QLabel()
        pixmap = QPixmap(GraphicsDirectoryPath('Mic_off.png'))
        new_pixmap = pixmap.scaled(60, 60)
        self.icon_label.setPixmap(new_pixmap)
        self.icon_label.setFixedSize(150,150)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.mic_active = False
        SetMicInactive()
        self.icon_label.mousePressEvent = self.toggle_icon
        self.chat_icon_label = QLabel()
        chat_pixmap = QPixmap(GraphicsDirectoryPath('Chats.png'))
        new_chat_pixmap = chat_pixmap.scaled(60, 60)
        self.chat_icon_label.setPixmap(new_chat_pixmap)
        self.chat_icon_label.setFixedSize(150,150)
        self.chat_icon_label.setAlignment(Qt.AlignCenter)
        self.chat_icon_label.mousePressEvent = self.show_text_input
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Type a message...")
        self.text_input.setFixedWidth(420)
        self.text_input.setStyleSheet(
            "background-color: white; color: black; font-size:16px; padding:10px; border-radius:8px;"
        )
        self.text_input.returnPressed.connect(self.submit_text_input)
        self.text_input.hide()
        self.label = QLabel("")
        self.label.setStyleSheet("color: white; font-size:16px ; margin-bottom:0;")
        content_layout.addWidget(gif_label, alignment=Qt.AlignCenter)
        content_layout.addWidget(self.label, alignment=Qt.AlignCenter)
        content_layout.addWidget(self.icon_label, alignment=Qt.AlignCenter)
        content_layout.addWidget(self.chat_icon_label, alignment=Qt.AlignCenter)
        content_layout.addWidget(self.text_input, alignment=Qt.AlignCenter)
        content_layout.setContentsMargins(0, 0, 0, 150)
        self.setLayout(content_layout)
        self.setFixedHeight(screen_height)
        self.setFixedWidth(screen_width)
        self.setStyleSheet("background-color: black;")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.SpeechRecogText)
        self.timer.start(100)

    def SpeechRecogText(self):
        messages = ReadTempFile("Status.data", "Available...")
        self.label.setText(messages)
        mic_active = GetMicrophoneStatus().strip() == "True"
        if mic_active != self.mic_active:
            self.mic_active = mic_active
            icon_name = "Mic_on.png" if mic_active else "Mic_off.png"
            self.load_icon(GraphicsDirectoryPath(icon_name), 60, 60)

    def load_icon(self, path, width=60, height=60):
        pixmap = QPixmap(path)
        new_pixmap = pixmap.scaled(width, height)
        self.icon_label.setPixmap(new_pixmap)

    def toggle_icon(self, event=None):

        self.mic_active = not self.mic_active

        if self.mic_active:
            self.load_icon(GraphicsDirectoryPath('Mic_on.png'), 60, 60)
            SetMicActive()

        else:
            self.load_icon(GraphicsDirectoryPath('Mic_off.png'), 60, 60)
            SetMicInactive()

    def show_text_input(self, event=None):
        self.chat_icon_label.hide()
        self.text_input.show()
        self.text_input.setFocus()

    def submit_text_input(self):
        query = self.text_input.text().strip()
        if not query:
            self.text_input.hide()
            self.chat_icon_label.show()
            return

        SetTextQuery(query)
        self.text_input.clear()
        self.text_input.hide()
        self.chat_icon_label.show()

class MessageScreen(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        desktop = QApplication.desktop()
        screen_width = desktop.screenGeometry().width()
        screen_height = desktop.screenGeometry().height()
        layout = QVBoxLayout()
        label = QLabel("")
        layout.addWidget(label)
        chat_section = ChatSection()
        layout.addWidget(chat_section)
        self.setLayout(layout)
        self.setStyleSheet("background-color: black;")
        self.setFixedHeight(screen_height)
        self.setFixedWidth(screen_width)

class CustomTopBar(QWidget):

    def __init__(self, parent, stacked_widget):
        super().__init__(parent)
        self.initUI()
        self.current_screen = None
        self.stacked_widget = stacked_widget

    def initUI(self):
        self.setFixedHeight(50)
        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignRight)
        home_button = QPushButton()
        home_icon = QIcon(GraphicsDirectoryPath("Home.png"))
        home_button.setIcon(home_icon)
        home_button.setText(" Home")
        home_button.setStyleSheet("height:40px; line-height:40px; background-color:white; color: black")
        message_button = QPushButton()
        message_icon = QIcon(GraphicsDirectoryPath("Chats.png"))
        message_button.setIcon(message_icon)
        message_button.setText(" Chat")
        message_button.setStyleSheet("height:40px; line-height:40px; background-color:white; color: black")
        minimize_button = QPushButton()
        minimize_icon = QIcon(GraphicsDirectoryPath('Minimize2.png'))
        minimize_button.setIcon(minimize_icon)
        minimize_button.setStyleSheet("background-color:white")
        minimize_button.clicked.connect(self.minimizeWindow)
        self.maximize_button = QPushButton()
        self.maximize_icon = QIcon(GraphicsDirectoryPath('Minimize.png'))
        self.restore_icon = QIcon(GraphicsDirectoryPath('Maximize.png'))
        self.maximize_button.setIcon(self.maximize_icon)
        self.maximize_button.setFlat(True)
        self.maximize_button.setStyleSheet("background-color:white")
        self.maximize_button.clicked.connect(self.maximizeWindow)
        close_button = QPushButton()
        close_icon = QIcon(GraphicsDirectoryPath('Close.png'))
        close_button.setIcon(close_icon)
        close_button.setStyleSheet("background-color:white")
        close_button.clicked.connect(self.closeWindow)
        line_frame = QFrame()
        line_frame.setFixedHeight(1)
        line_frame.setFrameShape(QFrame.HLine)
        line_frame.setFrameShadow(QFrame.Sunken)
        line_frame.setStyleSheet("border-color: black;")
        title_label = QLabel(f"{str(Assistantname).title()} AI")
        title_label.setStyleSheet("color: black; font-size: 18px;; background-color:white")
        home_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        message_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        layout.addWidget(title_label)
        layout.addStretch(1)
        layout.addWidget(home_button)
        layout.addWidget(message_button)
        layout.addStretch(1)
        layout.addWidget(minimize_button)
        layout.addWidget(self.maximize_button)
        layout.addWidget(close_button)
        layout.addWidget(line_frame)
        self.draggable = True
        self.offset = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.white)
        super().paintEvent(event)

    def minimizeWindow(self):
        self.parent().showMinimized()

    def maximizeWindow(self):
        if self.parent().isMaximized():
            self.parent().showNormal()
            self.maximize_button.setIcon(self.maximize_icon)
        else:
            self.parent().showMaximized()
            self.maximize_button.setIcon(self.restore_icon)

    def closeWindow(self):
        self.parent().close()

    def mousePressEvent(self, event):
        if self.draggable:
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.draggable and self.offset:
            new_pos = event.globalPos() - self.offset
            self.parent().move(new_pos)

    def showMessageScreen(self):
        if self.current_screen is not None:
            self.current_screen.hide()

        message_screen = MessageScreen(self)
        layout = self.parent().layout()
        if layout is not None:
            layout.addWidget(message_screen)
        self.current_screen = message_screen

    def showInitialScreen(self):
        if self.current_screen is not None:
            self.current_screen.hide()

        initial_screen = InitialScreen(self)
        layout = self.parent().layout()
        if layout is not None:
            layout.addWidget(initial_screen)
        self.current_screen = initial_screen

class MainWindow(QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.initUI()

    def initUI(self):
        desktop = QApplication.desktop()
        screen_width = desktop.screenGeometry().width()
        screen_height = desktop.screenGeometry().height()
        stacked_widget = QStackedWidget(self)
        initial_screen = InitialScreen()
        message_screen = MessageScreen()
        stacked_widget.addWidget(initial_screen)
        stacked_widget.addWidget(message_screen)
        self.setGeometry(0, 0, screen_width, screen_height)
        self.setStyleSheet("background-color: black;")
        top_bar = CustomTopBar(self, stacked_widget)
        self.setMenuWidget(top_bar)
        self.setCentralWidget(stacked_widget)

def GraphicalUserInterface():
    SetMicInactive()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    GraphicalUserInterface()
