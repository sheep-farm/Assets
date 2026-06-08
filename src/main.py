# main.py
#
# Copyright 2025 Flavio de Vasconcellos Corrêa
#
# SPDX-License-Identifier: MIT

# Configurar matplotlib para backend não-interativo ANTES de qualquer outro import
# import matplotlib
# matplotlib.use('Agg')

import sys
import os
import gi
# import numpy

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gio, Adw
from pathlib import Path

# Carregar GResource para desenvolvimento (meson faz isso na instalação)
gresource_path = Path(__file__).parent / 'assets.gresource'
if gresource_path.exists():
    resource = Gio.Resource.load(str(gresource_path))
    Gio.resources_register(resource)
else:
    # Workaround: Carregar .ui files manualmente para desenvolvimento
    print("⚠ GResource not found - using direct .ui file loading for development")
    print("  Run 'meson compile' for production build")

from .window import AssetsWindow
from .preferences_dialog import PreferencesDialog


class AssetsApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(application_id='com.github.sheep.farm.assets',
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
                         resource_base_path='/com/github/sheep/farm/assets')
        self.create_action('quit', lambda *_: self.quit(), ['<control>q'])
        self.create_action('about', self.on_about_action)
        self.create_action('preferences', self.on_preferences_action)

    def do_activate(self):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        win = self.props.active_window
        if not win:
            win = AssetsWindow(application=self)
        win.present()

    def on_about_action(self, *args):
        """Callback for the app.about action."""
        about = Adw.AboutDialog(application_name='assets',
                                application_icon='com.github.sheep.farm.assets',
                                developer_name='Flavio de Vasconcellos Corrêa',
                                version='0.1.0',
                                developers=['Flavio de Vasconcellos Corrêa'],
                                copyright='© 2025 Flavio de Vasconcellos Corrêa')
        # Translators: Replace "translator-credits" with your name/username, and optionally an email or URL.
        about.set_translator_credits(_('translator-credits'))
        about.present(self.props.active_window)

    def on_preferences_action(self, widget, _):
        """Callback for the app.preferences action."""
        dialog = PreferencesDialog(self.props.active_window)
        dialog.present()

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


def main(version):
    """The application's entry point."""
    app = AssetsApplication()
    return app.run(sys.argv)
