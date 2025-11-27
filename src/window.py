# window.py
#
# Copyright 2025 Flavio de Vasconcellos Corrêa
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Adw, Gtk, Gio, Gdk
import cairo
from pathlib import Path

from .canvas import AssetsCanvas
from .output_panel import OutputPanel


@Gtk.Template(resource_path='/com/github/sheep/farm/assets/window.ui')
class AssetsWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'AssetsWindow'

    # Template widgets
    sidebar_toggle = Gtk.Template.Child()
    run_button = Gtk.Template.Child()
    result_toggle = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    split_view = Gtk.Template.Child()
    toolbar_box = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    favorites_toggle = Gtk.Template.Child()
    import_button = Gtk.Template.Child()
    export_button = Gtk.Template.Child()
    node_list = Gtk.Template.Child()
    main_paned = Gtk.Template.Child()
    canvas_box = Gtk.Template.Child()
    result_box = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Estado para controle do painel de resultado
        self.result_panel_visible = True
        self.result_panel_height = 200

        # Estado de população
        self._is_populating = False

        # Conectar signals do Toolbar
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.favorites_toggle.connect("toggled", self._on_favorites_toggled)
        self.import_button.connect("clicked", self._on_import_library)
        self.export_button.connect("clicked", self._on_export_library)

        # Conectar signals dos botões principais
        self.run_button.connect("clicked", self._on_run_graph)
        self.result_toggle.connect("toggled", self._on_result_toggle)

        # Estado do arquivo
        self.current_file = None

        # Popular lista inicial de nodes
        self._populate_node_list()

        # Criar canvas
        self.canvas = AssetsCanvas()

        # Colocar canvas dentro de ScrolledWindow
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_vexpand(True)
        self.scrolled_window.set_hexpand(True)
        self.scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.set_child(self.canvas)

        self.canvas_box.append(self.scrolled_window)

        # Criar e adicionar output panel
        self.output_panel = OutputPanel()
        self.output_panel.set_vexpand(True)
        self.output_panel.set_hexpand(True)
        self.result_box.append(self.output_panel)

        # Setup canvas actions (menu de contexto)
        self._setup_canvas_actions()

        # Setup window actions
        self._create_actions()

        # Note: Canvas will grab focus when clicked (see canvas.py on_mouse_pressed)
        # We don't grab focus on startup to avoid interfering with search entry

        # Connect close handler to cleanup
        self.connect("close-request", self._on_close_request)

    def _setup_canvas_actions(self):
        """Setup actions for canvas context menu"""
        # Edit Code action
        edit_action = Gio.SimpleAction.new("edit-code", None)
        edit_action.connect("activate", lambda a, p: self.canvas.edit_node_code())
        self.canvas.action_group.add_action(edit_action)

        # Rename action
        rename_action = Gio.SimpleAction.new("rename", None)
        rename_action.connect("activate", lambda a, p: self.canvas.rename_node())
        self.canvas.action_group.add_action(rename_action)

        # Properties action
        props_action = Gio.SimpleAction.new("properties", None)
        props_action.connect("activate", lambda a, p: self.canvas.show_node_properties())
        self.canvas.action_group.add_action(props_action)

        # Save to Library action
        save_lib_action = Gio.SimpleAction.new("save-to-library", None)
        save_lib_action.connect("activate", lambda a, p: self.canvas.save_node_to_library())
        self.canvas.action_group.add_action(save_lib_action)

        # Delete action
        delete_action = Gio.SimpleAction.new("delete", None)
        delete_action.connect("activate", lambda a, p: self.canvas.delete_context_node())
        self.canvas.action_group.add_action(delete_action)

        # Alignment actions
        align_left = Gio.SimpleAction.new("align-left", None)
        align_left.connect("activate", lambda a, p: self.canvas.align_selected_nodes("left"))
        self.canvas.action_group.add_action(align_left)

        align_center_h = Gio.SimpleAction.new("align-center-h", None)
        align_center_h.connect("activate", lambda a, p: self.canvas.align_selected_nodes("center-h"))
        self.canvas.action_group.add_action(align_center_h)

        align_right = Gio.SimpleAction.new("align-right", None)
        align_right.connect("activate", lambda a, p: self.canvas.align_selected_nodes("right"))
        self.canvas.action_group.add_action(align_right)

        align_top = Gio.SimpleAction.new("align-top", None)
        align_top.connect("activate", lambda a, p: self.canvas.align_selected_nodes("top"))
        self.canvas.action_group.add_action(align_top)

        align_center_v = Gio.SimpleAction.new("align-center-v", None)
        align_center_v.connect("activate", lambda a, p: self.canvas.align_selected_nodes("center-v"))
        self.canvas.action_group.add_action(align_center_v)

        align_bottom = Gio.SimpleAction.new("align-bottom", None)
        align_bottom.connect("activate", lambda a, p: self.canvas.align_selected_nodes("bottom"))
        self.canvas.action_group.add_action(align_bottom)

        # Distribution actions
        distribute_h = Gio.SimpleAction.new("distribute-h", None)
        distribute_h.connect("activate", lambda a, p: self.canvas.distribute_selected_nodes("horizontal"))
        self.canvas.action_group.add_action(distribute_h)

        distribute_v = Gio.SimpleAction.new("distribute-v", None)
        distribute_v.connect("activate", lambda a, p: self.canvas.distribute_selected_nodes("vertical"))
        self.canvas.action_group.add_action(distribute_v)

        # Connect canvas signal to update node list when library changes
        # self.canvas.connect("node-saved-to-library", lambda c: self._populate_node_list())

    def _create_actions(self):
        """Create window actions"""
        # New
        new_action = Gio.SimpleAction.new("new", None)
        new_action.connect("activate", self.on_new)
        self.add_action(new_action)

        # Open
        open_action = Gio.SimpleAction.new("open", None)
        open_action.connect("activate", self.on_open)
        self.add_action(open_action)

        # Save
        save_action = Gio.SimpleAction.new("save", None)
        save_action.connect("activate", self.on_save)
        self.add_action(save_action)

        # Save As
        save_as_action = Gio.SimpleAction.new("save-as", None)
        save_as_action.connect("activate", self._on_save_as)
        self.add_action(save_as_action)


    def on_new(self, action, param):
        """Handle New action"""
        # TODO: Ask if user wants to save changes before clearing
        self.canvas.nodes.clear()
        self.canvas.connections.clear()
        self.current_file = None
        self.canvas.queue_draw()
        print("✓ New graph created")

    def on_open(self, action, param):
        """Handle Open action"""
        from .graph_io import GraphSerializer

        dialog = Gtk.FileDialog()
        dialog.set_title("Open Graph")

        # Filter for .assets files
        filter_assets = Gtk.FileFilter()
        filter_assets.set_name("Assets Files (*.assets)")
        filter_assets.add_pattern("*.assets")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_assets)
        dialog.set_filters(filters)

        dialog.open(self, None, self._on_open_finish)

    def _on_open_finish(self, dialog, result):
        """Callback for open dialog"""
        try:
            file = dialog.open_finish(result)
            if file:
                from .graph_io import GraphSerializer
                from .node import Node
                filepath = file.get_path()

                # Load graph data (returns dict with raw data)
                graph_data = GraphSerializer.load_graph(filepath)

                if graph_data is not None:
                    # Deserialize nodes
                    nodes = []
                    node_id_map = {}

                    for node_data in graph_data.get("nodes", []):
                        node = Node.from_dict(node_data)
                        nodes.append(node)
                        node_id_map[node.id] = node

                    # Deserialize connections
                    connections = []
                    for conn_data in graph_data.get("connections", []):
                        src_id = conn_data["source_node_id"]
                        dst_id = conn_data["target_node_id"]

                        if src_id in node_id_map and dst_id in node_id_map:
                            connection = (
                                node_id_map[src_id],
                                conn_data["source_port"],
                                node_id_map[dst_id],
                                conn_data["target_port"]
                            )
                            connections.append(connection)
                        else:
                            print(f"⚠️  Invalid connection ignored: {src_id} -> {dst_id}")

                    # Update canvas
                    self.canvas.nodes = nodes
                    self.canvas.connections = connections
                    self.current_file = filepath

                    # Pre-calculate port positions for all nodes
                    # This ensures connections can be drawn immediately
                    for node in nodes:
                        node._calculate_port_positions()

                    # Update canvas size based on nodes and zoom
                    self.canvas._update_canvas_size()

                    self.canvas.queue_draw()

                    print(f"✓ Graph loaded: {filepath}")
                    print(f"  - {len(nodes)} nodes")
                    print(f"  - {len(connections)} connections")
                else:
                    print(f"❌ Failed to load: {filepath}")
                    toast = Adw.Toast.new(f"Failed to load: {filepath}")
                    self.toast_overlay.add_toast(toast)
        except Exception as e:
            if "dismissed" not in str(e).lower():
                print(f"❌ Error opening: {e}")
                import traceback
                traceback.print_exc()
                toast = Adw.Toast.new(f"Error opening file: {e}")
                self.toast_overlay.add_toast(toast)

    def on_save(self, action, param):
        """Handle Save action"""
        if self.current_file:
            self._save_to_file(self.current_file)
        else:
            self._on_save_as(action, param)

    def _on_save_as(self, action, param):
        """Handle Save As action"""
        from .graph_io import get_default_save_directory

        dialog = Gtk.FileDialog()
        dialog.set_title("Save Graph")
        dialog.set_initial_name("graph.assets")

        # Set initial folder
        default_dir = get_default_save_directory()
        if default_dir.exists():
            folder = Gio.File.new_for_path(str(default_dir))
            dialog.set_initial_folder(folder)

        dialog.save(self, None, self._on_save_finish)

    def _on_save_finish(self, dialog, result):
        """Callback for save dialog"""
        try:
            file = dialog.save_finish(result)
            if file:
                filepath = file.get_path()

                # Ensure .assets extension
                if not filepath.endswith('.assets'):
                    filepath += '.assets'

                self._save_to_file(filepath)
        except Exception as e:
            if "dismissed" not in str(e).lower():
                print(f"❌ Error saving: {e}")

    def _save_to_file(self, filepath):
        """Save graph to file"""
        from .graph_io import GraphSerializer

        success = GraphSerializer.save_graph(
            self.canvas.nodes,
            self.canvas.connections,
            filepath
        )

        if success:
            self.current_file = filepath
            print(f"✓ Saved: {filepath}")

    def _on_result_toggle(self, button):
        """Toggle result area visibility"""
        if button.get_active():
            # Mostrar: restaurar altura
            new_position = self.get_height() - self.result_panel_height
            self.main_paned.set_position(max(100, new_position))
            self.result_panel_visible = True
        else:
            # Esconder: salvar altura atual e colapsar
            current_pos = self.main_paned.get_position()
            self.result_panel_height = self.get_height() - current_pos
            self.main_paned.set_position(self.get_height() - 1)
            self.result_panel_visible = False

    def _populate_node_list(self, nodes=None):
        """Populate node list in sidebar"""
        if self._is_populating:
            return

        self._is_populating = True

        try:
            from .node_library import get_all_categories, get_nodes_in_category, get_category_icon

            # Clear existing rows
            while True:
                row = self.node_list.get_row_at_index(0)
                if row is None:
                    break
                self.node_list.remove(row)

            if nodes is None:
                # Normal mode: show by categories
                for category in get_all_categories():
                    icon = get_category_icon(category)

                    # Category header
                    header_label = Gtk.Label()
                    header_label.set_markup(f"<b>{icon} {category}</b>")
                    header_label.set_xalign(0)
                    header_label.set_margin_top(12)
                    header_label.set_margin_bottom(3)
                    header_label.set_margin_start(6)
                    header_label.add_css_class("heading")
                    header_row = Gtk.ListBoxRow()
                    header_row.set_child(header_label)
                    header_row.set_selectable(False)
                    header_row.set_activatable(False)
                    self.node_list.append(header_row)

                    # Nodes in category
                    category_nodes = get_nodes_in_category(category)
                    for node_template in category_nodes:
                        self._create_node_row(node_template)
            else:
                # Search/filter mode: show specific nodes
                if not nodes:
                    no_results = Gtk.Label(label="No nodes found")
                    no_results.set_margin_top(20)
                    no_results.set_margin_bottom(20)
                    row = Gtk.ListBoxRow()
                    row.set_child(no_results)
                    row.set_selectable(False)
                    row.set_activatable(False)
                    self.node_list.append(row)
                else:
                    for node_template in nodes:
                        self._create_node_row(node_template, show_category=True)
        finally:
            self._is_populating = False

    def _create_node_row(self, node_template, show_category=False):
        """Create a row for a node template"""
        from .node_library import _get_library

        library = _get_library()

        # Horizontal box for button + favorite star
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)

        # Node button
        node_label = node_template["name"]
        if show_category and "_category" in node_template:
            node_label = f"[{node_template['_category']}] {node_label}"

        node_button = Gtk.Button(label=node_label)
        node_button.set_has_frame(False)
        node_button.set_halign(Gtk.Align.START)
        node_button.set_hexpand(True)

        # Tooltip with description and tags
        tooltip = node_template.get("description", "")
        if "tags" in node_template and node_template["tags"]:
            tooltip += f"\n\nTags: {', '.join(node_template['tags'])}"
        node_button.set_tooltip_text(tooltip)

        node_button.connect("clicked", self._on_node_template_clicked, node_template)
        hbox.append(node_button)

        # Favorite button
        is_fav = library.is_favorite(node_template["name"])
        fav_button = Gtk.Button()
        fav_button.set_icon_name("starred-symbolic" if is_fav else "non-starred-symbolic")
        fav_button.set_has_frame(False)
        fav_button.set_tooltip_text("Toggle favorite")
        fav_button.connect("clicked", self._on_toggle_favorite, node_template["name"])
        hbox.append(fav_button)

        row = Gtk.ListBoxRow()
        row.set_child(hbox)
        row.set_activatable(False)
        self.node_list.append(row)

    def _on_node_template_clicked(self, button, template):
        """When clicking a node template in the library"""
        from .node_library import create_node_from_template

        # Create node at center of visible canvas
        center_x = (400 - self.canvas.pan_offset_x) / self.canvas.zoom_level
        center_y = (300 - self.canvas.pan_offset_y) / self.canvas.zoom_level

        new_node = create_node_from_template(template, center_x, center_y)
        self.canvas.nodes.append(new_node)

        # Select the new node
        for node in self.canvas.nodes:
            node.set_selected(False)
        new_node.set_selected(True)
        self.canvas.focused_node_index = len(self.canvas.nodes) - 1

        # Update canvas size
        self.canvas._update_canvas_size()

        self.canvas.queue_draw()

        # Return focus to canvas for keyboard shortcuts
        self.canvas.grab_focus()

    def _on_search_changed(self, search_entry):
        """Search nodes as user types"""
        query = search_entry.get_text().strip()

        from .node_library import _get_library
        library = _get_library()

        if query:
            self.favorites_toggle.set_active(False)
            results = library.search_nodes(query)
            self._populate_node_list(results)
        else:
            self._populate_node_list()

    def _on_favorites_toggled(self, button):
        """Toggle favorites filter"""
        from .node_library import _get_library

        library = _get_library()

        if button.get_active():
            # Clear search
            self.search_entry.set_text("")
            favorites = library.get_favorites()
            self._populate_node_list(favorites)
        else:
            self._populate_node_list()

    def _on_toggle_favorite(self, button, node_name):
        """Toggle favorite status of a node"""
        from .node_library import _get_library

        library = _get_library()
        library.toggle_favorite(node_name)

        # Update UI
        if self.favorites_toggle.get_active():
            # If in favorites mode, update list
            favorites = library.get_favorites()
            self._populate_node_list(favorites)
        elif self.search_entry.get_text().strip():
            # If searching, redo search
            self._on_search_changed(self.search_entry)
        else:
            # Recreate normal list
            self._populate_node_list()

    def _on_import_library(self, button):
        """Import node library from file"""
        print("Import library clicked")
        # TODO: Implement import dialog

    def _on_export_library(self, button):
        """Export node library to file"""
        print("Export library clicked")
        # TODO: Implement export dialog

    def _on_run_graph(self, button):
        """When clicking Run button - execute graph in background"""
        import threading

        # Disable button during execution
        button.set_sensitive(False)

        def run_in_background():
            # Execute the graph
            success = self.canvas.execute_graph()

            # Re-enable button on main thread
            from gi.repository import GLib
            def finish():
                button.set_sensitive(True)
                if success:
                    print("=" * 60)
                    print("✅ EXECUTION COMPLETED SUCCESSFULLY")
                    print("=" * 60 + "\n")
                else:
                    print("=" * 60)
                    print("❌ EXECUTION FAILED")
                    print("=" * 60 + "\n")
                return False  # Remove from idle queue

            GLib.idle_add(finish)

        # Start thread
        thread = threading.Thread(target=run_in_background, daemon=True)
        thread.start()

    def _recreate_library_panel(self):
        """Recreate library panel (after adding new nodes)"""
        # Just repopulate the list
        self._populate_node_list()
        print("✓ Library updated")

    def _on_close_request(self, window):
        """Cleanup before closing"""
        try:
            # Close all matplotlib figures
            import matplotlib.pyplot as plt
            plt.close('all')
        except:
            pass

        # Allow window to close
        return False  # False = allow close, True = prevent close
