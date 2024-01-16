from django.shortcuts import render, redirect
#from chatbot.models import Dialogs
import datetime
#from ai import chat
import os
import requests
import uuid

server_key = os.environ['CALLS_API_KEY']
# if server_key is None:
#     raise Exception('CALLS_API_KEY environment variable is not defined')

if 'CALLS_SERVER' in os.environ:
    server = os.environ['CALLS_SERVER']
else:
    server = 'http://127.0.0.1:5000'

def j(response):
    if response.status_code != 200:
        raise Exception('Wrong status code: ' + str(response))
    return response.json() if len(response.text) else dict()

def dialog_title(info):
    return datetime.datetime.fromtimestamp(info['timestamp']).strftime("%b %d %H:%M:%S")

def list_dialogs():
    ids = j(requests.get(server + '/chat/list', params={'api_key':server_key}))
    infos = []
    for id in ids:
        info = j(requests.get(server + '/chat/info', params={'api_key':server_key, 'id':id}))
        info['id'] = id
        infos.append( info )
        
    infos.sort(key=lambda info: info['timestamp'])

    for idx,info in enumerate(infos):
        info['number'] = idx+1
        info['title'] = dialog_title(info)

    return infos

class Dialog:
    def sparams(self, params=dict()):
        params['api_key'] = server_key
        params['id'] = self.dialog_id
        return params
    
    def __init__(self, dialog_id=None):
        self.dialog_id = dialog_id
        if dialog_id is None:
            self.dialog_id = j(requests.post(server + '/chat/open', params=self.sparams( {'sid':str(uuid.uuid4())} )))['id']

    def close(self):
        return j(requests.post(server + '/chat/close', params=self.sparams()))

    def reply(self, message):
        return j(requests.post(server + '/chat/reply', params=self.sparams({'message':message})))
    
    def get_id(self):
        return self.dialog_id
    
    def get_info(self):
        return j(requests.get(server + '/chat/info', params=self.sparams()))
    
    def title(self):
        info = self.get_info()
        return dialog_title(info)
    
    def save(self):
        return j(requests.post(server + '/chat/save', params=self.sparams()))

    def delete(self):
        return j(requests.post(server + '/chat/delete', params=self.sparams()))

    def get_messages(self):
        return j(requests.get(server + '/chat/messages', params=self.sparams()))
       

def get_dialog(request):
    if not request.user.is_authenticated:
        return None
    
    dialog_id = request.GET.get('dialog_id', '')
    if dialog_id is not None and len(dialog_id)>0:
        request.session['dialog_id'] = dialog_id
        request.session.pop('messages', None)
        request.session.pop('summary', None)
        request.session.modified = True
    
    if 'dialog_id' not in request.session:
        dialog = Dialog()
        request.session['dialog_id'] = dialog.get_id()
        request.session.pop('messages', None)
        request.session.pop('summary', None)
        request.session.modified = True
    else:
        dialog = Dialog(request.session['dialog_id'])
        # TODO Another user could remove it

    print(f'Dialog ID is {dialog.get_id()}')
    
    return dialog

def dialogs(request):
    if not request.user.is_authenticated:
        return redirect('/accounts/login')
    context = {
        'dialogs': list_dialogs(),
    }
    request.session.pop('dialog_id', None)
    request.session.pop('messages', None)
    request.session.pop('summary', None)
    request.session.modified = True
    return render(request, 'dialogs.html', context)

def home(request):
    dialog = get_dialog(request)
    if dialog is None:
        return redirect('accounts/login')
    
    try:
        messages = dialog.get_messages()

        info = dialog.get_info()
        finished = info['finished']

        if 'messages' not in request.session:
            request.session['messages'] = messages
            request.session.modified = True
        if 'summary' not in request.session:
            request.session['summary'] = str(info)
            request.session.modified = True
        if request.method == 'POST':
            input = request.POST.get('prompt')
            
            jreply = dialog.reply(input)
            finished = jreply['finished']

            request.session['messages'] = dialog.get_messages()
            if finished:
                info = dialog.close()
                request.session['summary'] = str(info)
                request.session.modified = True
            else:
                dialog.save()
            request.session.modified = True
            context = {
                'dialog_id': dialog.get_id(),
                'title': dialog.title(),
                'finished': finished,
                'messages': request.session['messages'],
                'prompt': '',
                'summary': request.session['summary'],
            }
        else:
            context = {
                'dialog_id': dialog.get_id(),
                'title': dialog.title(),
                'finished': finished,
                'messages': request.session['messages'],
                'prompt': '',
                'summary': request.session['summary'],
            }
        return render(request, 'home.html', context)
    except Exception as e:
        print('*** RAISED EXCEPTION:', e)
        return redirect('error_handler')

def del_chat(request):
    dialog = get_dialog(request)
    if dialog is None:
        return redirect('accounts/login')
    dialog.delete()
    request.session.pop('dialog_id', None)
    request.session.pop('messages', None)
    request.session.pop('summary', None)
    request.session.modified = True
    return redirect('dialogs')

def save_chat(request):
    dialog = get_dialog(request)
    if dialog is None:
        return redirect('accounts/login')
    dialog.save()
    return redirect('home')

def new_chat(request):
    dialog = get_dialog(request)
    if dialog is None:
        return redirect('accounts/login')
    request.session.pop('dialog_id', None)
    request.session.pop('messages', None)
    request.session.pop('summary', None)
    request.session.modified = True
    return redirect('home')

def gen_json(request):
    dialog = get_dialog(request)
    if dialog is None:
        return redirect('accounts/login')
    
    request.session['summary'] = str(dialog.close())
    request.session.modified = True
    return redirect('home')

def error_handler(request):
    return render(request, '404.html')
