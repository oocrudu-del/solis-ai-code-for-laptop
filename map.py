import sys
import os
import json
import uuid
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsPathItem, QVBoxLayout, QHBoxLayout, QWidget, QFrame, QLabel, 
    QPushButton, QLineEdit, QTextEdit, QComboBox, QSlider, QDockWidget, 
    QMessageBox, QInputDialog, QListWidget, QDialog
)
from PyQt6.QtCore import (
    Qt, QPointF, QRectF, pyqtSignal
)
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QFont, QPainterPath, QLinearGradient
)

# Create Projects directory at startup
os.makedirs("Project", exist_ok=True)

# --- THEME COLORS ---
THEME = {
    "bg_dark": "#06070d",
    "bg_panel": "#10121b",
    "accent_blue": "#00f2ff",
    "accent_purple": "#7000ff",
    "text_main": "#e0e0e0",
    "text_dim": "#a0a0a0",
    "border": "#1f2230",
    "status_planned": "#555555",
    "status_progress": "#009dff",
    "status_testing": "#ff9d00",
    "status_completed": "#00ff88",
    "grid": "#161823"
}

# --- DATA MODEL ---
class FeatureNodeData:
    def __init__(self, name="New Feature"):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = "Feature details here..."
        self.priority = "Medium"
        self.status = "Planned"
        self.progress = 0
        self.pos_x = 0.0
        self.pos_y = 0.0
        self.connections = [] # List of connected Node IDs

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(data):
        node = FeatureNodeData()
        for key, value in data.items():
            setattr(node, key, value)
        return node

# --- GRAPHICS: CONNECTOR LINE ---
class EdgeItem(QGraphicsPathItem):
    def __init__(self, source_item, dest_item):
        super().__init__()
        self.source_item = source_item
        self.dest_item = dest_item
        self.setZValue(-1)
        self.update_path()

    def update_path(self):
        if not self.source_item or not self.dest_item: return
        path = QPainterPath()
        start = self.source_item.sceneBoundingRect().center()
        end = self.dest_item.sceneBoundingRect().center()
        path.moveTo(start)
        # Smooth Cubic Curve
        cp1 = QPointF(start.x() + (end.x() - start.x()) / 2, start.y())
        cp2 = QPointF(start.x() + (end.x() - start.x()) / 2, end.y())
        path.cubicTo(cp1, cp2, end)
        self.setPath(path)
        self.setPen(QPen(QColor(THEME["accent_blue"]), 2, Qt.PenStyle.SolidLine))

