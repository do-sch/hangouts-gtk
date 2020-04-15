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

import hangups
import cairo
import math
import os

from gi.repository import Gtk, GLib, Gdk, Pango
from ..backend.image_cache import PROFILE_PHOTO_SMALL, SENT_IMAGE_PREVIEW


def _convert_chat_message_segments_2_markup(chat_message_segments):
    markup = ""
    for segment in chat_message_segments:
        seg_text: str = segment.text
        seg_text = GLib.markup_escape_text(seg_text)
        # if segment.type_ == hangouts_pb2.SEGMENT_TYPE_TEXT:
        if segment.is_bold:
            seg_text = "<b>{0}</b>".format(seg_text)
        if segment.is_italic:
            seg_text = "<i>{0}</i>".format(seg_text)
        if segment.is_strikethrough:
            seg_text = "<s>{0}</s>".format(seg_text)
        if segment.is_underline:
            seg_text = "<u>{0}</u>".format(seg_text)
        if segment.link_target:
            seg_text = "<a href=\"{0}\">{1}</a>".format(
                GLib.markup_escape_text(segment.link_target),
                GLib.markup_escape_text(seg_text)
            )

        markup += seg_text

    return markup


def _time_2_local(ts):
    g_time = GLib.DateTime.new_local(ts.year, ts.month, ts.day, ts.hour, ts.minute, ts.second)
    time_str = None
    # if ts.date() == ts.today().date():
    #     time_str = g_time.format("%X")
    # else:
    time_str = g_time.format("%x, %X")

    return time_str


