from pyomegle import OmegleClient, OmegleHandler
import time
import threading

class OmegleBot(OmegleHandler):
    def __init__(self, npform, auto_reconnect=False, start_message=None):
        #Do the necessary default setup
        super(OmegleBot, self)

        #Create a link to the form where messages are sent/displayeds
        self.form = npform

        #Setup variables
        self.auto_reconnect = auto_reconnect
        self.start_message = start_message

    #Will stop the bot from auto-reconnecting
    def kill(self):
        self.auto_reconnect = False

    #Called while waiting for a stranger
    def waiting(self):
        #Defaults
        super(OmegleBot, self).waiting()

        #Clear the chat for a connecting message.
        self.form.Chat.entry_widget.clearBuffer()
        self.form.Chat.entry_widget.buffer(["Searching for a stranger..."])

        #Remove typing, as nobody is
        self.form.Chat.footer = ""

        #Update the form
        self.form.display()

    #Runs when the bot connects to a stranger
    def connected(self):
        #Defaults
        super(OmegleBot, self).connected()

        #Reset the chat so the old conversation isn't there
        self.form.Chat.entry_widget.clearBuffer()
        self.form.Chat.entry_widget.buffer(["Connected to a stranger."])

        #Send a start message if that's set
        if self.start_message != None:
            self.omegle.send(self.start_message)
            outstring = "You: " + self.start_message
            self.updateChat(outstring)

        #Update the form
        self.form.display()

    #Whenever a message is receieved
    def message(self, message):
        #Default behaviour
        super(OmegleBot, self).message(message)

        #Create the "outstring" and add it to the form
        outstring = "Stranger: " + message
        self.updateChat(outstring)

        #This removes the "stranger is typing..." message on the footer
        self.form.Chat.footer = ""

        #Update the form
        self.form.display()

    #If common likes are established this is called
    def common_likes(self, likes):
        #default behaviour
        super(OmegleBot, self).common_likes(likes)

        #Output to the chat the shared likes
        outstring = "You both like: %s" % ", ".join(likes)
        self.updateChat(outstring)

        #Update the form
        self.form.display()

    #This is called when the stranger starts typing
    def typing(self):
        #Default behaviour
        super(OmegleBot, self).typing()

        #Add a footer to the chat widget
        self.form.Chat.footer = "Stranger is typing..."

        #Update the form
        self.form.display()

    #This is called when they stop typing without sending a message
    def stopped_typing(self):
        #Default behaviour
        super(OmegleBot, self).stopped_typing()

        #Removes the footer
        self.form.Chat.footer = ""
        
        #Update the form
        self.form.display()

    #This does nothing I don't know why it's here if I'm honest. For some reason it now uses a tempban rather than a captcha 
    #Suppose it stops errors? I really don't want to remove this as something will break
    def captcha_required(self):
        print("Solve a captcha please!")
        super(OmegleBot, self).captcha_required()
        self.form.display()

    #Called when disconnected by the other user (i.e. they leave :c)
    def disconnected(self):
        #Clear the chat and tell the user it's disconnected.
        self.form.Chat.entry_widget.clearBuffer()
        self.form.Chat.entry_widget.buffer(["Disconnected!"])

        #Update that form
        self.form.display()

        #Auto reconnection handling
        if self.auto_reconnect:
            time.sleep(2)
            self.omegle.start()

    #This will use the form's
    def updateChat(self, outstring):
        #Upper line length
        lengthcap = self.form.Chat.width - 8

        #Cut the string into chunks of lengthcap if needed
        if len(outstring) > lengthcap:
            self.form.Chat.entry_widget.buffer([outstring[i:i+lengthcap] for i in range(0, len(outstring), lengthcap)], scroll_if_editing=True)
        else:
            self.form.Chat.entry_widget.buffer([outstring], scroll_if_editing=True)