# --- GRAPHICS: NODE BOX ---
class NodeItem(QGraphicsItem):
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.width, self.height = 190, 110
        self.rect = QRectF(0, 0, self.width, self.height)
        self.edges = []
        
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setPos(data.pos_x, data.pos_y)

    def boundingRect(self):
        return self.rect.adjusted(-5, -5, 5, 5)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Shadow/Glow
        if self.isSelected():
            painter.setBrush(QBrush(QColor(112, 0, 255, 80)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(self.rect.adjusted(-4, -4, 4, 4), 12, 12)

        # Main Body
        grad = QLinearGradient(0, 0, 0, self.height)
        grad.setColorAt(0, QColor(THEME["bg_panel"]))
        grad.setColorAt(1, QColor(THEME["bg_dark"]))
        painter.setBrush(QBrush(grad))
        
        border_col = THEME["accent_blue"] if self.isSelected() else THEME["border"]
        painter.setPen(QPen(QColor(border_col), 2))
        painter.drawRoundedRect(self.rect, 10, 10)

        # Title
        painter.setPen(QPen(QColor(THEME["text_main"])))
        painter.setFont(QFont("Orbitron", 9, QFont.Weight.Bold))
        painter.drawText(QRectF(15, 12, self.width-30, 25), Qt.AlignmentFlag.AlignLeft, self.data.name)
        
        # Description
        painter.setPen(QPen(QColor(THEME["text_dim"])))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(QRectF(15, 40, self.width-30, 45), Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, self.data.description)
        
        # Progress Bar
        painter.setBrush(QBrush(QColor("#000000")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(15, 90, self.width-30, 6, 3, 3)
        painter.setBrush(QBrush(QColor(THEME["accent_blue"])))
        painter.drawRoundedRect(15, 90, int((self.width-30)*(self.data.progress/100)), 6, 3, 3)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            if hasattr(self, 'data'):
                self.data.pos_x, self.data.pos_y = value.x(), value.y()
            for edge in self.edges: edge.update_path()
        return super().itemChange(change, value)

# --- ZOOMABLE CANVAS ---
class RoadmapView(QGraphicsView):
    node_clicked = pyqtSignal(object)

    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor(THEME["bg_dark"])))
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def wheelEvent(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
        else:
            self.scale(zoom_out_factor, zoom_out_factor)

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if isinstance(item, NodeItem):
            self.node_clicked.emit(item)
        super().mousePressEvent(event)

# --- PROJECT HISTORY DIALOG ---
class HistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Project History")
        self.resize(380, 450)
        self.setStyleSheet(f"background-color: {THEME['bg_panel']}; color: white; font-family: 'Segoe UI';")
        
        layout = QVBoxLayout(self)
        
        self.label = QLabel("Select a project to load:")
        self.label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(self.label)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            "background-color: #06070d; border: 1px solid #1f2230; color: #e0e0e0; "
            "padding: 8px; border-radius: 6px; font-size: 13px;"
        )
        layout.addWidget(self.list_widget)
        
        self.populate_projects()
        
        btn_layout = QHBoxLayout()
        self.btn_load = QPushButton("📂 LOAD")
        self.btn_load.setStyleSheet(f"background-color: {THEME['accent_purple']}; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        self.btn_load.clicked.connect(self.accept)
        
        self.btn_cancel = QPushButton("CANCEL")
        self.btn_cancel.setStyleSheet("background-color: #2b2e3c; color: white; padding: 8px; border-radius: 4px;")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def populate_projects(self):
        if not os.path.exists("Project"):
            return
        files = [f[:-5] for f in os.listdir("Project") if f.endswith(".json")]
        self.list_widget.addItems(files)

    def get_selected_project(self):
        selected = self.list_widget.currentItem()
        return selected.text() if selected else None

# --- MAIN STUDIO ---
class SolisRoadmapStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SOLIS AI ROADMAP STUDIO")
        self.resize(1400, 900)
        self.nodes = {}
        self.conn_mode = False
        self.source_node = None

        self.init_ui()
        self.setup_default_roadmap()

    def init_ui(self):
        self.setStyleSheet(f"background-color: {THEME['bg_dark']}; color: white; font-family: 'Segoe UI';")
        
        # Canvas
        self.scene = QGraphicsScene(-5000, -5000, 10000, 10000)
        self.view = RoadmapView(self.scene)
        self.view.node_clicked.connect(self.handle_node_selection)
        self.setCentralWidget(self.view)

        # Docks
        self.create_left_panel()
        self.create_right_panel()

    def create_left_panel(self):
        dock = QDockWidget(" CONTROL CENTER", self)
        container = QFrame()
        layout = QVBoxLayout(container)

        self.btn_add = QPushButton("➕ ADD NEW MODULE")
        self.btn_add.clicked.connect(self.add_custom_node)
        
        self.btn_conn = QPushButton("🔗 CONNECT MODULES")
        self.btn_conn.clicked.connect(self.start_connection)

        # --- NEW EXTRA FEATURE: SEARCH & HIGHLIGHT MODULE ---
        layout.addWidget(QLabel("SEARCH ROADMAP"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search module name/details...")
        self.search_box.setStyleSheet(
            "background-color: #0a0b10; border: 1px solid #1f2230; "
            "color: #00f2ff; padding: 6px; border-radius: 4px;"
        )
        self.search_box.textChanged.connect(self.filter_modules)
        layout.addWidget(self.search_box)
        # ----------------------------------------------------
        
        self.stats_box = QTextEdit()
        self.stats_box.setReadOnly(True)
        self.stats_box.setStyleSheet("background: #0a0b10; border: 1px solid #1f2230; color: #00f2ff;")

        layout.addWidget(QLabel("TOOLS"))
        layout.addWidget(self.btn_add)
        layout.addWidget(self.btn_conn)
        layout.addWidget(QLabel("PROJECT STATS"))
        layout.addWidget(self.stats_box)
        
        # Save Button
        btn_save = QPushButton("💾 SAVE PROJECT")
        btn_save.setStyleSheet("background-color: #102a45; color: #00f2ff;")
        btn_save.clicked.connect(self.save_project_flow)
        layout.addWidget(btn_save)

        # History Button
        btn_history = QPushButton("📜 PROJECT HISTORY")
        btn_history.setStyleSheet(f"background-color: {THEME['accent_purple']}; color: white;")
        btn_history.clicked.connect(self.show_history_dialog)
        layout.addWidget(btn_history)

        layout.addStretch()
        dock.setWidget(container)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

    def create_right_panel(self):
        dock = QDockWidget(" MODULE PROPERTIES", self)
        container = QFrame()
        layout = QVBoxLayout(container)

        self.ed_name = QLineEdit()
        self.ed_desc = QTextEdit()
        self.ed_status = QComboBox()
        self.ed_status.addItems(["Planned", "In Progress", "Testing", "Completed"])
        self.ed_prog = QSlider(Qt.Orientation.Horizontal)
        self.ed_prog.setRange(0, 100)

        layout.addWidget(QLabel("MODULE NAME"))
        layout.addWidget(self.ed_name)
        layout.addWidget(QLabel("DESCRIPTION"))
        layout.addWidget(self.ed_desc)
        layout.addWidget(QLabel("STATUS"))
        layout.addWidget(self.ed_status)
        layout.addWidget(QLabel("PROGRESS %"))
        layout.addWidget(self.ed_prog)

        btn_upd = QPushButton("✅ APPLY CHANGES")
        btn_upd.clicked.connect(self.update_node_data)
        layout.addWidget(btn_upd)

        btn_del = QPushButton("🗑️ DELETE MODULE")
        btn_del.setStyleSheet("background-color: #500;")
        btn_del.clicked.connect(self.delete_selected)
        layout.addWidget(btn_del)

        layout.addStretch()
        dock.setWidget(container)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        self.current_node = None

    def setup_default_roadmap(self):
        # SOLIS AI Structure
        structure = {
            "SOLIS AI CORE": ["Memory System", "AI Chat", "Voice Assistant", "Personality Engine"],
            "COMMUNICATION": ["Personal Chat", "Group Chat", "Video Calls"],
            "AI GENERATION": ["Image Gen", "Video Gen", "Music Gen", "Coding Assistant"],
            "PLATFORMS": ["Windows App", "Android App", "iOS App"],
            "SECURITY": ["Encryption", "Cloud Backup", "Google Login"]
        }

        root = self.spawn_node("SOLIS AI", 0, 0)
        
        y_off = -400
        for cat, items in structure.items():
            cat_node = self.spawn_node(cat, 350, y_off)
            self.create_link(root, cat_node)
            
            sub_y = y_off - 100
            for item in items:
                sub_node = self.spawn_node(item, 700, sub_y)
                self.create_link(cat_node, sub_node)
                sub_y += 130
            y_off += 450
        self.update_stats()

    def spawn_node(self, name, x, y):
        data = FeatureNodeData(name)
        data.pos_x, data.pos_y = x, y
        item = NodeItem(data)
        self.scene.addItem(item)
        self.nodes[data.id] = item
        return item

    def add_custom_node(self):
        center = self.view.mapToScene(self.view.viewport().rect().center())
        self.spawn_node("New Module", center.x(), center.y())
        self.update_stats()

    def handle_node_selection(self, item):
        if self.conn_mode:
            self.finish_connection(item)
        else:
            self.current_node = item
            self.ed_name.setText(item.data.name)
            self.ed_desc.setPlainText(item.data.description)
            self.ed_status.setCurrentText(item.data.status)
            self.ed_prog.setValue(item.data.progress)

    def update_node_data(self):
        if not self.current_node: return
        self.current_node.data.name = self.ed_name.text()
        self.current_node.data.description = self.ed_desc.toPlainText()
        self.current_node.data.status = self.ed_status.currentText()
        self.current_node.data.progress = self.ed_prog.value()
        self.current_node.update()
        self.update_stats()

    def start_connection(self):
        sel = self.scene.selectedItems()
        if sel and isinstance(sel[0], NodeItem):
            self.conn_mode = True
            self.source_node = sel[0]
            self.btn_conn.setText("🎯 SELECT TARGET...")
            self.btn_conn.setStyleSheet("background: #7000ff;")
        else:
            QMessageBox.information(self, "Link", "First select a source module box!")

    def finish_connection(self, target_node):
        if self.source_node and target_node != self.source_node:
            self.create_link(self.source_node, target_node)
        self.conn_mode = False
        self.btn_conn.setText("🔗 CONNECT MODULES")
        self.btn_conn.setStyleSheet("")

    def create_link(self, n1, n2):
        edge = EdgeItem(n1, n2)
        self.scene.addItem(edge)
        n1.edges.append(edge)
        n2.edges.append(edge)
        if n2.data.id not in n1.data.connections:
            n1.data.connections.append(n2.data.id)

    def delete_selected(self):
        if self.current_node:
            for e in self.current_node.edges[:]: self.scene.removeItem(e)
            self.scene.removeItem(self.current_node)
            del self.nodes[self.current_node.data.id]
            self.current_node = None
            self.update_stats()

    def update_stats(self):
        total = len(self.nodes)
        done = sum(1 for n in self.nodes.values() if n.data.status == "Completed")
        prog = sum(n.data.progress for n in self.nodes.values()) / total if total > 0 else 0
        self.stats_box.setPlainText(f"--- SOLIS REPORT ---\nTotal Modules: {total}\nCompleted: {done}\nOverall Progress: {int(prog)}%")

    # --- SEARCH & HIGHLIGHT MODULE FEATURE ---
    def filter_modules(self, text):
        query = text.lower().strip()
        for node_id, node_item in self.nodes.items():
            if not query:
                node_item.setOpacity(1.0)
            else:
                match_name = query in node_item.data.name.lower()
                match_desc = query in node_item.data.description.lower()
                if match_name or match_desc:
                    node_item.setOpacity(1.0)
                else:
                    node_item.setOpacity(0.25)

    # --- SAVE TO THE "Project" FOLDER ---
    def save_project_flow(self):
        name, ok = QInputDialog.getText(self, "Save Project", "Enter Project Name:")
        if ok and name.strip():
            project_name = name.strip()
            filename = f"{project_name}.json"
            filepath = os.path.join("Project", filename)

            # Confirm overwrite if file exists
            if os.path.exists(filepath):
                ret = QMessageBox.question(
                    self, "Confirm Overwrite", 
                    f"A project named '{project_name}' already exists. Overwrite?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if ret == QMessageBox.StandardButton.No:
                    return

            data = [n.data.to_dict() for n in self.nodes.values()]
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                QMessageBox.information(self, "Success", f"Project successfully saved in 'Project/{filename}'")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Unable to save project: {str(e)}")

    # --- LOAD FROM HISTORY ---
    def show_history_dialog(self):
        dlg = HistoryDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected = dlg.get_selected_project()
            if selected:
                self.load_project(selected)

    def load_project(self, project_name):
        filepath = os.path.join("Project", f"{project_name}.json")
        if not os.path.exists(filepath):
            QMessageBox.warning(self, "Error", "Project file not found.")
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data_list = json.load(f)

            # Clear current canvas & data
            self.scene.clear()
            self.nodes.clear()
            self.current_node = None

            # 1. Spawn Nodes
            for d in data_list:
                node_data = FeatureNodeData.from_dict(d)
                item = NodeItem(node_data)
                self.scene.addItem(item)
                self.nodes[node_data.id] = item

            # 2. Re-establish Connection Edges
            connected_pairs = set()
            for n_id, item in self.nodes.items():
                for conn_id in item.data.connections:
                    if conn_id in self.nodes:
                        pair = tuple(sorted((n_id, conn_id)))
                        if pair not in connected_pairs:
                            self.create_link(item, self.nodes[conn_id])
                            connected_pairs.add(pair)

            self.update_stats()
            self.search_box.clear() # Reset search bar
            QMessageBox.information(self, "Loaded", f"Project '{project_name}' restored successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Could not load workspace configuration: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = SolisRoadmapStudio()
    win.showMaximized()
    sys.exit(app.exec())