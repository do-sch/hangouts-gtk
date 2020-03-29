# This file is part of Hangouts GTK
# Copyright © 2019-2020 Dominik Schütz <do.sch.dev@gmail.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk, Gdk
import cairo
import math


@Gtk.Template(resource_path="/com/dosch/HangoutsGTK/ui/conversation_edit_user_element.ui")
class ConversationEditUserElement(Gtk.Box):

    __gtype_name__ = "ConversationEditUserElement"

    preview_image: Gtk.Image = Gtk.Template.Child()
    user_name: Gtk.Label = Gtk.Template.Child()
    remove_from_group: Gtk.Button = Gtk.Template.Child()
    block: Gtk.Button = Gtk.Template.Child()

    def __init__(self, user, image_cache, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # set text
        self.user_name.set_text(user.full_name)

        # set icon
        def got_item(image):
            width, height = image.get_width(), image.get_height()
            scale = width / height if width > height else height / width
            radius_2 = height if width > height else width
            radius = radius_2 / 2

            icon_width = Gtk.IconSize.lookup(Gtk.IconSize.DND)[1]
            scale *= radius_2 / icon_width

            offset = (radius_2 - icon_width) / 2

            def paint(wid, cr):
                surface = Gdk.cairo_surface_create_from_pixbuf(image, 0, None)
                surface.set_device_scale(scale, scale)

                cr.set_source_surface(surface, offset, offset)
                cr.arc(radius, radius, icon_width / 2, 0, 2 * math.pi)
                cr.clip()
                cr.paint()

                return False

            self.preview_image.set_from_surface(cairo.ImageSurface(cairo.FORMAT_ARGB32, int(radius_2), int(radius_2)))
            self.preview_image.connect("draw", paint)

        image_cache.get_image(
            user.photo_url,
            got_item
        )
