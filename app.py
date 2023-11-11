from PyQt5.QtWidgets import (
    QMessageBox,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QHBoxLayout,
    QApplication,
    QFileDialog,
)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont
from mutagen.mp3 import MP3
import sqlite3
import os


class MusicPlayer(QWidget):
    def __init__(self):
        super().__init__()

        self.player = QMediaPlayer()
        self.player.positionChanged.connect(self.update_bar)
        self.player.stateChanged.connect(self.handle_state_changed)

        self.layout = QVBoxLayout()
        self.buttons_layout = QHBoxLayout()
        self.song_table = QTableWidget()
        self.song_slider = QSlider(Qt.Horizontal)
        self.volume_slider = QSlider(Qt.Vertical)
        self.song_label = QLabel("No song loaded")
        self.add_song_button = QPushButton("+")

        self.prev_button = QPushButton("<<<")
        self.pause_button = QPushButton("Play")
        self.next_button = QPushButton(">>>")

        self.setWindowTitle("ExL MediaPlayer")
        self.setFixedSize(300, 350)

        self.init_ui()
        self.update_table()

    def init_ui(self):
        self.setLayout(self.layout)
        self.layout.addWidget(self.song_table)
        self.layout.addWidget(self.song_slider)
        self.layout.addWidget(self.song_label)
        self.layout.addLayout(self.buttons_layout)
        self.layout.addWidget(self.add_song_button)

        button_font = QFont("Arial", 8)
        button_font.setWeight(25)

        self.prev_button.setFont(button_font)
        self.next_button.setFont(button_font)
        self.pause_button.setFont(button_font)
        self.song_label.setFont(button_font)
        self.add_song_button.setFont(button_font)
        self.song_table.setFont(button_font)

        self.buttons_layout.addWidget(self.prev_button)
        self.buttons_layout.addWidget(self.pause_button)
        self.buttons_layout.addWidget(self.next_button)
        self.buttons_layout.addWidget(self.volume_slider)

        self.song_table.setColumnCount(3)
        self.song_table.setHorizontalHeaderLabels(["Song", "Length", "Size"])
        self.song_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.add_song_button.clicked.connect(self.add_song)
        self.prev_button.clicked.connect(self.prev_song)
        self.pause_button.clicked.connect(self.pause_song)
        self.next_button.clicked.connect(self.next_song)
        self.song_slider.sliderMoved.connect(self.set_position)
        self.volume_slider.sliderMoved.connect(self.change_volume)

        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.player.volume())

        try:
            if os.path.isfile("./volume.txt"):
                with open("./volume.txt", "r") as f:
                    volume = int(f.read())
                    self.player.setVolume(volume)
                    self.volume_slider.setValue(volume)
        except Exception:
            pass

    def add_song(self):
        song_path, _ = QFileDialog.getOpenFileName(
            self, "Open file", "", "Audio Files (*.mp3 *.wav)"
        )

        if song_path == "":
            return

        try:
            sqlite_connection = sqlite3.connect("./music.db")
            cur = sqlite_connection.cursor()
            cur.execute(f"""CREATE TABLE IF NOT EXISTS music (path TEXT UNIQUE)""")
            sqlite_connection.commit()
            cur.execute(f'INSERT INTO music (path) VALUES ("{song_path}");')
            sqlite_connection.commit()
            cur.close()
            sqlite_connection.close()
        except Exception as e:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Already exists")
            msg.setWindowTitle("Error")
            msg.exec_()

        self.update_table()

    def update_table(self):
        # Get data from database
        sqlite_connection = sqlite3.connect("./music.db")
        cur = sqlite_connection.cursor()
        cur.execute(f"""CREATE TABLE IF NOT EXISTS music (path TEXT UNIQUE)""")
        sqlite_connection.commit()
        cur.execute("SELECT * FROM music;")
        records = cur.fetchall()

        # Clear all records
        self.song_table.setRowCount(0)

        # Create new records
        if len(records) > 0:
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(records[0][0])))
        else:
            return

        for row in records:
            self.song_table.setRowCount(self.song_table.rowCount() + 1)
            audio = MP3(row[0])
            self.song_table.setItem(
                self.song_table.rowCount() - 1,
                0,
                QTableWidgetItem(os.path.basename(row[0])),
            )  # for simplicity, we put the path as song name
            self.song_table.setItem(
                self.song_table.rowCount() - 1,
                1,
                QTableWidgetItem(f"{round(audio.info.length)} sec"),
            )  # artist unknown
            self.song_table.setItem(
                self.song_table.rowCount() - 1,
                2,
                QTableWidgetItem(f"{os.path.getsize(row[0])} bytes"),
            )  # duration unknown

        self.song_table.selectRow(0)
        self.update_texts()

    def prev_song(self):
        if self.song_table.currentRow() > 0:
            self.song_table.selectRow(self.song_table.currentRow() - 1)
        else:
            self.song_table.selectRow(self.song_table.rowCount() - 1)

        
        sqlite_connection = sqlite3.connect("./music.db")
        cur = sqlite_connection.cursor()
        cur.execute("SELECT * FROM music;")
        records = cur.fetchall()

        self.player.setMedia(
            QMediaContent(
                QUrl.fromLocalFile(
                    records[self.song_table.currentRow()][0]
                )
            )
        )
        self.player.play()
        self.pause_button.setText("Pause")
        self.update_texts()

    def pause_song(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.pause_button.setText("Play")
        else:
            self.player.play()
            self.pause_button.setText("Pause")

    def next_song(self):
        if self.song_table.currentRow() < self.song_table.rowCount() - 1:
            self.song_table.selectRow(self.song_table.currentRow() + 1)
        else:
            self.song_table.selectRow(0)

        sqlite_connection = sqlite3.connect("./music.db")
        cur = sqlite_connection.cursor()
        cur.execute("SELECT * FROM music;")
        records = cur.fetchall()

        self.player.setMedia(
            QMediaContent(
                QUrl.fromLocalFile(
                    records[self.song_table.currentRow()][0]
                )
            )
        )
        self.player.play()
        self.pause_button.setText("Pause")
        self.update_texts()

    def update_texts(self):
        if not self.song_table.item(self.song_table.currentRow(), 0):
            return
        self.song_label.setText(
            os.path.basename(
                self.song_table.item(self.song_table.currentRow(), 0).text()
            )
        )

    def update_bar(self):
        position = self.player.position()
        duration = self.player.duration()
        if duration == 0:
            return
        percentage_played = round((position / duration) * 100)
        self.song_slider.setValue(percentage_played)

    def change_volume(self):
        self.player.setVolume(self.volume_slider.value())

        with open("volume.txt", "w") as f:
            f.write(str(self.volume_slider.value()))

    def set_position(self):
        duration = self.player.duration()
        position = round((self.song_slider.value() / 100) * duration)
        self.player.setPosition(position)

    def handle_state_changed(self, state):
        if state == QMediaPlayer.StoppedState:
            self.next_song()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    player = MusicPlayer()
    player.show()
    sys.exit(app.exec_())
