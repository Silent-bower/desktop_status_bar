import importlib.machinery
import importlib.util
import pathlib
import unittest
import contextlib


def load_status_bar_module():
    module_path = pathlib.Path(__file__).with_name("status_bar.pyw")
    loader = importlib.machinery.SourceFileLoader("status_bar_module", str(module_path))
    spec = importlib.util.spec_from_loader("status_bar_module", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


status_bar = load_status_bar_module()


class TopLauncherLayoutTests(unittest.TestCase):
    def test_top_mode_window_width_expands_for_two_columns(self):
        self.assertEqual(status_bar.compute_window_width(186, top_center_mode=True), 560)
        self.assertEqual(status_bar.compute_window_width(186, top_center_mode=False), 186)

    def test_build_shortcut_grid_rows_fills_second_column_and_keeps_last_gap(self):
        shortcuts = [
            {"name": "OpenCode"},
            {"name": "SketchUp"},
            {"name": "AutoCAD"},
        ]

        rows = status_bar.build_shortcut_grid_rows(shortcuts, columns=2)

        self.assertEqual(rows[0][0]["name"], "OpenCode")
        self.assertEqual(rows[0][1]["name"], "SketchUp")
        self.assertEqual(rows[1][0]["name"], "AutoCAD")
        self.assertIsNone(rows[1][1])

    def test_format_shortcut_text_truncates_only_when_needed(self):
        self.assertEqual(
            status_bar.format_shortcut_text("📁", "OpenCode", max_name_chars=20),
            " 📁  OpenCode",
        )
        self.assertEqual(
            status_bar.format_shortcut_text("📁", "VeryLongApplicationName", max_name_chars=10),
            " 📁  VeryLon...",
        )

    def test_top_mode_height_limit_is_reduced_for_flatter_layout(self):
        self.assertEqual(status_bar.compute_available_height(1200, top_center_mode=True), 214)
        self.assertEqual(status_bar.compute_available_height(1200, top_center_mode=False), 1008)

    def test_top_monitor_rows_switch_to_inline_layout(self):
        top_layout = status_bar.get_stat_row_layout(top_center_mode=True)
        side_layout = status_bar.get_stat_row_layout(top_center_mode=False)

        self.assertTrue(top_layout["inline"])
        self.assertEqual(top_layout["canvas_height"], 8)
        self.assertFalse(side_layout["inline"])
        self.assertEqual(side_layout["canvas_height"], 10)

    def test_top_launch_spacing_gets_tighter_without_shrinking_buttons(self):
        top_spacing = status_bar.get_launch_spacing(top_center_mode=True)
        side_spacing = status_bar.get_launch_spacing(top_center_mode=False)

        self.assertLess(top_spacing["header_pady"], side_spacing["header_pady"])
        self.assertLess(top_spacing["group_top_pady"], side_spacing["group_top_pady"])
        self.assertEqual(top_spacing["button_pady"], side_spacing["button_pady"])

    def test_top_launch_height_is_capped_by_remaining_window_space(self):
        launch_h = status_bar.compute_top_launch_height(
            available_height=214,
            header_height=24,
            launch_header_height=18,
            desired_launch_height=240,
        )

        self.assertEqual(launch_h, 164)

    def test_top_runtime_launch_canvas_does_not_exceed_window_height(self):
        app = status_bar.StatusBar()
        try:
            app.root.update_idletasks()
            self.assertLessEqual(app._launch_canvas.winfo_height(), app.root.winfo_height())
        finally:
            with contextlib.suppress(Exception):
                app.root.destroy()


if __name__ == "__main__":
    unittest.main()
