from django.shortcuts import render, redirect
import requests
import os
import logging
import requests
import time
import asyncio
import json
import threading
import re

from websockets import ConnectionClosed, ConnectionClosedError
from websockets.server import serve
from websockets.client import connect

DEEPGRAM_API_KEY = os.environ['DEEPGRAM_API_KEY']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']

DEEPGRAM_RECOG_URL = "wss://api.deepgram.com/v1/listen?model=nova-2-phonecall&language=en"
DEEPGRAM_SPEAK_URL = "https://api.deepgram.com/v1/speak?model=aura-asteria-en&encoding=mp3"

SOCKET_MEDIARECORDER_PORT = 8765

if 'SERVER_IP_ADDRESS' in os.environ:
    my_ip_address = os.environ['SERVER_IP_ADDRESS']
else:
    my_ip_address = '127.0.0.1'

socket_stt = None # Deepgram Speech-To-Text socket
socket_web = None # Website socket
session_tts = None # Session to Text-To-Speech
socket_mediarecorder_addr = f'ws://{my_ip_address}:{SOCKET_MEDIARECORDER_PORT}' # Mediarecorder socket address

#
# Transfer data from user microphone to STT
#
async def task_mediarecorder():
    async def on_mediarecorder(socket):
        global socket_web
        socket_web = socket
        async for data in socket:
            try:
                await socket_stt.send(data)
            except Exception as e: # ConnectionClosedError, ConnectionClosedOk
                print("on_mediarecorder", str(e))
                break

    while True:
        try:
            async with serve(on_mediarecorder, 'localhost', SOCKET_MEDIARECORDER_PORT) as server:
                await asyncio.Future()
        except Exception as e:# ConnectionClosedError, ConnectionClosedOk
            print("task_mediarecorder", str(e))
            continue

#
# Await data from STT
#
async def task_stt_receive():
    global socket_stt
    # https://websockets.readthedocs.io/en/stable/reference/asyncio/client.html
    while True:
        try:
            socket_stt = await connect(DEEPGRAM_RECOG_URL, extra_headers={'Authorization':f'Token {DEEPGRAM_API_KEY}'})
            #async for stt_socket in connect(f'{DEEPGRAM_RECOG_URL}?token={DEEPGRAM_API_KEY}'):
            while True:
                    data = await socket_stt.recv()
                    assert type(data) is str
                    message = json.loads(data)
                    if message['type'] != 'Results':
                        continue
                    transcript = message['channel']['alternatives'][0]['transcript']
                    assert type(transcript) is str
                    final = message['is_final']
                    assert type(final) is bool
                    if final and len(transcript)>0:
                        print(f'{transcript}')
                        await ask_gpt(transcript)
                        #await play(transcript) # ECHO ~2 sec
        except Exception as e:# ConnectionClosed:
            print("task_stt_receive", str(e))
            await socket_stt.close()
            continue

#
# Call GPT
#
async def ask_gpt(question:str) -> None:
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json',
        #'Connection': 'keep-alive'
    }

    #start = time.time()
    url = 'https://api.openai.com/v1/chat/completions'
    data = {
        'model': 'gpt-4o',
        'messages': [
            { 'role': "system", 'content': "You are phone assistant, conencted to user via speech-to-text technology. Answer shortly on user question." },
            { 'role': "user", 'content': question }
        ],
        'max_tokens': 100,
        'stream': True
    }
    #first = True
    answer = ''    
    #with await asyncio.to_thread(requests.post, url, json=data, headers = headers, stream=True) as response:
    response = await asyncio.to_thread(requests.post, url, json=data, headers = headers, stream=True)
    for line in response.iter_lines():
        if not line:
            continue
        data = line.decode('utf-8')
        if data.startswith(' [DONE]'):
            break
        if data.startswith("data:"):
            data = data[5:]
        jdata = json.loads(data)
        text = jdata['choices'][0]['delta']['content']
        answer += text
        if re.match(text, r'[.,!?]'):
            print(f'>>>{answer}')
            await play(answer)
            answer = ''

            # ret = time.time()
            # if line and first:
            #     first = False
            #     times.append(ret-start)
            #     decoded_line = line.decode('utf-8')
            #     print(f"{ret-start}\n")
    if len(answer)>0:
        print(f'>>>{answer}')
        await play(answer)

