import sys
import os
import csv
import sqlite3
from datetime import datetime

from PyQt5.uic import loadUi
from PyQt5.QtCore import Qt, QTimer, QTime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QListWidgetItem, QMessageBox,
    QFileDialog, QInputDialog
)

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    PDF_AVAILABLE = True
except Exception:
    PDF_AVAILABLE = False


DB_NAME = "planner.db"


class Window(QWidget):
    def __init__(self):
        super(Window, self).__init__()
        loadUi("todo.ui", self)

        self.dark_mode = False
        self.current_seconds = 25 * 60
        self.pomodoro_running = False
        self.editing_task_id = None

        self.init_db()
        self.bind_events()
        self.start_clock()
        self.update_pomodoro_label()
        self.calendarDateChanged()
        self.apply_light_theme()

    def init_db(self):
        db = sqlite3.connect(DB_NAME)
        cursor = db.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                category TEXT DEFAULT 'General',
                completed TEXT NOT NULL DEFAULT 'NO',
                date TEXT NOT NULL,
                time TEXT DEFAULT ''
            )
        """)

        db.commit()
        db.close()

    def db_execute(self, query, params=()):
        db = sqlite3.connect(DB_NAME)
        cursor = db.cursor()
        cursor.execute(query, params)
        db.commit()
        last_id = cursor.lastrowid
        db.close()
        return last_id

    def db_fetchall(self, query, params=()):
        db = sqlite3.connect(DB_NAME)
        cursor = db.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        db.close()
        return rows

    def db_fetchone(self, query, params=()):
        db = sqlite3.connect(DB_NAME)
        cursor = db.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        db.close()
        return row


    def bind_events(self):
        self.calendarWidget.selectionChanged.connect(self.calendarDateChanged)

        self.addButton.clicked.connect(self.add_or_update_task)
        self.editButton.clicked.connect(self.load_selected_task_for_edit)
        self.deleteButton.clicked.connect(self.delete_task)
        self.saveChecksButton.clicked.connect(self.save_checks)

        self.searchLineEdit.textChanged.connect(self.filter_tasks)
        self.statusFilterComboBox.currentTextChanged.connect(self.filter_tasks)

        self.startPomodoroButton.clicked.connect(self.start_pomodoro)
        self.pausePomodoroButton.clicked.connect(self.pause_pomodoro)
        self.resetPomodoroButton.clicked.connect(self.reset_pomodoro)

        self.darkModeButton.clicked.connect(self.toggle_dark_mode)
        self.exportCsvButton.clicked.connect(self.export_csv)
        self.exportPdfButton.clicked.connect(self.export_pdf)

        self.taskLineEdit.returnPressed.connect(self.add_or_update_task)

    def start_clock(self):
        self.clockTimer = QTimer(self)
        self.clockTimer.timeout.connect(self.update_clock)
        self.clockTimer.start(1000)
        self.update_clock()

    def update_clock(self):
        now = datetime.now()
        self.clockLabel.setText(now.strftime("%H:%M:%S"))
        self.dateNowLabel.setText(now.strftime("%d-%m-%Y"))

    def selected_date_value(self):
        return self.calendarWidget.selectedDate().toString("yyyy-MM-dd")

    def calendarDateChanged(self):
        self.update_task_list(self.selected_date_value())

    def update_task_list(self, date_value):
        self.tasksListWidget.clear()

        rows = self.db_fetchall("""
            SELECT id, task, category, completed, time
            FROM tasks
            WHERE date = ?
            ORDER BY time ASC, id ASC
        """, (date_value,))

        for task_id, task, category, completed, task_time in rows:
            display_text = f"[{category}]"
            if task_time:
                display_text += f" [{task_time}]"
            display_text += f" {task}"

            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, task_id)
            item.setData(Qt.UserRole + 1, task)
            item.setData(Qt.UserRole + 2, category)
            item.setData(Qt.UserRole + 3, task_time)

            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)

            if completed == "Xa":
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)

            self.tasksListWidget.addItem(item)

        self.filter_tasks()
        self.update_stats()

    def add_or_update_task(self):
        task = self.taskLineEdit.text().strip()
        category = self.categoryComboBox.currentText()
        date_value = self.selected_date_value()
        time_value = self.timeEdit.time().toString("HH:mm")

        if not task:
            QMessageBox.warning(self, "Xatolik", "Vazifa bo'sh bo'lmasin.")
            return

        if self.editing_task_id is None:
            self.db_execute("""
                INSERT INTO tasks(task, category, completed, date, time)
                VALUES (?, ?, 'NO', ?, ?)
            """, (task, category, date_value, time_value))
            QMessageBox.information(self, "Qo'shildi", "Vazifa qo'shildi.")
        else:
            self.db_execute("""
                UPDATE tasks
                SET task = ?, category = ?, time = ?
                WHERE id = ?
            """, (task, category, time_value, self.editing_task_id))
            QMessageBox.information(self, "Yangilandi", "Vazifa yangilandi.")
            self.editing_task_id = None
            self.addButton.setText("Vazifa qo'shish")

        self.taskLineEdit.clear()
        self.categoryComboBox.setCurrentText("General")
        self.timeEdit.setTime(QTime.currentTime())
        self.update_task_list(date_value)

    def load_selected_task_for_edit(self):
        item = self.tasksListWidget.currentItem()
        if not item:
            QMessageBox.warning(self, "Xatolik", "Tahrirlash uchun vazifa tanlang.")
            return

        self.editing_task_id = item.data(Qt.UserRole)
        task = item.data(Qt.UserRole + 1)
        category = item.data(Qt.UserRole + 2)
        task_time = item.data(Qt.UserRole + 3)

        self.taskLineEdit.setText(task)
        self.categoryComboBox.setCurrentText(category)

        if task_time:
            self.timeEdit.setTime(QTime.fromString(task_time, "HH:mm"))

        self.addButton.setText("Vazifa yangilandi")

    def delete_task(self):
        item = self.tasksListWidget.currentItem()
        if not item:
            QMessageBox.warning(self, "Xatolik", "O'chirish uchun vazifa tanlang.")
            return

        task_id = item.data(Qt.UserRole)

        reply = QMessageBox.question(
            self,
            "O'chirish",
            "Rostdan ham vazifa o'chirilsinmi?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.db_execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            self.update_task_list(self.selected_date_value())

    def save_checks(self):
        for i in range(self.tasksListWidget.count()):
            item = self.tasksListWidget.item(i)
            task_id = item.data(Qt.UserRole)
            completed = "YES" if item.checkState() == Qt.Checked else "NO"

            self.db_execute("""
                UPDATE tasks
                SET completed = ?
                WHERE id = ?
            """, (completed, task_id))

        self.update_stats()
        QMessageBox.information(self, "Saqlash", "Checkbox holatlari saqlandi.")

    def filter_tasks(self):
        search_text = self.searchLineEdit.text().strip().lower()
        status_filter = self.statusFilterComboBox.currentText()

        visible_total = 0
        visible_done = 0

        for i in range(self.tasksListWidget.count()):
            item = self.tasksListWidget.item(i)
            text = item.text().lower()
            is_done = item.checkState() == Qt.Checked

            visible = True

            if search_text and search_text not in text:
                visible = False

            if status_filter == "Qadalgan" and is_done:
                visible = False
            elif status_filter == "Bajarilgan" and not is_done:
                visible = False

            item.setHidden(not visible)

            if visible:
                visible_total += 1
                if is_done:
                    visible_done += 1

        percent = int((visible_done / visible_total) * 100) if visible_total else 0
        self.progressBar.setValue(percent)
        self.statsLabel.setText(f"Mavjud: {visible_total} | Bajarilgan: {visible_done} | {percent}%")

    def update_stats(self):
        total = self.tasksListWidget.count()

        if total == 0:
            self.progressBar.setValue(0)
            self.statsLabel.setText("Mavjud: 0 | Bajarildi: 0 | 0%")
            return

        done = 0
        for i in range(total):
            item = self.tasksListWidget.item(i)
            if item.checkState() == Qt.Checked:
                done += 1

        percent = int((done / total) * 100)
        self.progressBar.setValue(percent)
        self.statsLabel.setText(f"Vazifalar: {total} | Bajarildi: {done} | {percent}%")

    # =========================
    # POMODORO
    # =========================
    def start_pomodoro(self):
        self.current_seconds = self.workMinutesSpinBox.value() * 60
        self.pomodoro_running = True
        self.pomodoroStatusLabel.setText("Jarayonda")

        if hasattr(self, "pomodoroTimer"):
            self.pomodoroTimer.stop()

        self.pomodoroTimer = QTimer(self)
        self.pomodoroTimer.timeout.connect(self.update_pomodoro)
        self.pomodoroTimer.start(1000)

    def pause_pomodoro(self):
        self.pomodoro_running = False
        if hasattr(self, "pomodoroTimer"):
            self.pomodoroTimer.stop()
        self.pomodoroStatusLabel.setText("To'xtatilgan")

    def reset_pomodoro(self):
        self.pomodoro_running = False
        if hasattr(self, "pomodoroTimer"):
            self.pomodoroTimer.stop()
        self.current_seconds = self.workMinutesSpinBox.value() * 60
        self.pomodoroStatusLabel.setText("Boshidan boshlash")
        self.update_pomodoro_label()

    def update_pomodoro(self):
        if not self.pomodoro_running:
            return

        if self.current_seconds > 0:
            self.current_seconds -= 1
            self.update_pomodoro_label()
        else:
            self.pomodoro_running = False
            self.pomodoroTimer.stop()
            self.pomodoroStatusLabel.setText("Tugadi")
            QMessageBox.information(self, "Pomodoro", "Pomodoro tugadi.")

    def update_pomodoro_label(self):
        minutes = self.current_seconds // 60
        seconds = self.current_seconds % 60
        self.pomodoroTimeLabel.setText(f"{minutes:02d}:{seconds:02d}")

    # =========================
    # DARK MODE
    # =========================
    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            self.apply_dark_theme()
            self.darkModeButton.setText("Yorug' rejim")
        else:
            self.apply_light_theme()
            self.darkModeButton.setText("Tungi rejim")

    def apply_light_theme(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #f6f8fb;
                color: #1f2937;
                font-family: 'Segoe UI';
                font-size: 10.5pt;
            }

            QFrame#headerFrame {
                background-color: #4338ca;
                border-radius: 18px;
                border: none;
            }

            QFrame#headerFrame QLabel {
                background: transparent;
            }

            QLabel#titleLabel {
                color: #ffffff;
                font-size: 22pt;
                font-weight: 700;
            }

            QLabel#subtitleLabel {
                color: #eef2ff;
                font-size: 10.5pt;
                font-weight: 600;
            }

            QLabel#clockLabel {
                color: #ffffff;
                font-size: 20pt;
                font-weight: 700;
            }

            QLabel#dateNowLabel {
                color: #eef2ff;
                font-size: 10pt;
                font-weight: 600;
            }

            QGroupBox {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 16px;
                margin-top: 12px;
                padding-top: 10px;
                font-weight: 600;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
                color: #374151;
            }

            QLineEdit, QComboBox, QTimeEdit, QListWidget, QSpinBox, QCalendarWidget {
                background-color: #ffffff;
                color: #111827;
                border: 1px solid #d1d5db;
                border-radius: 12px;
                padding: 8px;
            }

            QLineEdit:focus, QComboBox:focus, QTimeEdit:focus, QListWidget:focus, QSpinBox:focus {
                border: 2px solid #4f46e5;
            }

            QListWidget {
                padding: 6px;
            }

            QPushButton {
                background-color: #4f46e5;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 9px 14px;
                font-weight: 600;
            }

            QPushButton:hover {
                background-color: #4338ca;
            }

            QPushButton:pressed {
                background-color: #3730a3;
            }

            QPushButton#deleteButton {
                background-color: #ef4444;
            }

            QPushButton#deleteButton:hover {
                background-color: #dc2626;
            }

            QPushButton#saveChecksButton,
            QPushButton#exportCsvButton,
            QPushButton#exportPdfButton {
                background-color: #0f766e;
            }

            QPushButton#saveChecksButton:hover,
            QPushButton#exportCsvButton:hover,
            QPushButton#exportPdfButton:hover {
                background-color: #0d5f59;
            }

            QPushButton#darkModeButton {
                background-color: #111827;
                color: #ffffff;
            }

            QPushButton#darkModeButton:hover {
                background-color: #1f2937;
            }

            QLabel#pomodoroTimeLabel {
                font-size: 30pt;
                font-weight: 700;
                color: #4f46e5;
            }

            QLabel#pomodoroStatusLabel,
            QLabel#statsLabel {
                color: #4b5563;
                font-weight: 600;
            }

            QProgressBar {
                background-color: #e5e7eb;
                border: none;
                border-radius: 10px;
                text-align: center;
                color: #111827;
                font-weight: 600;
                min-height: 20px;
            }

            QProgressBar::chunk {
                background-color: #4f46e5;
                border-radius: 10px;
            }

            QCalendarWidget QWidget {
                alternate-background-color: #f9fafb;
            }

            QCalendarWidget QToolButton {
                color: #1f2937;
                background: transparent;
                font-weight: 600;
                border: none;
                margin: 4px;
            }

            QCalendarWidget QMenu {
                background-color: #ffffff;
                color: #111827;
            }

            QCalendarWidget QSpinBox {
                background: #ffffff;
                color: #111827;
                selection-background-color: #4f46e5;
            }

            QCalendarWidget QAbstractItemView:enabled {
                color: #111827;
                background-color: #ffffff;
                selection-background-color: #4f46e5;
                selection-color: white;
                border-radius: 8px;
            }
        """)

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #0b1220;
                color: #e5e7eb;
                font-family: 'Segoe UI';
                font-size: 10.5pt;
            }

            QFrame#headerFrame {
                background-color: #111827;
                border: 1px solid #1f2937;
                border-radius: 18px;
            }

            QLabel#titleLabel {
                color: #f9fafb;
                font-size: 22pt;
                font-weight: 700;
            }

            QLabel#subtitleLabel {
                color: #9ca3af;
                font-size: 10.5pt;
                font-weight: 500;
            }

            QLabel#clockLabel {
                color: #f9fafb;
                font-size: 20pt;
                font-weight: 700;
            }

            QLabel#dateNowLabel {
                color: #9ca3af;
                font-size: 10pt;
                font-weight: 500;
            }

            QGroupBox {
                background-color: #111827;
                border: 1px solid #253046;
                border-radius: 16px;
                margin-top: 12px;
                padding-top: 10px;
                font-weight: 600;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
                color: #d1d5db;
            }

            QLineEdit, QComboBox, QTimeEdit, QListWidget, QSpinBox, QCalendarWidget {
                background-color: #0f172a;
                color: #e5e7eb;
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 8px;
            }

            QLineEdit:focus, QComboBox:focus, QTimeEdit:focus, QListWidget:focus, QSpinBox:focus {
                border: 2px solid #6366f1;
            }

            QListWidget {
                padding: 6px;
            }

            QPushButton {
                background-color: #6366f1;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 9px 14px;
                font-weight: 600;
            }

            QPushButton:hover {
                background-color: #5558e6;
            }

            QPushButton:pressed {
                background-color: #4547c9;
            }

            QPushButton#deleteButton {
                background-color: #ef4444;
            }

            QPushButton#deleteButton:hover {
                background-color: #dc2626;
            }

            QPushButton#saveChecksButton,
            QPushButton#exportCsvButton,
            QPushButton#exportPdfButton {
                background-color: #0f766e;
            }

            QPushButton#saveChecksButton:hover,
            QPushButton#exportCsvButton:hover,
            QPushButton#exportPdfButton:hover {
                background-color: #115e59;
            }

            QPushButton#darkModeButton {
                background-color: #f3f4f6;
                color: #111827;
            }

            QPushButton#darkModeButton:hover {
                background-color: #e5e7eb;
            }

            QLabel#pomodoroTimeLabel {
                font-size: 30pt;
                font-weight: 700;
                color: #818cf8;
            }

            QLabel#pomodoroStatusLabel,
            QLabel#statsLabel {
                color: #9ca3af;
                font-weight: 600;
            }

            QProgressBar {
                background-color: #1f2937;
                border: none;
                border-radius: 10px;
                text-align: center;
                color: #f9fafb;
                font-weight: 600;
                min-height: 20px;
            }

            QProgressBar::chunk {
                background-color: #6366f1;
                border-radius: 10px;
            }

            QCalendarWidget QWidget {
                alternate-background-color: #111827;
            }

            QCalendarWidget QToolButton {
                color: #e5e7eb;
                background: transparent;
                font-weight: 600;
                border: none;
                margin: 4px;
            }

            QCalendarWidget QMenu {
                background-color: #111827;
                color: #e5e7eb;
            }

            QCalendarWidget QSpinBox {
                background: #0f172a;
                color: #e5e7eb;
                selection-background-color: #6366f1;
            }

            QCalendarWidget QAbstractItemView:enabled {
                color: #e5e7eb;
                background-color: #0f172a;
                selection-background-color: #6366f1;
                selection-color: white;
                border-radius: 8px;
            }
        """)

    def export_csv(self):
        date_value = self.selected_date_value()
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "CSV saqlash",
            f"vazifa_{date_value}.csv",
            "CSV Files (*.csv)"
        )
        if not filename:
            return

        rows = self.db_fetchall("""
            SELECT task, category, completed, date, time
            FROM tasks
            WHERE date = ?
            ORDER BY time ASC, id ASC
        """, (date_value,))

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Vazifalar", "Kategoriya", "Bajarildi", "Sana", "Vaqt"])
            for row in rows:
                writer.writerow(row)

        QMessageBox.information(self, "Export", "CSV muvaffaqiyatli saqlandi.")

    def export_pdf(self):
        if not PDF_AVAILABLE:
            QMessageBox.warning(
                self,
                "PDF",
                "PDF export uchun reportlab kerak:\npip install reportlab"
            )
            return

        date_value = self.selected_date_value()
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "PDF saqlash",
            f"vazifa_{date_value}.pdf",
            "PDF Files (*.pdf)"
        )
        if not filename:
            return

        rows = self.db_fetchall("""
            SELECT task, category, completed, time
            FROM tasks
            WHERE date = ?
            ORDER BY time ASC, id ASC
        """, (date_value,))

        c = canvas.Canvas(filename)
        y = 800

        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, f"Tasks for {date_value}")
        y -= 30

        c.setFont("Helvetica", 11)
        for task, category, completed, task_time in rows:
            line = f"[{completed}] [{category}] [{task_time}] {task}"
            c.drawString(50, y, line[:110])
            y -= 20
            if y < 50:
                c.showPage()
                y = 800
                c.setFont("Helvetica", 11)

        c.save()
        QMessageBox.information(self, "Export", "PDF muvaffaqiyatli saqlandi.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())