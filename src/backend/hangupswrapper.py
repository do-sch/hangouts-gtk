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

import threading
import asyncio
import hangups

from gi.repository.GLib import idle_add

from hangups import build_user_conversation_list
from hangups import Client as HangupsClient, GoogleAuthError, NetworkError
from hangups.conversation import ConversationList as HangupsConversationList, Conversation as HangupsConversation


def start_client(user_data, token_storage, oauth_code=None):

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
            print("Conversation.connect_on_event")
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

    # Thread communication wrapper for ConversationList
    class ConversationList(HangupsConversationList):

        hangups_conversation_list = NotImplemented
        loop = NotImplemented
        queue = NotImplemented

        def __init__(self, hangups_conversation_list, queue, loop):
            self.hangups_conversation_list = hangups_conversation_list
            self.loop = loop
            self.queue = queue

        def connect_on_event(self, callback):
            print("ConversationList.connect_on_event")
            def _callback(conv_event):
                print("ConversationList.connect_on_event.callback")
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
            return map(lambda c: Conversation(c, self.queue, self.loop), conversations)

        def get(self, conf_id):
            return self.hangups_conversation_list.get(conf_id)

        def leave_conversation(self, conf_id):
            self.loop.call_soon_threadsafe(lambda: self.queue.put_nowait(self.hangups_conversation_list.leave_conversation(conf_id)))

    class Client:

        hangups_client = NotImplemented
        queue = NotImplemented
        loop = NotImplemented

        def __init__(self, hangups_client, queue, loop):
            self.hangups_client = hangups_client
            self.queue = queue
            self.loop = loop

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
            asyncio.run_coroutine_threadsafe(self.hangups_client.disconnect(), self.loop)

        def set_active(self):
            # async def async_set_active():
            #     await self.hangups_client.set_active()
            # self.loop.call_soon_threadsafe(self.queue.put_nowait(lambda: async_set_active()))
            asyncio.run_coroutine_threadsafe(self.hangups_client.set_active(), self.loop)

        def upload_image(self, callback, image_file, filename=None, return_uploaded_image=True):
            async def async_upload_image(callback, image_file, filename, return_uploaded_image):
                uploaded_image = await self.hangups_client.upload_image(image_file, filename, return_uploaded_image)
                idle_add(callback, uploaded_image)

            self.loop.call_soon_threadsafe(lambda: self.queue.put_nowait(async_upload_image(callback, image_file, filename, return_uploaded_image)))

    # function is called, when refresh_token is retrieved
    def session_with_refresh_token(refresh_token, user_data):
        print("session_with_refresh_token")

        # function handles getting access_token and refresh_token, if only oauth_code is avaliable
        def session_with_refresh_token_async(refresh_token, user_data):
            print("session_with_refresh_token_async")

            callback, auth_error, network_error, undefined_error = user_data

            # code here is altered from hangups.get_auth
            try:
                # with requests.Session() as session:
                #     access_token = None
                #     session.headers = {'user-agent', USER_AGENT}

                #     # get access_token from refresh_token if refreshtoken is avaliable
                #     if refresh_token is not None:
                #         access_token = _auth_with_refresh_token(session, refresh_token)

                #     # get access_token and refresh_token if only oauth_code is avaliable
                #     elif access_token is None:
                #         access_token, refresh_token = _auth_with_code(session, oauth_code)
                #         # persist refresh_token
                #         token_storage.store_refresh_token(refresh_token)

                #     # error in code
                #     else:
                #         print("error")
                #         raise HangupsError("refresh_token and access_token is None")

                #     # create hangups client
                #     cookies = _get_session_cookies(session, access_token)

                class CredentialsPrompt:
                    def get_authorization_code():
                        return oauth_code

                class RefreshTokenCache:
                    def get():
                        return refresh_token

                    def set(new_refresh_token):
                        token_storage.store_refresh_token(new_refresh_token)

                cookies = hangups.get_auth(CredentialsPrompt, RefreshTokenCache, manual_login=True)

                hangups_client = HangupsClient(cookies)

                exception = None

                def exception_handler(_loop, context):
                    queue.put(hangups_client.disconnect())
                    default_exception = Exception(context.get("message"))
                    exception = context.get("exception", default_exception)

                def on_disconnect_callback():
                    print("hangups disconnected")

                loop = asyncio.new_event_loop()
                # queue = janus.Queue(loop=loop).sync_q
                queue = asyncio.Queue(loop=loop)
                hangups_client.on_disconnect.add_observer(on_disconnect_callback)

                async def connect_task():
                    print("connect_task")
                    task = asyncio.ensure_future(hangups_client.connect())

                    on_connect = asyncio.Future()

                    def on_connect_callback():
                        print("on_connect_callback")
                        on_connect.set_result(None)

                    async def run_queue(queue):
                        while True:
                            coro = await queue.get()
                            await coro

                    print("pre_add_observer")
                    hangups_client.on_connect.add_observer(on_connect_callback)
                    done, pending = await asyncio.wait(
                        (on_connect, task), return_when=asyncio.FIRST_COMPLETED
                    )
                    print("post_add_abserver")

                    user_list, conversation_list = await build_user_conversation_list(hangups_client)
                    print("build_user_conversation_list")

                    idle_add(callback, Client(hangups_client, queue, loop), user_list, ConversationList(conversation_list, queue, loop))

                    print("pre pending")
                    pending = list(pending)
                    pending.append(run_queue(queue))

                    done, pending = await asyncio.wait(
                        pending, return_when=asyncio.FIRST_COMPLETED
                    )

                try:
                    loop.run_until_complete(connect_task())
                    print("session complete")
                except KeyboardInterrupt:
                    loop.run_until_complete(hangups_client.disconnect())
                finally:
                    loop.close()
                    if exception:
                        raise exception

            # handle Errors an show them in the GUI
            except GoogleAuthError as e:
                print("GoogleAuthError: ")
                print(e)
                raise e
                idle_add(auth_error)
            except NetworkError as e:
                print("NetworkError: ")
                print(e)
                raise e
                idle_add(network_error)
            except Exception as e:
                print("Exception: ")
                # print(e)
                raise e
                idle_add(undefined_error)

        thread = threading.Thread(
            target=session_with_refresh_token_async,
            args=(refresh_token, user_data)
        )
        thread.start()

    token_storage.get_refresh_token_cached(session_with_refresh_token, user_data)
