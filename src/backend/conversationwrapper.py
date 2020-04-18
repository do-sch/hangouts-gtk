# conversationwrapper.py
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

import asyncio

from gi.repository.GLib import idle_add
from hangups.conversation import Conversation as HangupsConversation

# Thread communication wrapper for Conversation
class Conversation(HangupsConversation):

    hangups_conversation = NotImplemented
    queue = NotImplemented
    loop = NotImplemented

    def __init__(self, hangups_conversation, queue, loop):
        self.__dict__ = hangups_conversation.__dict__
        self.hangups_conversation = hangups_conversation
        self.queue = queue
        self.loop = loop

    def connect_on_event(self, callback):
        def _callback(conv_event):
            print("Conversation.connect_on_event_callback")
            idle_add(callback, conv_event)
        self.hangups_conversation.on_event.add_observer(_callback)
        return _callback

    def disconnect_on_event(self, callback):
        self.hangups_conversation.on_event.remove_observer(callback)

    def connect_on_typing(self, callback):
        def _callback(typing_message):
            idle_add(callback, typing_message)
        self.hangups_conversation.on_typing.add_observer(_callback)
        return _callback

    def disconnect_on_typing(self, callback):
        self.hangups_conversation.on_typing.remove_observer(callback)

    def connect_on_watermark_notification(self, callback):
        def _callback(watermark_notification):
            idle_add(callback, watermark_notification)
        self.hangups_conversation.on_watermark_notification.add_observer(_callback)
        return _callback

    def disconnect_on_watermark_notification(self, callback):
        self.hangups_conversation.on_watermark_notification.remove_observer(callback)

    def get_id(self):
        return self.hangups_conversation.id_

    def get_users(self):
        return self.hangups_conversation.users

    def get_name(self):
        return self.hangups_conversation.name

    def get_last_modified(self):
        return self.hangups_conversation.last_modified

    def get_latest_read_timestamp(self):
        return self.hangups_conversation.latest_read_timestamp

    def get_stored_events(self):
        return self.hangups_conversation.events

    def get_watermarks(self):
        return self.hangups_conversation.watermarks

    def get_unread_events(self):
        return self.hangups_conversation.unread_events

    def get_is_archived(self):
        return self.hangups_conversation.is_archived

    def get_is_quiet(self):
        return self.hangups_conversation.is_quiet

    def get_is_off_the_record(self):
        return self.hangups_conversation.is_off_the_record

    def get_user(self, user_id):
        return self.hangups_conversation.get_user(user_id)

    def send_message(self, segments, image_file=None):
        self.loop.call_soon_threadsafe(lambda: self.queue.put_nowait(self.hangups_conversation.send_message(segments, image_file)))

    def leave(self):
        self.loop.call_soon_threadsafe(lambda: self.queue.put_nowait(self.hangups_conversation.leave()))

    def rename(self, name):
        self.loop.call_soon_threadsafe(lambda: self.queue.put_nowait(self.hangups_conversation.rename(name)))

    def set_notification_level(self, level):
        self.loop.call_soon_threadsafe(lambda: self.queue.put_nowait(self.hangups_conversation.set_notification_level(level)))

    def set_typing(self, typing=1):
        self.loop.call_soon_threadsafe(lambda: self.queue.put_nowait(self.hangups_conversation.set_typing(typing)))

    def update_read_timestamp(self, read_timestamp=None):
        self.loop.call_soon_threadsafe(lambda: self.queue.put_nowait(self.hangups_conversation.update_read_timestamp(read_timestamp)))

    def get_events(self, callback, event_id=None, max_events=50):
        async def async_get_events(cb, event_id, max_events):
            events = await self.hangups_conversation.get_events(event_id, max_events)

            idle_add(callback, events)

        self.loop.call_soon_threadsafe(lambda: self.queue.put_nowait(async_get_events(callback, event_id, max_events)))

    def next_event(self, event_id, prev=False):
        return self.hangups_conversation.next_event(event_id, prev)

    def get_event(self, event_id):
        return self.hangups_conversation.get_event(event_id)