#
# Call Synthesis
#
async def play(text:str) -> str:
    response = await asyncio.to_thread(session_tts.post, DEEPGRAM_SPEAK_URL, json={'text': text}, stream=True)
    for chunk in response.iter_content(chunk_size=None):
        if chunk:
            await socket_web.send(chunk)

async def process():
    headers = {
        'Authorization': f'token {DEEPGRAM_API_KEY}',
        'Content-Type': 'application/json',
        #'Connection': 'keep-alive'
    }

    global session_tts
    session_tts = requests.Session()
    session_tts.headers.update(headers)

    tasks = [
        asyncio.create_task(task_mediarecorder()),
        asyncio.create_task(task_stt_receive())
    ]
    await asyncio.gather(*tasks)

call_loop = asyncio.new_event_loop()
call_thread = threading.Thread(
    target = call_loop.run_forever,
    name = "Call Thread"
)
call_thread.start()
asyncio.run_coroutine_threadsafe(process(), call_loop)

async def onsite(request):
    context = {
        'deepgram_api_key': DEEPGRAM_API_KEY,
        'openai_api_key': OPENAI_API_KEY,
        'socket_mediarecorder_addr': socket_mediarecorder_addr
    }

    return render(request, 'call.html', context)

def test_openai(use_session=True):
    logging.basicConfig(level=logging.DEBUG)

    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json',
        #'Connection': 'keep-alive'
    }

    if use_session:
        session = requests.Session()
        session.headers.update(headers)
    else:
        session = requests

    # Function to make requests
    times = []
    def make_request(session, question):
        start = time.time()
        url = 'https://api.openai.com/v1/chat/completions'
        data = {
            'model': 'gpt-4o',
            'messages': [
                { 'role': "system", 'content': "You are phone assistant, conencted to user via speech-to-text technology. Answer shortly on user question." },
                { 'role': "user", 'content': question }
            ],
            'max_tokens': 100,
            'stream': True
        }
        first = True
        with session.post(url, json=data, headers = None if use_session else headers, stream=True) as response:
            for line in response.iter_lines():
                ret = time.time()
                if line and first:
                    first = False
                    times.append(ret-start)
                    decoded_line = line.decode('utf-8')
                    print(f"{ret-start}\n")

    for n in range(1,3):
        make_request(session, "Translate the following English text to French: 'Hello, how are you?'")
        make_request(session, "Translate the following English text to Spanish: 'What is your name?'")
        make_request(session, "Who is Alber Einstein?")

    if len(times)>0:
        print(times)
        times.sort()
        print(f'min={min(times)}, max={max(times)}, avg={sum(times)/len(times)}, med={times[int(len(times)/2)]}')

    if use_session:
        session.close()

def test_deepgram(use_session=True):
    logging.basicConfig(level=logging.DEBUG)

    headers = {
        'Authorization': f'token {DEEPGRAM_API_KEY}',
        'Content-Type': 'application/json',
        #'Connection': 'keep-alive'
    }

    if use_session:
        session = requests.Session()
        session.headers.update(headers)
    else:
        session = requests

    # Function to make requests
    times = []
    def make_request(session, text):
        start = time.time()
        url = 'https://api.deepgram.com/v1/speak?model=aura-asteria-en'
        data = {'text': text }
        first = True
        with session.post(url, json=data, headers = None if use_session else headers, stream=True) as response:
            for line in response.iter_lines():
                ret = time.time()
                if line and first:
                    first = False
                    times.append(ret-start)
                    #decoded_line = line.decode('utf-8')
                    print(f"{ret-start}\n")

    for n in range(1,10):
        make_request(session, "Translate the following English text to French: 'Hello, how are you?'")
        make_request(session, "Translate the following English text to Spanish: 'What is your name?'")
        make_request(session, "Who is Alber Einstein?")

    if len(times)>0:
        print(times)
        times.sort()
        print(f'min={min(times)}, max={max(times)}, avg={sum(times)/len(times)}, med={times[int(len(times)/2)]}')

    if use_session:
        session.close()

if __name__ == '__main__':
    # From MIC: https://stackoverflow.com/questions/55202250/persisting-recorded-audio-from-browser-to-python-api-as-wav-file
    #test_openai(False)
    test_deepgram(True)
