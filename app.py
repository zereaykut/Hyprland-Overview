import sys
import subprocess as sp
import json
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QPoint, QTimer

class Hyprland:
    @staticmethod
    def monitor(index=0):
        """
        Get available monitor info.

        index: 
            0 => Main monitor
            1 => HDMI
        """
        try:
            result = sp.run(
                ["hyprctl", "monitors", "-j"],
                check=True,
                stdout=sp.PIPE,
                stderr=sp.PIPE,
                text=True
            )
            monitors = json.loads(result.stdout)
            if index < len(monitors):
                mon = monitors[index]
                return mon["width"], mon["height"]
            else:
                print(f"Monitor index {index} out of range.")
                return None
        except sp.CalledProcessError as e:
            print("Error calling hyprctl:", e.stderr)
            return None

    @staticmethod
    def clients():
        """
        Get hyprland clients' info.
        """
        try:
            result = sp.run(
                ["hyprctl", "clients", "-j"],
                check=True,
                stdout=sp.PIPE,
                stderr=sp.PIPE,
                text=True
            )
            return json.loads(result.stdout)
        except sp.CalledProcessError as e:
            print("Error calling hyprctl:", e.stderr)
            return []

    @staticmethod
    def workspaces():
        """
        Get active workspaces' info.
        """
        try:
            result = sp.run(
                ["hyprctl", "workspaces", "-j"],
                check=True,
                stdout=sp.PIPE,
                stderr=sp.PIPE,
                text=True
            )
            return json.loads(result.stdout)
        except sp.CalledProcessError as e:
            print("Error calling hyprctl:", e.stderr)
            return []

    @staticmethod
    def moveToWorkspaceSilent(address, ws):
        """
        Move specified window to specified workspace.

        address: window address info
        ws: workspace number
        """
        try:
            sp.run(
                f"hyprctl dispatch movetoworkspacesilent {ws},address:{address}",
                shell=True,
                check=True,
                stdout=sp.PIPE,
                stderr=sp.PIPE,
                text=True
            )
        except sp.CalledProcessError as e:
            print("Error calling hyprctl:", e.stderr)

    @staticmethod
    def dispatchWorkspace(ws):
        try:
            sp.run(
                f"hyprctl dispatch workspace {ws}",
                shell=True,
                check=True,
                stdout=sp.PIPE,
                stderr=sp.PIPE,
                text=True
            )
        except sp.CalledProcessError as e:
            print("Error calling hyprctl:", e.stderr)

    @staticmethod
    def killwindow(address):
        try:
            sp.run(
                f"hyprctl dispatch killwindow address:{address}",
                shell=True,
                check=True,
                stdout=sp.PIPE,
                stderr=sp.PIPE,
                text=True
            )
        except sp.CalledProcessError as e:
            print("Error calling hyprctl:", e.stderr)

