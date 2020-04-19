# Copyright 2020 The GNOME Music developers
#
# Copyright 2020 Dominik Schütz <do.sch.dev@gmail.com>
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
#
# SPDX-License-Identifier: GPL-3.0-or-later

import inspect
import os

from gi.repository import GLib, GObject


class HangoutsLogger(GObject.GObject):
    """GLib logging wrapper
    A tiny wrapper aroung the default GLib logger.
    * Message is for user facing warnings, which ideally should be in
      the application.
    * Warning is for logging non-fatal errors during execution.
    * Debug is for developer use as a way to get more runtime info.
    """

    _DOMAIN = "com.dosch.HangoutsGTK"

    def _log(self, message, level):
        stack = inspect.stack()

        filename = os.path.basename(stack[2][1])
        line = stack[2][2]
        function = stack[2][3]

        if level in [GLib.LogLevelFlags.LEVEL_DEBUG,
                     GLib.LogLevelFlags.LEVEL_WARNING]:
            message = "({}, {}, {}) {}".format(
                filename, function, line, message)

        variant_message = GLib.Variant("s", message)
        variant_file = GLib.Variant("s", filename)
        variant_line = GLib.Variant("i", line)
        variant_func = GLib.Variant("s", function)

        variant_dict = GLib.Variant("a{sv}", {
            "MESSAGE": variant_message,
            "CODE_FILE": variant_file,
            "CODE_LINE": variant_line,
            "CODE_FUNC": variant_func
        })

        GLib.log_variant(self._DOMAIN, level, variant_dict)

    def message(self, message):
        """The default user facing message
        Wraps g_message.
        :param string message: Message
        """
        self._log(message, GLib.LogLevelFlags.LEVEL_MESSAGE)

    def warning(self, message):
        """Warning message
        Wraps g_warning.
        :param string message: Warning message
        """
        self._log(message, GLib.LogLevelFlags.LEVEL_WARNING)

    def info(self, message):
        """Informational message
        Wraps g_info.
        :param string message: Informational message
        """
        self._log(message, GLib.LogLevelFlags.LEVEL_INFO)

    def debug(self, message):
        """Debug message
        Wraps g_debug.
        :param string message: Debug message
        """
        self._log(message, GLib.LogLevelFlags.LEVEL_DEBUG)
