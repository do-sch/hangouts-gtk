# This file is part of Hangouts GTK
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
from hangups.conversation import ConversationList as HangupsConversationList

from ..backend.conversationwrapper import Conversation


# Thread communication wrapper for ConversationList
class ConversationList(HangupsConversationList):

    hangups_conversation_list = NotImplemented
    loop = NotImplemented
    queue = NotImplemented

    __conversations_cache = dict()

    def __init__(self, hangups_conversation_list, queue):
        self.hangups_conversation_list = hangups_conversation_list
        self.queue = queue
        self.loop = asyncio.get_running_loop()

    def connect_on_event(self, callback):
        def _callback(conv_event):
            idle_add(callback, conv_event)
        self.hangups_conversation_list.on_connect.add_observer(_callback)
        return _callback

    def disconnect_on_event(self, callback):
        self.hangups_conversation_list.on_connect.remove_observer(callback)

    def connect_on_typing(self, callback):
        def _callback(typing_message):
            idle_add(callback, typing_message)
        self.hangups_conversation_list.on_typing.add_observer(_callback)
        return _callback

    def disconnect_on_typing(self, callback):
        self.hangups_conversation_list.on_typing.remove_observer(callback)

    def connect_on_watermark_notification(self, callback):
        def _callback(watermark_notification):
            idle_add(callback, watermark_notification)
        self.hangups_conversation_list.on_watermark_notification.add_observer(_callback)
        return _callback

    def disconnect_on_watermark_notification(self, callback):
        self.hangups_conversation_list.on_watermark_notification.remove_observer(callback)

    def get_all(self, include_archived=False):
        conversations = self.hangups_conversation_list.get_all(include_archived)
        wrapper_list = list()
        for conv in conversations:
            if not conv.id_ in self.__conversations_cache:
                wrapper_conv = Conversation(
                    conv,
                    self.queue,
                    self.loop
                )
                self.__conversations_cache[conv.id_] = wrapper_conv
            else:
                wrapper_conv = self.__conversations_cache[conv.id_]
            wrapper_list.append(wrapper_conv)
        return wrapper_list

    def get(self, conv_id):
        conv = self.__conversations_cache.get(conv_id, None)
        if conv is None:
            try:
                conv = Conversation(
                    self.hangups_conversation_list.get(conf_id),
                    self.queue,
                    self.loop
                )
                self.__conversations_cache[conv_id] = conv
            except KeyError:
                raise
        return conv

    def leave_conversation(self, conf_id):
        self.loop.call_soon_threadsafe(lambda: self.queue.put_nowait(self.hangups_conversation_list.leave_conversation(conf_id)))
