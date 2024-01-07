from django.db import models
import datetime
#from chat import Chat
import json

# Create your models here.
class Dialogs(models.Model):
    date = models.DateTimeField(default=datetime.datetime.now())
    messages = models.TextField()

    def __str__(self):
        return f'{self.id}: {self.date.strftime("%b %d %H:%M:%S")}'
    
    def get_messages(self):
        if len(self.messages) == 0:
            return []
        return json.loads(self.messages)

    def set_messages(self, messages):
        self.messages = json.dumps(messages)
