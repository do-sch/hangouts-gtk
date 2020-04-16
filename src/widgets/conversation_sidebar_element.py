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

from gi.repository import Gtk, GLib, Gdk
import cairo
import math
import datetime

from hangups.conversation_event import (ChatMessageEvent, OTREvent, RenameEvent, MembershipChangeEvent, HangoutEvent, GroupLinkSharingModificationEvent)
from hangups.parsers import WatermarkNotification


@Gtk.Template(resource_path="/com/dosch/HangoutsGTK/ui/conversation_sidebar_element.ui")
class ConversationSidebarElement(Gtk.Box):
    __gtype_name__ = "ConversationSidebarElement"

    photo_preview: Gtk.Image = Gtk.Template.Child()
    group_name: Gtk.Label = Gtk.Template.Child()
    text_boxes: Gtk.Box = Gtk.Template.Child()
    active_time: Gtk.Label = Gtk.Template.Child()
    last_message: Gtk.Label = Gtk.Template.Child()

    __conversation = NotImplemented

    def __init__(self, main_window, conversation, image_cache, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # set conversation
        self.__conversation = conversation

        # set message text funcion
        def set_message_string(event):
            if isinstance(event, ChatMessageEvent):
                sender_first_name = next(filter(lambda u: u.id_ == event.user_id, self.__conversation.users), "?").first_name
                last_message_str = sender_first_name + ": " + event.text
                self.last_message.set_text(last_message_str)
            elif isinstance(event, HangoutEvent):
                pass
            elif isinstance(event, MembershipChangeEvent):
                pass
            elif isinstance(event, RenameEvent):
                pass
            elif isinstance(event, GroupLinkSharingModificationEvent):
                pass
            elif isinstance(event, OTREvent):
                pass

        # TODO: add observer to change last_message and mark if unread messages are avaliable and remove observer
        # self.connect("destroy", )

        # set conversation name
        conversation_name = conversation.name
        if conversation_name is None:
            if len(conversation.users) > 2:
                conversation_name = ", ".join(
                    map(
                        lambda u: u.first_name,
                        filter(lambda u: not u.is_self, conversation.users)
                    )
                )
            else:
                conversation_name = ", ".join(
                    map(
                        lambda u: u.full_name,
                        filter(lambda u: not u.is_self, conversation.users)
                    )
                )
        self.group_name.set_text(conversation_name)

        # set last_event string
        if conversation.events:
            set_message_string(conversation.events[-1])

        # set time
        def set_time(ts: datetime.datetime):
            g_time = GLib.DateTime.new_local(ts.year, ts.month, ts.day, ts.hour, ts.minute, ts.second)
            time_str = None
            if ts.date() == ts.today().date():
                time_str = g_time.format("%X")
            else:
                time_str = g_time.format("%x")

            self.active_time.set_text(time_str)

        set_time(conversation.last_modified)

        user_count = len(conversation.users) - 1 if len(conversation.users) < 6 else 4
        images = list()

        # make round image
        def add_buf(pix):

            images.append(pix)

            if len(images) == user_count:

                ms = self.photo_preview.props.pixel_size  # min(chain(map(lambda pix: pix.props.width, images), map(lambda pix: pix.props.height, images)))

                half = ms * .5
                quarter = ms * .25
                width, height = pix.get_width(), pix.get_height()
                if width > height:
                    scale = height / width
                elif height > width:
                    scale = width / height
                else:
                    scale = 1

                if len(images) == 1:
                    arc = ((0, 0, half, half, half, scale), )
                elif len(images) == 2:
                    diagsq = ms * ms * 2
                    diag = math.sqrt(diagsq)
                    radius = diag / (2 + 2 * math.sqrt(2))
                    coord = ms - 2 * radius
                    arc = (
                        (0, 0, radius, radius, radius, scale),
                        (coord, coord, ms - radius, ms - radius, radius, scale)
                    )
                elif len(images) == 3:
                    offset = quarter * (1 - math.sqrt(3) / 2)
                    y_half = half - offset
                    threequaroff = quarter + y_half
                    quaroff = quarter + offset
                    arc = (
                        (quarter, offset, half, quaroff, quarter, scale),
                        (0, y_half, quarter, threequaroff, quarter, scale),
                        (half, y_half, half + quarter, threequaroff, quarter, scale)
                    )
                else:
                    threequar = half + quarter
                    arc = (
                        (0, 0, quarter, quarter, quarter, scale),
                        (half, 0, threequar, quarter, quarter, scale),
                        (0, half, quarter, threequar, quarter, scale),
                        (half, half, threequar, threequar, quarter, scale)
                    )

                def paint(wid, cr):
                    for num, image in enumerate(images):
                        surface = Gdk.cairo_surface_create_from_pixbuf(image, 0, None)
                        surface.set_device_scale(arc[num][5], arc[num][5])

                        cr.save()
                        cr.set_source_surface(surface, *(arc[num][0:2]))
                        cr.arc(*(arc[num][2:5]), 0, 2 * math.pi)
                        cr.clip()
                        cr.paint()
                        cr.restore()

                    return False

                self.photo_preview.set_from_surface(cairo.ImageSurface(cairo.FORMAT_ARGB32, ms, ms))
                self.photo_preview.connect("draw", paint)

        size = self.photo_preview.props.pixel_size
        width = (size, (size - .5 * math.sqrt(2) * size) * 2, size * .5, size * .5)

        # set image
        for user in list(filter(lambda u: not u.is_self, conversation.users))[:4]:
            image_cache.get_image(
                user.photo_url,
                add_buf,
                (width[user_count - 1], width[user_count - 1]),
                cache=True
            )

        # recognize new messages
        def on_event(event):
            set_message_string(event)
            context: Gtk.StyleContext = self.text_boxes.get_style_context()
            context.add_class("new_message")

        self.__on_event_callback = self.__conversation.connect_on_event(on_event)

        # get own user_id
        my_user = next(filter(lambda u: u.is_self, conversation.users))
        if my_user:
            self.__my_id = my_user.id_

        def read_status_changed(watermark_event):
            if watermark_event.user_id == self.__my_id and watermark_event.read_timestamp >= self.__conversation.events[-1].timestamp:
                context: Gtk.StyleContext = self.text_boxes.get_style_context()
                context.remove_class("new_message")

        if self.__my_id:
            wm = type("watermark", (), {})()
            wm.read_timestamp = self.__conversation.latest_read_timestamp
            wm.user_id = self.__my_id
            read_status_changed(wm)

        # add listener to change class, if self apart of conversation
        if self.__my_id:
            self.__calback_water = self.__conversation.connect_on_watermark_notification(read_status_changed)

        # call read_status_changed so that correct class is set
        for unread in self.__conversation.unread_events:
            if isinstance(unread, (ChatMessageEvent)):
                self.text_boxes.get_style_context().add_class("new_message")
                break

    def get_id(self):
        return str(self.__conversation.id_)
