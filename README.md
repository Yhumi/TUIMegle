# TUIMegle
TUIMegle is a different way to experience Omegle. Born out of an annoyance with the basic CLI handling of Pymegle this small project was thrown together in an evening to bring a nice TUI experience to Omegle.

## Running & Usage
Use `requirements.txt` to get the requirements.
Using python 2.7.1 run `main.py` in a command line that supports redirection. Tested in powershell. Avoid resizing as that messes with npyscreen a lot.

After it's launched, typing and hitting enter will send a message. If you enter a command it will be ran, see commands below for a list of available commands.

During usage, if connecting to Omegle is taking a long time (or chats seemingly do not disappear when doing `/next`), open Omegle in a browser and check if you have to solve a captcha. Solve it and then use the `/reload` command, this will allow the bot to connect to omegle.

## Setup file
In order to use TUIMegle to its fullest there is a `setup_template.json` file included. First, go ahead and rename it to `setup.json` and then edit it as you wish.

```json
{
	"startLine": "Your starting message here. This is optional.",
	"topics": [
		"A topic",
		"A second topic",
		"These are also optional"
	],
	"shortcuts": {
		"example": ["this will send if you do /example"],
		"multiline": ["this will send", "followed by this"]
	}
}
```

**Note:** The starting message will be sent *before* shared topics between yourself and the other person are shown. This happens as the starting message is sent on `connection` and `shared_likes` are handled separately.

## Commands
In order to use the program there are a number of commands that can be used.

 - `/next` - Sending this message will disconnect from the current chat and look for a new one.
 - `/exit` - This will cleanly exit the program, disconnecting you from the user and closing the application.
 - `/reload` - This reloads the bot and then looks for a new chat. Use this for on-the-fly updating of your topics/starting message without the need to reload the program entirely.
 - `/sc example` - This looks for the shortcut "example" and then sends the message related to that, if found. You can also just do `/example` instead. Please not that shortcuts will not override the above commands for the sc-less variants. 

## Screenshots
![The application in use](https://loli.mafuyu.club/a6g3xTSsdo4n0CjRm92YBoA9yyHCMp3S.png)
![enter image description here](https://loli.mafuyu.club/9D1KQoa8upT8JyCNzfYe4VpYIX8IyqvR.png)
