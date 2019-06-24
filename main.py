import npyscreen
import curses
import threading
from omeglebot import OmegleBot
from pyomegle import OmegleClient, OmegleHandler
import time
import json
import pyperclip
import codecs
import math
import re
import webbrowser

# Redirect stdout and stderr to files
import sys
sys.stdout = codecs.open('logging/stdout.log', 'w', encoding="utf-8")
sys.stderr = codecs.open('logging/stderr.log', 'w', encoding="utf-8")

#Locale issue, maybe?
import locale
locale.setlocale(locale.LC_ALL, '')

class omegleForm(npyscreen.FormBaseNew):
    def create(self):
        #Override handlers for the messagebox
        handler = {
            curses.ascii.NL: self.sendMessage,
            curses.ascii.CR: self.sendMessage,
            curses.KEY_ENTER: self.sendMessage,
            "^V": self.pasteFromClipboard,
            curses.KEY_UP: self.moveThroughList,
            curses.KEY_DOWN: self.moveThroughList
        }

        #A way of bringing back any previous sent message, for whatever reason
        self.previousMessages = []
        self.currentIndex = 0
        self.overwitten = ""

        #The chatbox
        self.Chat = self.add(omegleChat, name="Chat", max_height=40)

        #Create the message box and add the handlers
        self.Message = self.add(omegleMessageBox, name="Message", max_height=6)
        self.Message.entry_widget.add_handlers(handler)

    def sendMessage(self, _input):
        #Get val
        value = self.Message.value
        self.Message.value = ""

        #Append the newest message
        self.previousMessages += [value]

        #Move the message index
        self.currentIndex = len(self.previousMessages)

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

        #This is dirty 
        if isinstance(clipboardtext, basestring):
            #We need to get the current cursor position
            cursorIndex = self.Message.entry_widget.cursor_position

            #Get the current value of the string
            currentValue = self.Message.entry_widget.value

            #Manipulate that string
            self.Message.entry_widget.value = currentValue[:cursorIndex] + clipboardtext + currentValue[cursorIndex:]

            #Lets attempt a cleaner approach to moving the cursor
            newCursorIndex = cursorIndex + len(clipboardtext)

            #Move it to the new index
            self.setCursorPosition(newCursorIndex)

    def moveThroughList(self, _input):
        #If there are no previous message nothing can happen
        if len(self.previousMessages) == 0:
            return

        #Get the index of the chosen movement direction
        if _input == curses.KEY_UP:
            #Remove one from the current index
            newIndex = self.currentIndex - 1
        else:
            #If we pick down and we're at the latest position, nothing should be done
            if self.currentIndex >= len(self.previousMessages):
                return
            
            #Otherwise, add 1 to the current index
            newIndex = self.currentIndex + 1

        #Some sanity checking
        #If it's below 0, there's nothing else
        if newIndex < 0:
            newIndex = 0

        #If the new index is >= the length of the list we're going back to the overwitten message
        if newIndex >= len(self.previousMessages):            
            #Simply set the current message properly and ensure the index is at the end
            self.Message.entry_widget.value = self.overwitten
            self.currentIndex = len(self.previousMessages)
        else:
            #Check to see if the previous index is the last index
            if self.currentIndex == len(self.previousMessages):
                #Save the current message
                self.overwitten = self.Message.entry_widget.value

            #Now we can get the new index's message
            newMessage = self.previousMessages[newIndex]

            #We've moved, so we need to overwrite the current index
            self.currentIndex = newIndex

            #Replace the new message
            self.Message.entry_widget.value = newMessage

        #Move the cursor to the end of the box
        self.setCursorPosition()

    def setCursorPosition(self, specificPosition=None):
        #If no position is specified, it will default to moving the cursor to the end of the string
        if specificPosition == None:
            specificPosition = len(self.Message.entry_widget.value)
        
        #Move the cursor
        self.Message.entry_widget.cursor_position = specificPosition

        #Update the drawing
        self.display()       

