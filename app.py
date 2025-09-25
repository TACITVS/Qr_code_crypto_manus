            self._state.camera_available = False
            return None

        try:
            from pyzbar import pyzbar  # type: ignore  # noqa: F401
        except Exception:
            self._state.camera_available = False
            return None

        self._state.camera_available = True
        self._cv2_module = cv2

        group = QGroupBox("Or Scan Using Camera")
        layout = QVBoxLayout()

        self._camera_display = QLabel("Camera preview will appear here")
        self._camera_display.setObjectName("qrDisplayLabel")
        self._camera_display.setAlignment(Qt.AlignCenter)
        self._camera_display.setMinimumSize(320, 240)

        self._camera_status = QLabel("Camera idle")
        self._camera_status.setAlignment(Qt.AlignCenter)
        self._camera_status.setObjectName("SubtleLabel")

        button_row = QHBoxLayout()
        self._camera_start_btn = QPushButton("Start Camera Scan")
        self._camera_stop_btn = QPushButton("Stop Camera")
        self._camera_stop_btn.setEnabled(False)

        self._camera_start_btn.clicked.connect(self._start_camera)
        self._camera_stop_btn.clicked.connect(self._stop_camera)

        button_row.addWidget(self._camera_start_btn)
        button_row.addWidget(self._camera_stop_btn)

        layout.addWidget(self._camera_display)
        layout.addLayout(button_row)
        layout.addWidget(self._camera_status)

        group.setLayout(layout)
        return group

    def _generate_mnemonic(self) -> None:
        try:
            mnemonic = self._mnemonic.generate(self._mnemonic_word_count)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Generation failed: {exc}")
            return

        numbered = "\n".join(
            f"{index + 1:>2}. {word}"
            for index, word in enumerate(mnemonic.split())
        )
        self._mnemonic_display.setText(numbered)
        self._checksum_label.setText(f"Checksum: {MnemonicManager.checksum(mnemonic)}")

        if not self._state.master_password:
            QMessageBox.critical(self, "Error", "No master password set")
            return

        self._app.start_crypto("encrypt", SecureString(mnemonic), self._state.master_password)

    def handle_encrypted(self, payload: Dict[str, str]) -> None:
        self._state.current_encrypted_payload = payload
        if not self._qr.is_available():
            self._qr_preview.setText("QR generation not available")
            return

        try:
            pixmap = self._qr.to_qpixmap(json.dumps(payload))
        except Exception as exc:
            self._qr_preview.setText(f"QR preview failed: {exc}")
            return

        scaled = pixmap.scaled(self._qr_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._qr_preview.setPixmap(scaled)

    def _save_as_qr(self) -> None:
        if not self._state.current_encrypted_payload:
            QMessageBox.warning(self, "Error", "No data to save")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save QR Code", "", "PNG Images (*.png)")
        if not path:
            return

        try:
            self._qr.save_png(json.dumps(self._state.current_encrypted_payload), path)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Save failed: {exc}")
        else:
            QMessageBox.information(self, "Success", "QR code saved successfully")

    def _save_as_json(self) -> None:
        if not self._state.current_encrypted_payload:
            QMessageBox.warning(self, "Error", "No data to save")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save JSON", "", "JSON Files (*.json)")
        if not path:
            return

        data = {
            "app": self._config.app_name,
            "version": self._config.app_version,
            "payload": self._state.current_encrypted_payload,
        }

        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
        except OSError as exc:
            QMessageBox.critical(self, "Error", f"Save failed: {exc}")
        else:
            QMessageBox.information(self, "Success", "JSON saved successfully")

    def _load_qr_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open QR Image", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if not path:
            return

        data = self._qr.read_from_file(path)
        if not data:
            QMessageBox.critical(self, "Error", "Failed to read QR from image")
            return

        self._process_loaded_data(data, f"Loaded: {Path(path).name}")

    def _load_json_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open JSON", "", "JSON Files (*.json)")
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            QMessageBox.critical(self, "Error", f"Load failed: {exc}")
            return

        if "payload" not in data:
            QMessageBox.critical(self, "Error", "Invalid JSON format - missing 'payload'")
            return

        self._process_loaded_data(json.dumps(data["payload"]), f"Loaded: {Path(path).name}")

    def _process_loaded_data(self, payload: str, source: str) -> None:
        try:
            payload_dict = json.loads(payload)
        except json.JSONDecodeError as exc:
            QMessageBox.critical(self, "Error", f"Invalid JSON data: {exc}")
            return

        self._loaded_label.setText(source)

        if not self._state.master_password:
            QMessageBox.critical(self, "Error", "No master password set")
            return

        self._app.start_crypto("decrypt", payload_dict, self._state.master_password)

    def handle_decrypted(self, result: SecureString) -> None:
        try:
            text = result.get()
            self._decrypted_display.setText(text)
            self._verify_checksum.setText(f"Checksum: {MnemonicManager.checksum(text)}")
        finally:
            result.clear()

    def _start_camera(self) -> None:
        if not self._state.camera_available or self._camera_thread:
            return

        self._camera_status.setText("Initialising camera…")
        assert self._camera_start_btn is not None and self._camera_stop_btn is not None
        self._camera_start_btn.setEnabled(False)
        self._camera_stop_btn.setEnabled(True)

        worker = CameraWorker(self._config, self._camera_config)
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.frame_captured.connect(self._on_camera_frame)
        worker.decoded.connect(self._on_camera_decoded)
        worker.status.connect(self._on_camera_status)
        worker.finished.connect(self._on_camera_finished)
        thread.finished.connect(thread.deleteLater)

        self._camera_thread = thread
        self._camera_worker = worker
        thread.start()

    def _stop_camera(self) -> None:
        if self._camera_worker:
            self._camera_worker.stop()
        if self._camera_thread and self._camera_thread.isRunning():
            self._camera_thread.quit()
            self._camera_thread.wait(1500)
        self._camera_thread = None
        self._camera_worker = None

        if self._camera_display:
            self._camera_display.clear()
            self._camera_display.setText("Camera preview will appear here")

        if self._camera_start_btn and self._camera_stop_btn:
            self._camera_start_btn.setEnabled(True)
            self._camera_stop_btn.setEnabled(False)

        if self._camera_status and "QR detected" not in self._camera_status.text():
            self._camera_status.setText("Camera stopped")

    def _on_camera_frame(self, frame) -> None:
        if not self._camera_display or self._cv2_module is None:
            return

        rgb = self._cv2_module.cvtColor(frame, self._cv2_module.COLOR_BGR2RGB)
        height, width, channel = rgb.shape
        image = QImage(rgb.data, width, height, channel * width, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(image.copy())
        target_size = self._camera_display.size()
        if target_size.width() and target_size.height():
            pixmap = pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._camera_display.setPixmap(pixmap)

    def _on_camera_decoded(self, payload: str) -> None:
        if self._camera_status:
            self._camera_status.setText("QR detected – decrypting…")
        self._stop_camera()
        self._process_loaded_data(payload, "Scanned from Camera")

    def _on_camera_status(self, message: str) -> None:
        if self._camera_status:
            self._camera_status.setText(message)

    def _on_camera_finished(self) -> None:
        if self._camera_thread and self._camera_thread.isRunning():
            self._camera_thread.quit()
            self._camera_thread.wait(1500)
        self._camera_thread = None
        self._camera_worker = None

        if self._camera_start_btn and self._camera_stop_btn:
            self._camera_start_btn.setEnabled(True)
            self._camera_stop_btn.setEnabled(False)

        if self._camera_status and self._camera_status.text() == "Initialising camera…":
            self._camera_status.setText("Camera unavailable")

    def stop_camera(self) -> None:
        self._stop_camera()


class SecureQRApp(QMainWindow):  # pragma: no cover - requires Qt event loop
    def __init__(self) -> None:
        super().__init__()

        self._config = AppConfig()
        self._camera_config = CameraConfig()
        self._style = StyleConfig()
        self._state = AppState()

        self._crypto_thread: QThread | None = None
        self._crypto_worker: CryptoWorker | None = None
        self._main_window: MainWindow | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle(f"{self._config.app_name} v{self._config.app_version}")
        self.setGeometry(100, 100, 850, 750)
        self.setMinimumSize(700, 650)

        try:
            self.setWindowIcon(create_icon())
        except RuntimeError:
            pass

        self._apply_stylesheet()

        self._stack = QStackedWidget()
        self._lock_screen = LockScreen(self._config, self._style)
        self._lock_screen.unlocked.connect(self._on_unlocked)
        self._stack.addWidget(self._lock_screen)
        self.setCentralWidget(self._stack)

        self.show()

    def _apply_stylesheet(self) -> None:
        style = self._style
        self.setStyleSheet(
            f"""
            QMainWindow {{ background: {style.bg_primary}; }}
            QWidget {{ color: {style.fg_primary}; font-family: {style.font_family}; font-size: {style.font_size}px; }}
            QTabWidget::pane {{ border: none; }}
            QTabBar::tab {{ background: {style.bg_secondary}; padding: 12px 20px; border: 1px solid {style.border}; border-bottom: none; border-top-left-radius: 5px; border-top-right-radius: 5px; }}
            QTabBar::tab:selected {{ background: {style.bg_tertiary}; color: {style.fg_secondary}; }}
            QGroupBox {{ font-weight: bold; border: 1px solid {style.border}; border-radius: 8px; margin-top: 1ex; padding: 15px; background: {style.bg_secondary}; }}
            QLineEdit, QTextEdit {{ background: {style.bg_primary}; color: {style.fg_secondary}; border: 1px solid {style.border}; border-radius: 4px; padding: 10px; }}
            QLineEdit:focus, QTextEdit:focus {{ border: 1px solid {style.accent_primary}; }}
            QPushButton {{ background: {style.accent_secondary}; color: {style.fg_secondary}; border: none; padding: 12px 18px; border-radius: 4px; font-weight: bold; }}
            QPushButton#AccentButton {{ background: {style.accent_primary}; color: {style.bg_primary}; }}
            QPushButton:hover {{ background: #81A1C1; }}
            #HeaderLabel {{ font-size: 24px; font-weight: bold; color: {style.fg_secondary}; }}
            #SubtleLabel {{ color: #81A1C1; }}
            #WarningLabel {{ background: {style.warning}; color: {style.bg_primary}; padding: 8px; border-radius: 4px; }}
            #SuccessLabel {{ background: {style.success}; color: {style.bg_primary}; padding: 8px; border-radius: 4px; }}
            #ChecksumLabel {{ font-family: {style.font_mono}; font-size: 16px; color: #EBCB8B; font-weight: bold; }}
            #CentralPanel {{ background: {style.bg_tertiary}; border-radius: 8px; padding: 20px; }}
            #qrDisplayLabel {{ border: 2px dashed {style.border}; background: {style.bg_primary}; border-radius: 4px; }}
            """
        )

    def _on_unlocked(self, password: SecureString) -> None:
        self._state.master_password = password
        self._main_window = MainWindow(
            self,
            self._config,
            self._state,
            self._style,
            self._camera_config,
        )
        self._stack.addWidget(self._main_window)
        self._stack.setCurrentWidget(self._main_window)
        self.resize(850, 850)

    def start_crypto(self, mode: str, data: Any, password: SecureString) -> None:
        self.stop_crypto()
        if self._main_window:
            self._main_window.setEnabled(False)

        thread = QThread()
        worker = CryptoWorker(CryptoManager(self._config), mode, data, password)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_crypto_finished)
        worker.error.connect(self._on_crypto_error)
        thread.finished.connect(thread.deleteLater)
        self._crypto_thread = thread
        self._crypto_worker = worker
        thread.start()

    def _on_crypto_finished(self, result: object) -> None:
        try:
            if not self._crypto_worker:
                return

            if self._crypto_worker._mode == "encrypt":
                assert isinstance(self._main_window, MainWindow)
                self._main_window.handle_encrypted(result)  # type: ignore[arg-type]
            else:
                assert isinstance(self._main_window, MainWindow)
                assert isinstance(result, SecureString)
                self._main_window.handle_decrypted(result)
        finally:
            self.stop_crypto()

    def _on_crypto_error(self, message: str) -> None:
        QMessageBox.critical(self, "Crypto Error", message)
        self.stop_crypto()

    def stop_crypto(self) -> None:
        if self._main_window:
            self._main_window.setEnabled(True)

        if self._crypto_thread and self._crypto_thread.isRunning():
            self._crypto_thread.quit()
            if not self._crypto_thread.wait(2000):
                self._crypto_thread.terminate()
                self._crypto_thread.wait()
        self._crypto_thread = None
        self._crypto_worker = None

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.stop_crypto()
        if self._main_window:
            self._main_window.stop_camera()
        if self._state.master_password:
            self._state.master_password.clear()
        self._state.master_password = None
        self._state.current_encrypted_payload = None
        event.accept()


def run() -> int:  # pragma: no cover - requires Qt event loop
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("Secure QR Code Tool")
    window = SecureQRApp()
    return app.exec_()


__all__ = ["run", "SecureQRApp"]
