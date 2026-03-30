from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from d3ahk.automation import AutomationController
from d3ahk.config_store import load_config, load_last_or_default, save_config, sanitize_config_name, list_config_names
from d3ahk.hotkeys import GlobalHotkeyManager
from d3ahk.models import ActionType, AppConfig, HotkeyConfig, TriggerConfig
from d3ahk.supported_inputs import ACTION_OPTIONS, HOTKEY_LETTERS, INPUT_OPTIONS, input_label


class HotkeyDialog(QDialog):
    def __init__(self, title: str, current_hotkey: HotkeyConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(360, 210)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("请选择热键组合: Shift/Ctrl/Alt 可选，字母必选。"))

        self.ctrl_checkbox = QCheckBox("Ctrl")
        self.shift_checkbox = QCheckBox("Shift")
        self.alt_checkbox = QCheckBox("Alt")
        self.ctrl_checkbox.setChecked(current_hotkey.ctrl)
        self.shift_checkbox.setChecked(current_hotkey.shift)
        self.alt_checkbox.setChecked(current_hotkey.alt)

        modifier_row = QHBoxLayout()
        modifier_row.addWidget(self.ctrl_checkbox)
        modifier_row.addWidget(self.shift_checkbox)
        modifier_row.addWidget(self.alt_checkbox)
        modifier_row.addStretch(1)
        layout.addLayout(modifier_row)

        form = QFormLayout()
        self.letter_combo = QComboBox()
        for letter in HOTKEY_LETTERS:
            self.letter_combo.addItem(letter, letter)
        self.letter_combo.setCurrentText(current_hotkey.normalized_letter())
        form.addRow("字母", self.letter_combo)
        layout.addLayout(form)

        button_row = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_row.addStretch(1)
        button_row.addWidget(ok_button)
        button_row.addWidget(cancel_button)
        layout.addLayout(button_row)

    def selected_hotkey(self) -> HotkeyConfig:
        return HotkeyConfig(
            ctrl=self.ctrl_checkbox.isChecked(),
            shift=self.shift_checkbox.isChecked(),
            alt=self.alt_checkbox.isChecked(),
            letter=str(self.letter_combo.currentData() or "S"),
        )