class omegleApplication(npyscreen.NPSAppManaged):
    def onStart(self):
        #Create form
        self.form = self.addForm('MAIN', omegleForm, name='Omegle')
        
        #Pre-creation of bot
        self.form.Chat.entry_widget.buffer(["Creating OmegleBot..."], scroll_if_editing=True)
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
        self.form.Chat.entry_widget.buffer(["Connecting..."], scroll_if_editing=True)
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

                self.form.Chat.entry_widget.buffer(["Exiting... Bye!"], scroll_if_editing=True)
                self.form.display()
                time.sleep(3)
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
            self.form.Chat.entry_widget.buffer([outstring[i:i+lengthcap] for i in range(0, len(outstring), lengthcap)], scroll_if_editing=True)
        else:
            self.form.Chat.entry_widget.buffer([outstring], scroll_if_editing=True)

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

#Custom buffer pager
class omegleBufferPager(npyscreen.BufferPager):
    def __init__(self, screen, maxlen=False, *args, **keywords):
        #Run the usual init
        super(omegleBufferPager, self).__init__(screen, *args, **keywords)

        #Set to true, important
        self.interested_in_mouse_even_when_not_editable = True

#Boxtitles for the widgets (makes it look prettier)
class omegleChat(npyscreen.BoxTitle):
    _contained_widget = omegleBufferPager

    def handle_mouse_event(self, mouse_event):
        #Event
        mouse_id, rel_x, rel_y, z, bstate = self.interpret_mouse_event(mouse_event)

        #Okay this is going to be epic
        #Okay so this is going to be some mathemagic to get the positon of the text under the cursor
        #Take the display's starting position the height of the widget, do some flooring magical shit
        cursorLine = rel_y // self.entry_widget._contained_widget_height + self.entry_widget.start_display_at

        #Get the text for that line
        if cursorLine <= len(self.entry_widget.values):
            cursorLineText = self.entry_widget.values[cursorLine - 1]
        else:
            return

        #We now need to do some magical shit with the x involving character width average floored? This is such a FUCKING mess
        #Find the character widths for the line
        allCharWidth = []
        for x in cursorLineText:
            allCharWidth += [self.find_width_of_char(x)]

        #Calculate the average, and floor it 
        averageCharacterWidth = math.floor(sum(allCharWidth) / len(allCharWidth))

        #Okay so now we're flooring the average width vs relative x
        cursorIndex = int(rel_x // averageCharacterWidth)

        #Letter position
        #Take 2 away as the line starts with an empty space of 1 character width
        letterIndex = cursorIndex - 2

        #Now then we can get the character for one thing
        #There's 1 width of character space at the start to be accounted for
        if cursorIndex <= len(cursorLineText) - 1:         
            clickedLetter = cursorLineText[letterIndex]
        else:
            return

        #If a space is clicked, nothing
        if clickedLetter == ' ':
            return

        #Using the getClosestWord function to get the closes word
        wordClicked = self.getClosestWord(cursorLineText, letterIndex)

        #Now we can check if the word is a URL - If it is, open it
        if self.checkURL(wordClicked):
            webbrowser.open(wordClicked, new=0, autoraise=True)

    def getClosestWord(self, string, position):
        #Search the beginning for the last space in the string
        #As we always add one to the beginning index to remove the space, if it fails and -1 is returned it will actually act as normal. Neat.
        beginningSpaceIndex = string[:position+1].rfind(' ')

        #Set to the beginning of the string ifnothing is found
        if beginningSpaceIndex == -1:
            beginningSpaceIndex = 0

        #End search
        endingSpaceIndex = string.find(' ', position)

        #Set to the length of the string so the -1 function works if it doesn't find anything
        if endingSpaceIndex == -1:
            endingSpaceIndex = len(string)

        #Now we return the word with whitespace removed
        return string[beginningSpaceIndex:endingSpaceIndex].strip()

    def checkURL(self, string):
        #Django URL check
        regex = re.compile(
            r'^(?:http|ftp)s?://' # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
            r'localhost|' #localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
            r'(?::\d+)?' # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        #Returns true if there is a match
        return re.match(regex, string) is not None

class omegleMessageBox(npyscreen.BoxTitle):
    _contained_widget = omegleTextbox

#Start the app
if __name__ == "__main__":
    Application = omegleApplication().run()