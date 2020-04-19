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

import re
import os
import giofile

from gi.repository import Gtk, Gdk, Pango, Gio, GLib

from ..widgets.message_views import ChatMessageOwn, ChatMessageForeign, ChatInfo, ChatInfoTimeless

from hangups.conversation_event import (ChatMessageEvent, OTREvent, RenameEvent, MembershipChangeEvent, HangoutEvent, GroupLinkSharingModificationEvent)
from hangups import ChatMessageSegment
from hangups import hangouts_pb2

url_regex = re.compile(r"(?:http(s)?:\/\/)?[\w.-]+(?:\.[\w\.-]+)+[\w\-\._~:/?#[\]@!\$&'\(\)\*\+,;=.]+")


@Gtk.Template(resource_path="/com/dosch/HangoutsGTK/ui/message_box.ui")
class MessageBox(Gtk.Box):

    __gtype_name__ = "MessageBox"

    overlay: Gtk.Overlay = Gtk.Template.Child()
    messages: Gtk.ListBox = Gtk.Template.Child()
    delete_attachment: Gtk.Button = Gtk.Template.Child()
    photo_button: Gtk.Button = Gtk.Template.Child()
    image_name: Gtk.Label = Gtk.Template.Child()
    scrolled_window: Gtk.ScrolledWindow = Gtk.Template.Child()
    text_input: Gtk.TextView = Gtk.Template.Child()
    message_sending_spinner: Gtk.Spinner = Gtk.Template.Child()
    to_bottom_button: Gtk.Button = Gtk.Template.Child()


    def __init__(self, conversation, image_cache, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__conversation = conversation
        self.__own_id = next(filter(lambda u: u.is_self, conversation.users), None).id_
        self.__image_cache = image_cache
        self.__last_event = self.__first_event = None
        self.__pending_messages = 0
        self.__scroll_down = True
        self.__send_file = None

        self.connect("destroy", self.destroy)
        self.connect("map", self.map)

        # cache all users of conversation
        self.__user_dict = {}
        for user in conversation.users:
            self.__user_dict[user.id_] = user

        # insert text listener
        buffer: Gtk.TextTag = self.text_input.props.buffer
        bold = buffer.create_tag("b", weight=Pango.Weight.BOLD)
        italic = buffer.create_tag("i", style=Pango.Style.ITALIC)
        underline = buffer.create_tag("u", underline=Pango.Underline.SINGLE)
        strike = buffer.create_tag("s", strikethrough=True)

        def key_press_event(text_view: Gtk.TextView, event: Gdk.EventKey):

            def segments_from_buffer(buffer):

                def get_segments(current_text, current_tags):

                    def get_text_segment(text, tags):

                        return ChatMessageSegment(
                            text,
                            hangouts_pb2.SEGMENT_TYPE_TEXT,
                            bold in tags,
                            italic in tags,
                            strike in tags,
                            underline in tags
                        )

                    segments = []

                    begin_index = 0
                    links = url_regex.finditer(current_text)
                    for match in links:
                        begin, end = match.span()

                        not_link = current_text[begin_index:begin]
                        if not_link:
                            segments.append(get_text_segment(not_link, current_tags))

                        link = current_text[begin:end]
                        segments.append(
                            ChatMessageSegment(
                                link,
                                hangouts_pb2.SEGMENT_TYPE_LINK,
                                link_target=link
                            )
                        )

                        begin_index = end

                    segments.append(get_text_segment(current_text[begin_index:], current_tags))

                    return segments

                iter: Gtk.TextIter = buffer.get_start_iter()
                current_text = ""
                segments = []
                current_tags = []

                while True:
                    enabled_tags = iter.get_toggled_tags(True)
                    disabled_tags = iter.get_toggled_tags(False)
                    char = iter.get_char()

                    if not char:
                        if current_text:
                            segments.extend(get_segments(current_text, current_tags))
                        return segments

                    if char == "\n":
                        segments.append(ChatMessageSegment(hangouts_pb2.SEGMENT_TYPE_LINE_BREAK))

                    current_text += char

                    if enabled_tags or disabled_tags:
                        segments.extend(get_segments(current_text, current_tags))
                        current_tags.extend(enabled_tags)
                        for disabled in disabled_tags:
                            current_tags.remove(disabled)
                        current_text = ""

                    if not iter.forward_char():
                        if current_text:
                            segments.extend(get_segments(current_text, current_tags))
                        return segments

            buffer: Gtk.TextBuffer = text_view.props.buffer
            send_keys = [Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_Send]
            if event.keyval in send_keys:
                if event.state & Gdk.ModifierType.SHIFT_MASK:
                    # do not send if Shift modifier key was pressed
                    buffer.props.text += "\n"
                else:
                    segments = segments_from_buffer(buffer)
                    buffer.props.text = ""

                    file = None
                    if self.__send_file:
                        # TODO: close file when upload is finished. As for now file should be closed, when it is deallocated
                        file = giofile.open(self.__send_file, 'rb')
                        # change view
                        self.photo_button.set_visible(True)
                        self.delete_attachment.set_visible(False)
                    self.__conversation.send_message(segments, image_file=file)
                    self.message_sending_spinner.set_visible(True)
                    self.__pending_messages += 1

                    del file
                    self.__send_file = None

                return True

            elif event.state & Gdk.ModifierType.CONTROL_MASK:

                if event.keyval == Gdk.KEY_B or event.keyval == Gdk.KEY_b:
                    tag = bold
                elif event.keyval == Gdk.KEY_U or event.keyval == Gdk.KEY_u:
                    tag = underline
                elif event.keyval == Gdk.KEY_I or event.keyval == Gdk.KEY_i:
                    tag = italic
                elif event.keyval == Gdk.KEY_S or event.keyval == Gdk.KEY_s:
                    tag = strike
                else:
                    return False

                if buffer.get_has_selection():
                    start, end = buffer.get_selection_bounds()
                    if start.has_tag(tag):
                        buffer.remove_tag(tag, start, end)
                    else:
                        buffer.apply_tag(tag, start, end)
                else:
                    # TODO: save enabled tags in list and enable that tags for every input char, use insert-text signal
                    mark = buffer.get_insert()
                    start = buffer.get_iter_at_mark(mark)
                    end = buffer.get_iter_at_mark(mark)
                    end.forward_char()
                    if start.has_tag(tag):
                        buffer.remove_tag(tag, start, end)
                    else:
                        buffer.apply_tag(tag, start, end)
                return True
            return False

        self.text_input.connect("key-press-event", key_press_event)

        # add conversation events now
        self.__add_events(self.__conversation.events, append_bottom=True)

        # add conversation events later
        self.__conversation.get_events(self.__add_events, conversation.events[0].id_)

        # add listeners for incoming messages
        def incoming_message(event):
            self.__add_events([event], True)
            self.__pending_messages -= 1
            if self.__pending_messages <= 0:
                self.__pending_messages = 0
                self.message_sending_spinner.set_visible(False)
        self.__add_event_callback = self.__conversation.connect_on_event(incoming_message)

        # handle scroll down
        def size_changed(messages, allocation):
            if self.__scroll_down:
                adj: Gtk.Adjustment = self.scrolled_window.get_vadjustment()
                adj.set_value(adj.get_upper() - adj.get_page_size())

        self.messages.connect("size-allocate", size_changed)

        # handle animated scroll down
        def animated_scroll_down(button):
            # inspired by Julian Sparbers animated scroll in fractal
            # GTK3 license
            adj: Gtk.Adjustment = self.scrolled_window.get_vadjustment()
            clock = self.scrolled_window.get_frame_clock()
            start = adj.get_value()
            end = adj.get_upper() - adj.get_page_size()
            start_time = clock.get_frame_time()
            end_time = start_time + 180000

            def tick_callback(scrolled_window, clock):
                time = clock.get_frame_time()
                if time < end_time and adj.get_value() != end:
                    progress = (time - start_time) / (end_time - start_time)
                    adj.set_value(start + progress * progress * progress * (end - start))
                    return True
                else:
                    adj.set_value(end)
                    return False

            self.scrolled_window.add_tick_callback(tick_callback)

        self.to_bottom_button.connect("clicked", animated_scroll_down)

        # listener to append image
        def on_image_button_clicked(button):
            dialog: Gtk.FileChooserDialog = Gtk.FileChooserDialog(
                title="Choose Image",
                action=Gtk.FileChooserAction.OPEN,
                buttons=(
                    Gtk.STOCK_CANCEL,
                    Gtk.ResponseType.CANCEL,
                    Gtk.STOCK_OPEN,
                    Gtk.ResponseType.OK
                )
            )
            file_filter = Gtk.FileFilter()
            file_filter.add_mime_type("image/jpeg")
            file_filter.add_mime_type("image/gif")
            file_filter.add_mime_type("image/png")
            dialog.set_filter(file_filter)

            res = dialog.run()
            if res == Gtk.ResponseType.OK:
                self.__send_file = dialog.get_file()
                self.image_name.set_text(os.path.basename(dialog.get_filename()))
                self.photo_button.set_visible(False)
                self.delete_attachment.set_visible(True)

            dialog.destroy()

        self.photo_button.connect("clicked", on_image_button_clicked)

        # add listener to remove attachment
        def on_delete_button_clicked(button):
            self.delete_attachment.set_visible(False)
            self.photo_button.set_visible(True)

        self.delete_attachment.connect("clicked", on_delete_button_clicked)

        # add listener to scrollbar change
        def on_scrollbar_value_changed(adjustment: Gtk.Adjustment):
            # when scrolled to bottom
            if adjustment.get_value() == adjustment.get_upper() - adjustment.get_page_size():
                self.to_bottom_button.set_state_flags(Gtk.StateFlags.INSENSITIVE, False)
                self.__scroll_down = True
            else:
                self.to_bottom_button.unset_state_flags(Gtk.StateFlags.INSENSITIVE)
                self.__scroll_down = False

        self.scrolled_window.get_vadjustment().connect("value-changed", on_scrollbar_value_changed)


    def __add_events(self, event_list, append_bottom=False):

        if append_bottom:
            it = event_list
            recentevent = self.__last_event
            add_func = self.messages.add
        else:
            it = reversed(event_list)
            recentevent = self.__first_event
            add_func = self.messages.prepend

        for event in it:

            widget = None

            if isinstance(event, ChatMessageEvent):
                if isinstance(recentevent, (ChatMessageOwn, ChatMessageForeign)) and event.user_id == recentevent.user_id and abs(event.timestamp - recentevent.timestamp).total_seconds() < 20 * 60:  # create new bubble after 20 minutes
                    if append_bottom:
                        recentevent.append(event, self.__image_cache)
                    else:
                        recentevent.prepend(event, self.__image_cache)
                    continue
                elif event.user_id == self.__own_id:
                    widget = ChatMessageOwn(event, self.__image_cache)
                else:
                    widget = ChatMessageForeign(event, self.__image_cache, self.__user_dict)

            elif isinstance(event, HangoutEvent):
                widget = ChatInfo()
                widget.set_hangout_event(event, self.__user_dict)
            elif isinstance(event, MembershipChangeEvent):
                widget = ChatInfo()
                widget.set_membership_change_event(event, self.__user_dict)
            elif isinstance(event, RenameEvent):
                widget = ChatInfoTimeless()
                widget.set_rename_event(event, self.__user_dict)
            elif isinstance(event, GroupLinkSharingModificationEvent):
                widget = ChatInfoTimeless()
                widget.set_group_sharing_event(event, self.__user_dict)
            elif isinstance(event, OTREvent):
                widget = ChatInfoTimeless()
                widget.set_group_sharing_eventChatOtrInfo(event)
            else:
                widget = Gtk.Label("?")

            if append_bottom:
                self.__last_event = widget
            else:
                self.__first_event = widget

            if not (self.__last_event and self.__first_event):
                self.__last_event = self.__first_event = widget

            add_func(widget)

            recentevent = widget


    def map(self, widget):
        self.__conversation.update_read_timestamp()
        Gio.Application.get_default().withdraw_notification(self.__conversation.id_)

    def destroy(self, widget):
        self.__conversation.disconnect_on_event(self.__add_event_callback)