class RuntimeOverlay(QWidget):
    def __init__(self, on_double_click, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_double_click = on_double_click
        self._running = True
        self._title = QLabel("运行中")
        self._title.setAlignment(Qt.AlignCenter)
        self._content = QLabel("")
        self._content.setAlignment(Qt.AlignCenter)
        self._content.setWordWrap(True)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setWindowOpacity(0.84)

        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self._title.setFont(font)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        layout.addWidget(self._title)
        layout.addWidget(self._content)

        self.resize_for_screen()
        self.set_running_state(True)

    def resize_for_screen(self) -> None:
        screen = QApplication.primaryScreen()
        geometry = screen.availableGeometry() if screen else self.geometry()
        width = max(600, geometry.width())
        self.setGeometry(geometry.x(), geometry.y(), width, 110)

    def set_running_state(self, running: bool) -> None:
        self._running = running
        title = "运行中" if running else "已停止"
        color = "rgba(23, 145, 76, 220)" if running else "rgba(180, 42, 42, 220)"
        self._title.setText(title)
        self.setStyleSheet(
            f"background-color: {color}; color: white; border-bottom: 2px solid rgba(255, 255, 255, 80);"
        )

    def update_summary(self, config: AppConfig) -> None:
        active = config.active_triggers()
        if not active:
            self._content.setText("当前没有已配置的按键")
            return
        summary = "    ".join(
            f"{index + 1}. {input_label(trigger.input_code)} / {trigger.interval_ms}ms / {self._action_label(trigger.action)}"
            for index, trigger in enumerate(active)
        )
        self._content.setText(summary)

    def _action_label(self, action: ActionType) -> str:
        if action is ActionType.PRESS:
            return "按下"
        if action is ActionType.RELEASE:
            return "释放"
        return "点击"

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        self.hide()
        self._on_double_click()
        super().mouseDoubleClickEvent(event)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("d3-ahk")
        self.resize(1480, 420)

        self.automation = AutomationController()
        self.current_config = load_last_or_default()
        if self.current_config is None:
            self.current_config = AppConfig.default(self._prompt_new_config_name(initial=True))

        self.overlay = RuntimeOverlay(self.show_configuration_page)
        self.hotkeys = GlobalHotkeyManager(QApplication.instance(), self.toggle_runtime_by_hotkey)

        self.slot_controls: list[dict[str, QComboBox | QSpinBox]] = []
        self.name_label = QLabel("")
        self.toggle_hotkey_label = QLabel("")

        self._build_menu()
        self._build_ui()
        self._load_into_form(self.current_config)
        self._apply_hotkeys()

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()

        hotkey_menu = menu_bar.addMenu("热键")
        toggle_action = QAction("设置开关热键", self)
        toggle_action.triggered.connect(self.change_toggle_hotkey)
        hotkey_menu.addAction(toggle_action)

        config_menu = menu_bar.addMenu("配置")
        load_action = QAction("加载配置", self)
        load_action.triggered.connect(self.choose_and_load_config)
        config_menu.addAction(load_action)

        new_action = QAction("新建配置", self)
        new_action.triggered.connect(self.create_new_config)
        config_menu.addAction(new_action)

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        meta_row = QHBoxLayout()
        self.name_label.setStyleSheet("font-weight: 600;")
        meta_row.addWidget(self.name_label)
        meta_row.addSpacing(24)
        meta_row.addWidget(self.toggle_hotkey_label)
        meta_row.addStretch(1)
        layout.addLayout(meta_row)

        slots_widget = QWidget()
        slots_layout = QGridLayout(slots_widget)
        slots_layout.setHorizontalSpacing(10)
        slots_layout.setVerticalSpacing(10)

        for index in range(10):
            column = QWidget()
            column_layout = QVBoxLayout(column)
            column_layout.setContentsMargins(8, 8, 8, 8)
            column_layout.setSpacing(8)
            column.setStyleSheet(
                "background: #f4f7fb; border: 1px solid #d1d9e6; border-radius: 8px;"
            )

            title_label = QLabel(f"按键 {index + 1}")
            title_label.setStyleSheet("font-weight: 600;")
            column_layout.addWidget(title_label)

            key_combo = QComboBox()
            for value, label in INPUT_OPTIONS:
                key_combo.addItem(label, value)
            column_layout.addWidget(QLabel("触发按键"))
            column_layout.addWidget(key_combo)

            action_combo = QComboBox()
            for label, action in ACTION_OPTIONS:
                action_combo.addItem(label, action)
            column_layout.addWidget(QLabel("动作"))
            column_layout.addWidget(action_combo)

            interval_spin = QSpinBox()
            interval_spin.setRange(1, 3_600_000)
            interval_spin.setSuffix(" ms")
            interval_spin.setSingleStep(10)
            column_layout.addWidget(QLabel("触发间隔"))
            column_layout.addWidget(interval_spin)
            column_layout.addStretch(1)

            self.slot_controls.append(
                {"key": key_combo, "action": action_combo, "interval": interval_spin}
            )

            row = index // 5
            col = index % 5
            slots_layout.addWidget(column, row, col)

        layout.addWidget(slots_widget)

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        start_button = QPushButton("启动")
        start_button.setMinimumHeight(38)
        start_button.clicked.connect(self.start_runtime)
        action_row.addWidget(start_button)
        layout.addLayout(action_row)

        self.setCentralWidget(root)

    def _load_into_form(self, config: AppConfig) -> None:
        self.current_config = config
        self.current_config.ensure_slot_count()
        self.name_label.setText(f"当前配置: {config.name}")
        self.toggle_hotkey_label.setText(f"开关热键: {config.toggle_hotkey.display()}")

        for control, trigger in zip(self.slot_controls, config.triggers):
            key_combo: QComboBox = control["key"]  # type: ignore[assignment]
            action_combo: QComboBox = control["action"]  # type: ignore[assignment]
            interval_spin: QSpinBox = control["interval"]  # type: ignore[assignment]

            key_index = key_combo.findData(trigger.input_code)
            key_combo.setCurrentIndex(max(key_index, 0))

            action_index = action_combo.findData(trigger.action)
            action_combo.setCurrentIndex(max(action_index, 0))

            interval_spin.setValue(trigger.interval_ms)

        self.overlay.update_summary(config)

    def _collect_from_form(self) -> AppConfig:
        triggers: list[TriggerConfig] = []
        for control in self.slot_controls:
            key_combo: QComboBox = control["key"]  # type: ignore[assignment]
            action_combo: QComboBox = control["action"]  # type: ignore[assignment]
            interval_spin: QSpinBox = control["interval"]  # type: ignore[assignment]
            triggers.append(
                TriggerConfig(
                    input_code=str(key_combo.currentData() or ""),
                    action=TriggerConfig.normalize_action(action_combo.currentData()),
                    interval_ms=int(interval_spin.value()),
                )
            )

        return AppConfig(
            name=sanitize_config_name(self.current_config.name),
            toggle_hotkey=HotkeyConfig(
                ctrl=self.current_config.toggle_hotkey.ctrl,
                shift=self.current_config.toggle_hotkey.shift,
                alt=self.current_config.toggle_hotkey.alt,
                letter=self.current_config.toggle_hotkey.normalized_letter(),
            ),
            triggers=triggers,
        )

    def _apply_hotkeys(self) -> None:
        config = self._collect_from_form()
        if not config.toggle_hotkey.has_modifier():
            QMessageBox.warning(self, "热键无效", "请至少选择一个修饰键: Shift/Ctrl/Alt。")
            return

        try:
            self.hotkeys.register(config.toggle_hotkey)
        except RuntimeError as exc:
            QMessageBox.critical(self, "热键注册失败", str(exc))

    def _prompt_new_config_name(self, initial: bool = False) -> str:
        prompt = "请输入新配置名称" if not initial else "未找到配置，请先输入配置名称"
        while True:
            name, ok = QInputDialog.getText(self, "新建配置", prompt)
            if ok and sanitize_config_name(name):
                return sanitize_config_name(name)
            if not initial:
                return sanitize_config_name(self.current_config.name)
            QMessageBox.information(self, "需要配置", "必须先创建一个配置才能启动应用。")

    def create_new_config(self) -> None:
        name = self._prompt_new_config_name()
        self._load_into_form(AppConfig.default(name))

    def choose_and_load_config(self) -> None:
        names = list_config_names()
        if not names:
            QMessageBox.information(self, "没有配置", "当前没有已保存配置，请先新建配置并启动一次。")
            return

        name, ok = QInputDialog.getItem(self, "加载配置", "选择配置", names, editable=False)
        if not ok:
            return

        self._load_into_form(load_config(name))
        self._apply_hotkeys()

    def change_toggle_hotkey(self) -> None:
        dialog = HotkeyDialog("设置开关热键", self.current_config.toggle_hotkey, self)
        if dialog.exec() != QDialog.Accepted:
            return
        hotkey = dialog.selected_hotkey()
        if not hotkey.has_modifier():
            QMessageBox.warning(self, "热键无效", "请至少选择一个修饰键: Shift/Ctrl/Alt。")
            return
        self.current_config.toggle_hotkey = hotkey
        self._load_into_form(self._collect_from_form())
        self._apply_hotkeys()

    def toggle_runtime_by_hotkey(self) -> None:
        if self.automation.running:
            self.stop_runtime()
            return

        if self.isVisible():
            self.start_runtime()
            return

        self._start_runtime(use_form=False)

    def start_runtime(self) -> None:
        self._start_runtime(use_form=True)

    def _start_runtime(self, use_form: bool) -> None:
        config = self._collect_from_form() if use_form else self.current_config
        if not config.active_triggers():
            QMessageBox.warning(self, "无法启动", "至少需要配置一个触发按键。")
            return

        if not config.toggle_hotkey.has_modifier():
            QMessageBox.warning(self, "热键无效", "请至少选择一个修饰键: Shift/Ctrl/Alt。")
            return

        self.current_config = config
        save_config(self.current_config)
        try:
            self.hotkeys.register(self.current_config.toggle_hotkey)
        except RuntimeError as exc:
            QMessageBox.critical(self, "热键注册失败", str(exc))
            return
        self.automation.start(self.current_config.active_triggers())
        self.overlay.update_summary(self.current_config)
        self.overlay.set_running_state(True)
        self.overlay.resize_for_screen()
        self.overlay.show()
        self.hide()

    def stop_runtime(self) -> None:
        self.automation.stop()
        self.overlay.set_running_state(False)
        if self.overlay.isHidden():
            self.overlay.show()

    def show_configuration_page(self) -> None:
        self.automation.stop()
        self.overlay.hide()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.automation.stop()
        self.hotkeys.unregister()
        self.overlay.close()
        super().closeEvent(event)


def build_application() -> tuple[QApplication, MainWindow]:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("d3-ahk")
    window = MainWindow()
    return app, window


def run() -> None:
    app, window = build_application()
    window.show()
    sys.exit(app.exec())
