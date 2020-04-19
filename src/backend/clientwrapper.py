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

class Client:
    hangups_client = NotImplemented
    queue = NotImplemented
    loop = NotImplemented

    def __init__(self, hangups_client, queue):
        self.hangups_client = hangups_client
        self.queue = queue
        self.loop = asyncio.get_running_loop()

    def connect_on_event(self, callback):
        print("Client.connect_on_event")
        def _callback(event):
            print("Client.connect_on_event.callback")
            idle_add(callback, event)
        self.hangups_client.on_connect.add_observer(_callback)
        return _callback

    def disconnect_on_event(self, callback):
        self.hangups_client.on_connect.remove_observer(callback)

    def connect_on_reconnect(self, callback):
        def _callback(event):
            idle_add(callback, event)
        self.hangups_client.on_reconnect.add_observer(_callback)
        return _callback

    def disconnect_on_reconnect(self, callback):
        self.hangups_client.on_reconnect.remove_observer(callback)

    def connect_on_disconnect(self, callback):
        def _callback(event):
            idle_add(callback, event)
        self.hangups_client.on_disconnect.add_observer(_callback)
        return _callback

    def disconnect_on_disconnect(self, callback):
        self.hangups_client.on_disconnect.remove_observer(callback)

    def connect_on_state_update(self, callback):
        def _callback(event):
            idle_add(callback, event)
        self.hangups_client.on_state_update.add_observer(_callback)
        return _callback

    def disconnect_on_state_update(self, callback):
        self.hangups_client.on_state_update.remove_observer(callback)

    def disconnect(self):
        print("add disconnect to queue")
        self.queue.continue_queue = False
        self.loop.call_soon_threadsafe(lambda: self.queue.put_nowait(self.hangups_client.disconnect()))
        #asyncio.run_coroutine_threadsafe(self.hangups_client.disconnect(), self.loop)

    def set_active(self):
        # async def async_set_active():
        #     await self.hangups_client.set_active()
        # self.loop.call_soon_threadsafe(self.queue.put_nowait(lambda: async_set_active()))
        self.loop.call_soon_threadsafe(lambda: self.queue.put_nowait(self.hangups_client.set_active()))
        #asyncio.run_coroutine_threadsafe(self.hangups_client.set_active(), self.loop)

    def upload_image(self, callback, image_file, filename=None, return_uploaded_image=True):
        async def async_upload_image(callback, image_file, filename, return_uploaded_image):
            uploaded_image = await self.hangups_client.upload_image(image_file, filename, return_uploaded_image)
            idle_add(callback, uploaded_image)

        self.loop.call_soon_threadsafe(lambda: self.queue.put_nowait(async_upload_image(callback, image_file, filename, return_uploaded_image)))
