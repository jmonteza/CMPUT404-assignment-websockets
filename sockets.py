#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# References:
# Author: Abram Hindle
# Author URL: https://github.com/abramhindle
# Title: WebSocketsExamples (chat.py)
# Source: https://github.com/abramhindle/WebSocketsExamples/blob/master/chat.py

import flask
from flask import Flask, request, redirect
from flask_sockets import Sockets, Rule
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

class Client:
    def __init__(self):
        self.queue = queue.Queue()

    def put(self, item):
        self.queue.put_nowait(item)

    def get(self):
        return self.queue.get()

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def get_set_listeners(self):
        return self.listeners

    def remove_set_listener(self, listener):
        self.listeners.remove( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        # self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

myWorld = World()        

def broadcast_to_other_clients(message):
    for listener in myWorld.get_set_listeners():
        if isinstance(listener, Client):
            # print(type(listener))
            listener.put(json.dumps(message))

def set_listener( entity, data ):
    ''' do something with the update ! '''

myWorld.add_set_listener( set_listener )
        
@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    return redirect("/static/index.html")

def read_ws(ws,client):
    '''A greenlet function that reads from the websocket and updates the world'''
    # XXX: TODO IMPLEMENT ME
    try:
        while True:
            message = ws.receive()
            
            if message is not None:
                # print(message, type(message))
                try:
                    entity_dict = json.loads(message)
                except Exception as e:
                    # print("JSON Loads Error", e)
                    pass
                else:
                    # print(entity_dict, type(entity_dict))
                    # myWorld.set()
                    for key, val in entity_dict.items():
                        if key == "clear":
                            myWorld.clear()
                        else:
                            myWorld.set(key, val)
                        # print(myWorld.world())
                        broadcast_to_other_clients(entity_dict)

            else:
                break
    except Exception as e:
        print(f"Websocket Error (read_ws) {e}")
        
    return None

@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    # XXX: TODO IMPLEMENT ME
    # message = ws.receive()
    # print("*" * 1000, message)
    # ws.send("Hello World!!!");
    
    # while not ws.closed:
    #     message = ws.receive()
    #     print(message)
        # python_dict = json.loads(message)
        # print(python_dict)

        
        # ws.send(message)

    # return "Hello World!"

    # Create a client
    client = Client()

    # Add this specific client as a listener
    myWorld.add_set_listener(client)

    # Create a greenlet
    greenlet = gevent.spawn(read_ws, ws, client)

    try:
        while True:
            # Get the message from client
            message = client.get()
            # print("Message type", type(message))

            # Send the message back to the websocket
            ws.send(message)
    except Exception as e:
        print(f"WebSocket Error (subscribe_socket) {e}")
    finally:
        # Remove this client as one of the world's listener
        myWorld.remove_set_listener(client)

        # Kill this specific greenlet
        gevent.kill(greenlet)
        



# I give this to you, this is how you get the raw body/data portion of a post in flask
# this should come with flask but whatever, it's not my project.
def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data.decode("utf8") != u''):
        return json.loads(request.data.decode("utf8"))
    else:
        return json.loads(request.form.keys()[0])

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    '''update the entities via this interface'''
    json_request = flask_post_json()

    myWorld.set(entity, json_request)

    return myWorld.get(entity)

@app.route("/world", methods=['POST','GET'])    
def world():
    '''you should probably return the world here'''
    return myWorld.world()

@app.route("/entity/<entity>")    
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''
    entity = myWorld.get(entity)
    return entity


@app.route("/clear", methods=['POST','GET'])
def clear():
    '''Clear the world out!'''
    myWorld.clear()
    return myWorld.world()


sockets.url_map.add(
    Rule('/subscribe', endpoint=subscribe_socket, websocket=True))

if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
