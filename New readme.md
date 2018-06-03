# Marshal Command Code: A Syntax Highlighter

*Created by [Nathan Liparski](http://twitter.com/NateLipiarski) with input and testing by [Moesh](http://moesh.ca/about) and [Maxaxik](https://twitter.com/maxaxik).*

## Using MCC Will Make Your Code Maintainable

__Latest News__
v1.13 of **Minecraft: Java Edition** brought many things to the table and MCC stepped up to add many improvements of its own.  The new version is now based on Minecraft's own command parser, Brigadier.  With this change, we've also fazed out [Smelt](http://smelt.gnasp.com) support. (Sorry Gnasp)

__What is Marshal Command Code?__

Marshal Command Code is a syntax highlighter built for Sublime Text! Our goal is to provide practical highlighting to support as many themes as possible. We attempt to strike a balance between categorization and readability, meaning the code highlights the relevant parts of the logic while checking for errors in the rigid structure of NBT, JSON, the scoreboard, and commands themselves.

__Well, what does it look like?__

***No Syntax Highlighting***
![No Syntax Highlighting](https://i.imgur.com/yzuc9mT.png)
***Nate's Special Color Scheme.***
![An Example of MCC](https://i.imgur.com/dbBfbPH.png)
***Sixteen Color Scheme.***
![An Example of MCC](https://i.imgur.com/g6mt5Y1.png)
***Monokai Color Scheme.***
![An example of MCC](https://i.imgur.com/ONm6hI0.png)
***Breakers Color Scheme.***
![An Example of MCC](https://i.imgur.com/RLl3Y94.png)

## Installation

Sublime is an extremely powerful, but kind of complicated, text editor. Learning how to use it effectively will be key to keeping your code maintainable.

### Instructions

*Installing Package Control can be scary, but just follow the instructions carefuly. You'll be OK.*

1. Install [Sublime](https://www.sublimetext.com/)
2. Install [Package Control Plugin](https://packagecontrol.io/installation) (double-check your Sublime version)
3. With Sublime opened, press Ctrl+Shift+P to open the Command Palette
4. Type "install package" into the Command Palette and select "Package Control: Install Package"
5. Type "Marshal Command Code" to filter the packages and select "Marshal Command Code Syntax Highlighter"

Now any file with an .mcc or .mcfunction extension will use the Marshal Command Code syntax highlighting.

If you run into any issues, feel free to send an email to [Moesh](mailto:moesh@moesh.ca) with the details or open an issue on the [github issue page](https://github.com/42iscool42/MCC/issues).

## What If You Want to Make Your Color Scheme Work With MCC
The first thing you should know is that MCC already automatically converts color schemes on its own, so you don't have to do anything if you don't want to.  If you really want to make sure your color scheme works with MCC, continue reading.


There are six scopes you will need to add and one you should propably already have in your color scheme.
1. **mccconstant:** Numbers, true/false, relative coords, and suffixes in nbt values will all have this scope.
2. **mcccoment:** Comments
3. **mccstring:** Any quoted or unquoted strings (e.g. usernames) will have this scope
4. **mcccommand:** All commands as well as any operators such as =, <, \*=, etc.
5. **mccentity:** Entity selectors as well as specific entities such as armor_stand will get this scope
6. **mccliteral:** This scope is applied to keywords liek merge, grant, set
7. **invalid.illegal or invalid:** Like I said above, most color schemes already have this one.


While usually you just have to set the foreground color when styling your scopes, because of the way MCC and Sublime work you also have to set the background parameter for all of the mcc scopes.  The background color should be a color that is just one away in red, green, or blue from whatever you chose as the background color.  Be aware that if your hex color ends in two zeros or four zeros you can not just subtract one from the hex value.  For example, say you chose #090300, a nice gray, as your background color.  If you subtract one from this, you get #0902FF which is a dark blue.  What you should do instead is subtract one from the middle two set of digits to get #090200 which is a color imperceptibly different from your original color.


The final thing that you need to do is add (MCC) to the name string within the p list for your color scheme or put (MCC) in the actual file name of your scheme.  It is important that you write (MCC) in all caps or else MCC won't recognize that it is a compatible color scheme.