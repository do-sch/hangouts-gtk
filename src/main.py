# main.py
#
# Copyright 2019-2020 Dominik Schütz <do.sch.dev@gmail.com>
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import gi

gi.require_version("Gio", "2.0")
gi.require_version('Gtk', '3.0')
gi.require_version('Handy', '0.0')
gi.require_version('WebKit2', '4.0')
gi.require_version('Pango', '1.0')

from gi.repository import Gtk, Gio, Gdk, GLib

from .main_window import MainWindow


class Application(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='com.dosch.HangoutsGTK',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

        # set GLib stuff
        GLib.set_application_name("HangoutsGTK")
        GLib.set_prgname(self.get_application_id())

        # set style
        provider = Gtk.CssProvider()
        provider.load_from_resource("/com/dosch/HangoutsGTK/ui/style.css")
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = MainWindow(application=self)
            win.set_default_icon_name(self.props.application_id)
        win.present()


def main(version):
    app = Application()
    return app.run(sys.argv)
