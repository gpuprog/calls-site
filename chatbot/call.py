from django.shortcuts import render, redirect
import requests
import os
import logging
import requests
import time

DEEPGRAM_API_KEY = os.environ['DEEPGRAM_API_KEY']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']

async def on_mediarecorder_data(socket):
    async for data in socket:
        pass


def onsite(request):
    context = {
        'deepgram_api_key': DEEPGRAM_API_KEY,
        'openai_api_key': OPENAI_API_KEY
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