class DraggableLabel(QLabel):
    def __init__(self, text, address, parent=None):
        super().__init__(text, parent)
        self.address = address
        self.setObjectName("windowLabel")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setFixedSize(150, 90)
        self.dragging = False
        self.offset = QPoint()
        self.grid_position = None

        if len(text) > 20:
            wrapped = self.word_wrap(text, 20)
            self.setText(wrapped)
        else:
            self.setText(text)

    def word_wrap(self, text, max_length):
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            if len(current_line + " " + word) <= max_length:
                if current_line:
                    current_line += " "
                current_line += word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return "\n".join(lines)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.offset = event.pos()
            self.raise_()
        elif event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.pos())
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.close_window()


    def mouseMoveEvent(self, event):
        if self.dragging:
            new_pos = self.mapToParent(event.pos() - self.offset)
            self.move(new_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.snap_to_grid()

    def show_context_menu(self, pos):
        menu = QMenu(self)

        close_action = QAction("Close Window", self)
        close_action.triggered.connect(self.close_window)
        menu.addAction(close_action)

        move_menu = QMenu("Move to Workspace", self)
        for (grid_pos, workspace_id) in self.parent().grid_to_workspace.items():
            ws_label = "Special" if workspace_id == -99 else f"Workspace {workspace_id}"
            action = QAction(ws_label, self)
            action.triggered.connect(lambda checked, ws=workspace_id: self.move_to_workspace(ws))
            move_menu.addAction(action)
        menu.addMenu(move_menu)

        menu.exec(self.mapToGlobal(pos))

    def close_window(self):
        try:
            Hyprland.killwindow(self.address)
            parent = self.parent()
            for label in parent.labels:
                label.deleteLater()
            parent.labels.clear()

            # Delay refresh to give Hyprland time to update
            QTimer.singleShot(20, parent.refresh_clients)
        except sp.CalledProcessError as e:
            print("Error closing window:", e.stderr)

    def move_to_workspace(self, ws):
        if ws == -99:
            ws = "special"
        Hyprland.moveToWorkspaceSilent(self.address, ws)
        parent = self.parent()
        for label in parent.labels:
            label.deleteLater()
        parent.labels.clear()
        parent.clients = Hyprland.clients()
        parent.create_labels()

    def snap_to_grid(self):
        nearest_cell = None
        min_distance = float('inf')

        for frame in self.parent().grid_frames:
            frame_center = QPoint(frame.x() + frame.width() // 2, frame.y() + frame.height() // 2)
            label_center = QPoint(self.x() + self.width() // 2, self.y() + self.height() // 2)
            distance = (frame_center - label_center).manhattanLength()

            if distance < min_distance:
                min_distance = distance
                nearest_cell = frame

        if nearest_cell:
            x = nearest_cell.x() + (nearest_cell.width() - self.width()) // 2
            y = nearest_cell.y() + (nearest_cell.height() - self.height()) // 2
            self.move(x, y)
            self.grid_position = (nearest_cell.x(), nearest_cell.y())

            grid_pos = (nearest_cell.x(), nearest_cell.y())
            workspace_id = self.parent().grid_to_workspace.get(grid_pos)
            if workspace_id is not None:
                if workspace_id == -99:
                    workspace_id = "special"
                Hyprland.moveToWorkspaceSilent(self.address, workspace_id)

            parent = self.parent()
            for label in parent.labels:
                label.deleteLater()
            parent.labels.clear()
            parent.clients = Hyprland.clients()
            parent.create_labels()

class GridWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hyprland-Overview")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(1000, 500)
        self.setObjectName("mainWindow")

        self.center_on_screen()

        self.cell_width, self.cell_height = 180, 120
        self.columns, self.rows = 5, 2
        self.margin_x, self.margin_y = 50, 40
        self.h_spacing, self.v_spacing = 5, 5

        self.grid_frames = []
        self.labels = []
        self.grid_to_workspace = {}

        self.clients = Hyprland.clients()
        self.workspaces = Hyprland.workspaces()

        self.create_grid()
        self.create_labels()

    def refresh_clients(self):
        self.clients = Hyprland.clients()
        self.create_labels()

    def center_on_screen(self):
        screen = self.screen().availableGeometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2
        )

    def create_grid(self):
        total_grid_width = self.columns * self.cell_width + (self.columns - 1) * self.h_spacing
        total_grid_height = self.rows * self.cell_height + (self.rows - 1) * self.v_spacing

        start_x = (self.width() - total_grid_width) // 2
        start_y = self.margin_y

        self.grid_origin = (start_x, start_y)

        for row in range(self.rows):
            for col in range(self.columns):
                x = start_x + col * (self.cell_width + self.h_spacing)
                y = start_y + row * (self.cell_height + self.v_spacing)

                frame = QLabel(self)
                frame.setGeometry(x, y, self.cell_width, self.cell_height)
                frame.setObjectName("gridCell")
                frame.lower()
                self.grid_frames.append(frame)
                self.grid_to_workspace[(x, y)] = row * self.columns + col + 1

        special_y = start_y + total_grid_height + 20
        special_x = (self.width() - self.cell_width) // 2

        special_frame = QLabel(self)
        special_frame.setGeometry(special_x, special_y, self.cell_width, self.cell_height)
        special_frame.setObjectName("specialCell")
        special_frame.lower()
        self.grid_frames.append(special_frame)
        self.grid_to_workspace[(special_x, special_y)] = -99
        self.special_frame = special_frame

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            QApplication.quit()

    def create_labels(self):
        start_x, start_y = self.grid_origin
        for client in self.clients:
            workspace = client.get("workspace", {})
            workspace_id = workspace.get("id")
            client_pos = client.get("at", [0, 0])
            client_size = client.get("size", [100, 100])
            window_title = client.get("title", "Unknown")
            if window_title == "Hyprland-Overview":
                continue
            address = client.get("address")

            virtual_width, virtual_height = Hyprland.monitor(0)
            # virtual_width = 1920
            # virtual_height = 1080
            scale_x = self.cell_width / virtual_width
            scale_y = self.cell_height / virtual_height
            scaled_x = int(client_pos[0] * scale_x)
            scaled_y = int(client_pos[1] * scale_y)
            scaled_width = max(40, int(client_size[0] * scale_x))
            scaled_height = max(30, int(client_size[1] * scale_y))

            label = DraggableLabel(window_title, address, self)
            label.setFixedSize(scaled_width, scaled_height)

            if workspace_id == -99:
                cell_x = self.special_frame.x()
                cell_y = self.special_frame.y()
            else:
                found = False
                for (x, y), ws_id in self.grid_to_workspace.items():
                    if ws_id == workspace_id:
                        cell_x, cell_y = x, y
                        found = True
                        break
                if not found:
                    continue

            label.move(cell_x + scaled_x, cell_y + scaled_y)
            label.raise_()
            label.show()
            self.labels.append(label)

def load_stylesheet(app, path):
    try:
        with open(path, "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print(f"Stylesheet not found: {path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Hyprland-Overview")
    load_stylesheet(app, "style.qss")  # Load external stylesheet
    window = GridWindow()
    window.show()
    sys.exit(app.exec())
