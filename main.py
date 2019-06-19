import npyscreen
import curses
import threading
from omeglebot import OmegleBot
from pyomegle import OmegleClient, OmegleHandler
import time
import json

# Redirect stdout and stderr to files
import sys
sys.stdout = open('logging/stdout.log', 'w')
sys.stderr = open('logging/stderr.log', 'w')

class omegleForm(npyscreen.FormBaseNew):
    def create(self):
        #Override handlers for the messagebox
        handler = {
            curses.ascii.NL: self.sendMessage,
            curses.ascii.CR: self.sendMessage,
            curses.KEY_ENTER: self.sendMessage
        }

        #The chatbox
        self.Chat = self.add(omegleChat, name="Chat", max_height=40)

        #Create the message box and add the handlers
        self.Message = self.add(omegleMessageBox, name="Message", max_height=6)
        self.Message.entry_widget.add_handlers(handler)

    def sendMessage(self, _input):
        #Get val
        value = self.Message.value
        self.Message.value = ""

        #Send it to the app above
        self.parentApp.onNewMessage(value)

        #Ensure an update is ran regardless
        self.display()

class omegleApplication(npyscreen.NPSAppManaged):
    def onStart(self):
        #Create form
        self.form = self.addForm('MAIN', omegleForm, name='Omegle')
        
        #Pre-creation of bot
        self.form.Chat.entry_widget.buffer(["Creating OmegleBot..."])
        self.omegleBot = None
        self.client = None

        #Set it up
        self.createBot()

    def createBot(self):
        #If there's an existing bot (i.e. /reload was ran) we'll kill the old one first
        if self.omegleBot != None:
            self.omegleBot.kill()
            self.client.disconnect()
            self.form.display()

        #Open the setup.json and load it
        try:
            with open('setup.json') as json_data:
                clientdata = json.load(json_data)
        
        #If no file exists, defaults are hardcoded so it doesn't break everything
        except (OSError, IOError):
            #Defaults
            clientdata = {}
            clientdata["startLine"] = ""
            clientdata["topics"] = []

            #Warn user
            self.updateChat("You have not created a setup.json file. Checkout the example version as this allows for topics & an optional automatic message. TUIMegle will continue with default settings in 5 seconds.")
            time.sleep(5)

        #Get the startline (or set to None)
        if clientdata["startLine"] == "":
            startline = None
        else:
            startline = clientdata["startLine"]

        #Reading from new setup
        self.omegleBot = OmegleBot(self.form, True, startline)

        #Creating client with topics from file
        self.form.Chat.entry_widget.buffer(["Connecting..."])
        self.form.display()

        self.client = OmegleClient(self.omegleBot, wpm=42, lang='en', topics=clientdata["topics"])
        self.client.start()

    #Acts as a command handler
    def onNewMessage(self, message):
        #If this manages to get sent with nothing, nothing will happen
        if message.strip() == "":
            pass

        #This is a command (done so typos of commands don't send in embarassing fashion)
        elif message.strip().startswith("/"):
            #This command (/next) will move onto a new conversation
            if message.strip() == "/next":
                self.client.next()

            #Stops the application
            elif message.strip() == "/exit":
                self.omegleBot.kill()
                self.form.chat = []
                self.client.disconnect()

                self.form.Chat.entry_widget.buffer(["Exiting... Bye!"])
                self.form.display()
                time.sleep(5)
                exit(0)

            #Recreates the bot - allowing you to update the setup.json
            elif message.strip() == "/reload":
                self.createBot()

            else:
                #Nothing will happen
                pass
        #Anything else will be sent as a message
        else:
            self.client.send(message.strip())

            outstring = "You: " + message.strip()
            self.updateChat(outstring)

    #This will use the form's
    def updateChat(self, outstring):
        #Upper line length
        lengthcap = self.form.Chat.width - 8

        #Cut the string into chunks of lengthcap if needed
        if len(outstring) > lengthcap:
            self.form.Chat.entry_widget.buffer([outstring[i:i+lengthcap] for i in range(0, len(outstring), lengthcap)])
        else:
            self.form.Chat.entry_widget.buffer([outstring])

#Boxtitles for the widgets (makes it look prettier)
class omegleChat(npyscreen.BoxTitle):
    _contained_widget = npyscreen.BufferPager

class omegleMessageBox(npyscreen.BoxTitle):
    _contained_widget = npyscreen.Textfield

#Start the app
if __name__ == "__main__":
    Application = omegleApplication().run()