import npyscreen
import curses
import threading
from omeglebot import OmegleBot
from pyomegle import OmegleClient, OmegleHandler
import time
import json
import pyperclip
import codecs

# Redirect stdout and stderr to files
import sys
sys.stdout = codecs.open('logging/stdout.log', 'w', encoding="utf-8")
sys.stderr = codecs.open('logging/stderr.log', 'w', encoding="utf-8")

class omegleForm(npyscreen.FormBaseNew):
    def create(self):
        #Override handlers for the messagebox
        handler = {
            curses.ascii.NL: self.sendMessage,
            curses.ascii.CR: self.sendMessage,
            curses.KEY_ENTER: self.sendMessage,
            "^V": self.pasteFromClipboard,
            curses.KEY_UP: self.usePrevious,
            curses.KEY_DOWN: self.returnToOverwritten
        }

        #A way of bringing back the previous sent message, for whatever reason
        self.previousMessage = ""
        self.overwittenMessage = ""

        #The chatbox
        self.Chat = self.add(omegleChat, name="Chat", max_height=40)

        #Create the message box and add the handlers
        self.Message = self.add(omegleMessageBox, name="Message", max_height=6)
        self.Message.entry_widget.add_handlers(handler)

    def sendMessage(self, _input):
        #Get val
        value = self.Message.value
        self.Message.value = ""

        #Set the previous message to the newly sent message
        self.previousMessage = value

        #Send it to the app above
        self.parentApp.onNewMessage(value)

        #Ensure an update is ran regardless
        self.display()

    def typingOverride(self, _input):
        #Add the input to the console
        self.Message.entry_widget.value += _input

    def pasteFromClipboard(self, _input):
        #Get clipboard
        clipboardtext = pyperclip.paste()

        #This is dirty (also only pastes at the end of the message regardless, will fix this up)
        if isinstance(clipboardtext, basestring):
            self.Message.entry_widget.value += clipboardtext
            for _ in range(len(clipboardtext)):
                self.Message.entry_widget.h_cursor_right(None)

    def usePrevious(self, _input):
        #Overwrite the current message with the previous but also set the overwitten message to the overwritten one
        if self.previousMessage != "":
            self.overwittenMessage = self.Message.entry_widget.value
            self.Message.entry_widget.value = self.previousMessage

        #Move the cursor to the end of the box
        self.moveToEnd()

    def returnToOverwritten(self, _input):
        #Return to the overwitten message
        if self.overwittenMessage != "":
            self.Message.entry_widget.value = self.overwittenMessage

        #Move the cursor to the end of the box
        self.moveToEnd()

    def moveToEnd(self):
        for _ in range(len(self.Message.entry_widget.value)):
            self.Message.entry_widget.h_cursor_right(None)

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
            clientdata["shortcuts"] = {}

            #Warn user
            self.updateChat("You have not created a setup.json file. Checkout the example version as this allows for topics & an optional automatic message. TUIMegle will continue with default settings in 5 seconds.")
            time.sleep(5)

        #Get the startline (or set to None)
        if clientdata["startLine"] == "":
            startline = None
        else:
            startline = clientdata["startLine"]

        #Shortcut-list
        self.shortcuts = clientdata["shortcuts"]

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

            elif message.strip().startswith("/sc"):
                #Get everything after first space
                shortcutname = message.strip().split(" ", 1)[1]
                
                #Send shortcut
                self.shortcutSend(shortcutname)

            elif message.strip() == "/disp":
                #Forces a full display refresh - good in case messages have hung without displaying for some reason?
                self.form.DISPLAY()

            else:
                #Handles as if it's a shortcut
                self.shortcutSend(message.strip()[1:])
        #Anything else will be sent as a message
        else:
            #Send the message & stop typing
            self.client.send(message.strip())
            self.client.stopped_typing()

            #Add to the chat
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

    def shortcutSend(self, shortcut):
        #Check we're good
        if shortcut == None or shortcut == "":
            return

        #Attempt to get the message to send
        try:
            messagesToSend = self.shortcuts[shortcut]
        except KeyError:
            #Do nothing if there isn't one found
            return

        #If we manage to get to this point despite there not being a message, we'll just exit
        if messagesToSend == None or len(messagesToSend) == 0:
            return

        #Send each message
        for messageToSend in messagesToSend:
            self.client.send(messageToSend)

            outstring = "You: " + messageToSend
            self.updateChat(outstring)

    def userIsTyping(self):
        #Checks the value of the textbox to see if the user is typing
        #NOTE: Seems always return false? 
        if self.form.Message.value != "":
            self.client.typing()
        else:
            self.client.stopped_typing()

#Customtextbox
class omegleTextbox(npyscreen.Textfield):
    def edit(self):
        #Do the usual
        super(omegleTextbox, self).edit()

        #Also check to see if we're typing or not
        self.parent.parentApp.userIsTyping()

#Boxtitles for the widgets (makes it look prettier)
class omegleChat(npyscreen.BoxTitle):
    _contained_widget = npyscreen.BufferPager

class omegleMessageBox(npyscreen.BoxTitle):
    _contained_widget = omegleTextbox

#Start the app
if __name__ == "__main__":
    Application = omegleApplication().run()