def save_image(parent_window, image_cache, url):
    dialog = Gtk.FileChooserDialog(
        "Save File",
        parent_window,
        Gtk.FileChooserAction.SAVE,
        (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
    )
    dialog.set_current_name(os.path.basename(url))

    res = dialog.run()
    if res == Gtk.ResponseType.OK:
        filename = dialog.get_filename()
        type = os.path.splitext(filename)[1][1:]
        if type == "jpg":
            type = "jpeg"
        if type not in ("jpeg", "png", "tiff", "ico", "bmp"):
            type = "png"

        def save(pixbuf):
            print("saving...")
            pixbuf.savev(filename, type, [], [])
        image_cache.get_image(url, save, None)
    dialog.destroy()


def build_image_right_click(widget: Gtk.Widget, image_cache, url):
    def right_click(widget, event: Gdk.EventButton):
        if event.button == 1:
            save_image(widget.get_toplevel(), image_cache, url)

    widget.connect("button-press-event", right_click)


@Gtk.Template(resource_path="/com/dosch/HangoutsGTK/ui/chat_message_own.ui")
class ChatMessageOwn(Gtk.Box):

    __gtype_name__ = "ChatMessageOwn"

    messages: Gtk.ListBox = Gtk.Template.Child()
    time: Gtk.Label = Gtk.Template.Child()

    def __init__(self, chatmessageevent, image_cache, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.user_id = chatmessageevent.user_id
        self.append(chatmessageevent, image_cache)
        self.timestamp = chatmessageevent.timestamp

        # message time
        time_str = _time_2_local(chatmessageevent.timestamp)
        self.time.set_text(time_str)

        self.show()

    def append(self, chatmessage_event, image_cache):
        # add attached images
        for att in chatmessage_event.attachments:
            image = Gtk.Image()
            self.messages.add(image)

            build_image_right_click(self, image_cache, att)

            image.show()
            image_cache.get_image(
                att,
                image.set_from_pixbuf,
                SENT_IMAGE_PREVIEW
            )

        # message text
        markup = _convert_chat_message_segments_2_markup(chatmessage_event.segments)
        if markup:
            label = Gtk.Label()
            label.set_selectable(True)
            label.set_markup(markup)
            label.set_halign(Gtk.Align.END)
            label.set_line_wrap(True)
            label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            label.set_max_width_chars(30)
            label.show()
            self.messages.add(label)

    def prepend(self, chatmessage_event, image_cache):
        # message text
        markup = _convert_chat_message_segments_2_markup(chatmessage_event.segments)
        if markup:
            label = Gtk.Label()
            label.set_selectable(True)
            label.set_markup(markup)
            label.set_halign(Gtk.Align.END)
            label.set_line_wrap(True)
            label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            label.set_max_width_chars(30)
            label.show()
            self.messages.prepend(label)

        # add attached images
        for att in reversed(chatmessage_event.attachments):
            image = Gtk.Image()
            self.messages.prepend(image)

            build_image_right_click(self, image_cache, att)

            image.show()
            image_cache.get_image(
                att,
                image.set_from_pixbuf,
                SENT_IMAGE_PREVIEW
            )


@Gtk.Template(resource_path="/com/dosch/HangoutsGTK/ui/chat_message_foreign.ui")
class ChatMessageForeign(Gtk.Box):

    __gtype_name__ = "ChatMessageForeign"

    messages: Gtk.ListBox = Gtk.Template.Child()
    time: Gtk.Label = Gtk.Template.Child()
    profile_photo: Gtk.DrawingArea = Gtk.Template.Child()
    name: Gtk.Label = Gtk.Template.Child()

    def __init__(self, chatmessageevent, image_cache, user_dict, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.user_id = chatmessageevent.user_id
        user = user_dict.get(chatmessageevent.user_id, None)

        self.append(chatmessageevent, image_cache)

        self.set_homogeneous(False)  # Do not know, why this one defaults to True

        # message name
        self.name.set_text(user.first_name if user is not None else "Unknown")

        # message time
        self.timestamp = chatmessageevent.timestamp
        time_str = _time_2_local(chatmessageevent.timestamp)
        self.time.set_text(time_str)

        # make round image
        def round(pix):

            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.profile_photo.props.pixel_size, self.profile_photo.props.pixel_size)
            draw_surface = Gdk.cairo_surface_create_from_pixbuf(pix, 0, self.profile_photo.props.window)

            def paint(wid, cr):
                cr.set_source_surface(draw_surface, 0, 0)
                smaller_one = pix.props.width if pix.props.width < pix.props.height else pix.props.height
                cr.arc(pix.props.width * .5, pix.props.height * .5, smaller_one * .5, 0, 2 * math.pi)
                cr.clip()
                cr.paint()

                return False

            self.profile_photo.connect("draw", paint)
            self.profile_photo.set_from_surface(surface)

        # message profile photo
        if user is not None:
            image_cache.get_image(
                user.photo_url,
                round,
                size=PROFILE_PHOTO_SMALL,
                cache=True
            )

        self.show()

    def append(self, chatmessage_event, image_cache):
        # add attached images
        for att in chatmessage_event.attachments:
            image = Gtk.Image()
            self.messages.add(image)

            build_image_right_click(self, image_cache, att)

            image.show()
            image_cache.get_image(
                att,
                image.set_from_pixbuf,
                SENT_IMAGE_PREVIEW
            )

        # message text
        markup = _convert_chat_message_segments_2_markup(chatmessage_event.segments)
        if markup:
            label = Gtk.Label()
            label.set_selectable(True)
            label.set_markup(markup)
            label.set_halign(Gtk.Align.START)
            label.set_line_wrap(True)
            label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            label.set_max_width_chars(30)
            label.show()
            self.messages.add(label)

    def prepend(self, chatmessage_event, image_cache):
        # message text
        markup = _convert_chat_message_segments_2_markup(chatmessage_event.segments)
        if markup:
            label = Gtk.Label()
            label.set_selectable(True)
            label.set_markup(markup)
            label.set_halign(Gtk.Align.START)
            label.set_line_wrap(True)
            label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            label.set_max_width_chars(30)
            label.show()
            self.messages.prepend(label)

        # add attached images
        for att in reversed(chatmessage_event.attachments):
            image = Gtk.Image()
            self.messages.prepend(image)

            build_image_right_click(self, image_cache, att)

            image.show()
            image_cache.get_image(
                att,
                image.set_from_pixbuf,
                SENT_IMAGE_PREVIEW
            )


@Gtk.Template(resource_path="/com/dosch/HangoutsGTK/ui/chat_info.ui")
class ChatInfo(Gtk.Box):

    __gtype_name__ = "ChatInfo"

    image: Gtk.Image = Gtk.Template.Child()
    text: Gtk.Image = Gtk.Template.Child()
    time: Gtk.Image = Gtk.Template.Child()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def set_time(self, event):
        time = _time_2_local(event.timestamp)
        self.time.set_text(time)

    def set_hangout_event(self, hangout_event, user_dict):
        # call-start-symbolic call-missed-symbolic call-stop-symbolic folder-video-symbolic
        self.image.set_from_icon_name("folder-video-symbolic", self.image.props.icon_size)
        self.set_time(hangout_event)
        text = "UNDEFINED"
        user = user_dict.get(hangout_event.user_id, None)
        user_name = user.first_name if user is not None else "Unknown"
        if hangout_event.event_type == hangups.HANGOUT_EVENT_TYPE_START:
            text = "{0} started a call".format(user_name)
        elif hangout_event.event_type == hangups.HANGOUT_EVENT_TYPE_END:
            text = "{0} has ended the call".format(user_name)
            self.image.set_from_icon_name("call-missed-symbolic", self.image.props.icon_size)
        elif hangout_event.event_type == hangups.HANGOUT_EVENT_TYPE_JOIN:
            text = "{0} has joined the call".format(user_name)
        elif hangout_event.event_type == hangups.HANGOUT_EVENT_TYPE_LEAVE:
            text = "{0} has left the call".format(user_name)
        elif hangout_event.event_type == hangups.HANGOUT_EVENT_TYPE_COMING_SOON:
            text = "a conference is coming soon"
        elif hangout_event.event_type == hangups.HANGOUT_EVENT_TYPE_ONGOING:
            text = "a call is ongoing"
        self.text.set_text(text)

        self.show_all()

    def set_membership_change_event(self, membership_change_event, user_dict):
        text = "UNDEFINED"
        user = user_dict.get(membership_change_event.user_id, None)
        user_name = user.first_name if user is not None else "Unknown"
        if membership_change_event.type_ is hangups.MEMBERSHIP_CHANGE_TYPE_JOIN:
            self.image.set_from_stock(Gtk.STOCK_QUIT, self.image.props.icon_size)

            text = "{0} joined the conversation".format(user_name)
        else:
            self.image.set_from_icon_name("user-avaliable-symbolic", self.image.props.icon_size)
            text = "{0} left the conversation".format(user_name)
        self.text.set_text(text)
        self.set_time(membership_change_event)
        self.show_all()


@Gtk.Template(resource_path="/com/dosch/HangoutsGTK/ui/chat_info_timeless.ui")
class ChatInfoTimeless(Gtk.Box):

    __gtype_name__ = "ChatInfoTimeless"

    image: Gtk.Image = Gtk.Template.Child()
    text: Gtk.Image = Gtk.Template.Child()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.image.set_from_stock(Gtk.STOCK_EDIT, self.image.props.icon_size)
        self.show_all()

    def set_rename_event(self, rename_event, user_dict):
        self.image.set_from_stock(Gtk.STOCK_EDIT, self.image.props.icon_size)
        user = user_dict.get(rename_event.user_id, None)
        user_name = user.first_name if user is not None else "Unknown"
        text = "{0} has renamed the Conversation in {1}".format(
            user_name,
            rename_event.new_name
        )
        self.text.set_text(text)
        self.show_all()

    def set_otr_event(self, otr_event):
        self.image.set_from_icon_name("send-to-symbolic", self.image.props.icon_size)
        text = "UNDEFINED"
        if otr_event.event_type == hangups.OFF_THE_RECORD_STATUS_OFF_THE_RECORD:
            text = "the conversation has been archived"
        elif otr_event.event_type == hangups.OFF_THE_RECORD_STATUS_ON_THE_RECORD:
            text = "the conversation has been dearchived"
        self.text.set_text(text)
        self.show_all()

    def set_group_sharing_event(self, group_sharing_event, user_dict):
        self.image.set_from_icon_name("send-to-symbolic", self.image.props.icon_size)
        text = "UNDEFINED"
        user = user_dict.get(group_sharing_event.user_id, None)
        user_name = user.first_name if user is not None else "Unknown"
        if group_sharing_event.new_status is hangups.GROUP_LINK_SHARING_STATUS_ON:
            text = "{0} has enabled group sharing".format(user_name)
        else:
            text = "{0} has disabled group sharing".format(user_name)
            self.text.set_text(text)
        self.show_all()
