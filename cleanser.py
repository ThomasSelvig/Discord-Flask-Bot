# https://discordapp.com/oauth2/authorize?client_id=703918313880944705&scope=bot&permissions=8
import discord, asyncio, time, datetime, threading, timeago, pytz, os
from flask import Flask, render_template, request
from hashlib import sha256
from subprocess import check_output

TOKEN = "no, go away"
GUILD = 649119550633410611

# runs synced in main thread
client = discord.Client()
# runs asynced in separate thread
app = Flask(__name__)

# dict of active users to datetime of last seen message, will be accessed across threads (thread safe: only the main thread will write to it)
# do not use this as an alone criteria! whitelist people who have elevated permissions, bots, etc..
active = {}
commands = {}  # command: function(message)      declared in "if __name__" thing


def findUnclean(guild):
	# remember to update the "active" list by doing the bot command in the chat!
	unclean = []
	for member in guild.members:
		if len(member.roles) == 1 and member not in active:  # '@everyone' role is distributed to everyone
			unclean.append(member)

	return unclean


async def updateActive(days=5):
	# takes ~5s in hypixel central with days=5
	active.clear()
	# activity must be recorded after this point
	after = datetime.datetime.now() - datetime.timedelta(days=days)

	for channel in client.get_guild(GUILD).text_channels:
		async for m in channel.history(after=after, oldest_first=True):
			
			if m.author in active and (m.created_at - active[m.author]).total_seconds() > 0: # if m is the latest message
				active[m.author] = m.created_at

			elif m.author not in active:
				active[m.author] = m.created_at


def htmlTable(members):
	members = [{
		"name": user.name,
		"nick": user.nick if user.nick else "",
		"mention": user.mention,
		"joined": timeago.format(user.joined_at),
		"age": timeago.format(user.created_at)
	} for user in members]
	
	return render_template("index.html", users=members)


def personalizedEmbed(member):
	def statusString(status):
		return "Online" if status == discord.Status.online else \
			"Offline" if status == discord.Status.offline else \
			"Idle" if status == discord.Status.idle else \
			"Do not disturb" if status == discord.Status.dnd else \
			status

	u = member
	data = {
		"Generic": {
			"Name": str(u),
			"Display Name": u.display_name,
			"Mention": u.mention,
			"ID": u.id,
			"Animated Avatar": str(u.is_avatar_animated()),
			"Robot": str(u.bot)
		},
		"Age": {
			"Joined at": str(u.joined_at),
			"Joined server": timeago.format(u.joined_at),
			"Created at": str(u.created_at),
			"Created": timeago.format(u.created_at)
		},
		"Temporary data": {
			"Last Nitro Boost": str(u.premium_since) if u.premium_since else "",
			"Activity": f"{u.activity}" if u.activity else "",
			"Voice State": str(u.voice),
			"Top Role": str(u.top_role),
			"Roles": ", ".join([f"{r} ({timeago.format(r.created_at)})" for r in u.roles]).replace("@everyone ", "everyone ")
		},
		"Status": {
			"Status": statusString(u.status),
			"Desktop Status": statusString(u.desktop_status),
			"Mobile Status": statusString(u.mobile_status),
			"Web Status": statusString(u.web_status),
			"Currently Mobile": str(u.is_on_mobile())
		}
	}
	embed = discord.Embed(
		title=f"{u.name} ({u.nick})" if u.nick is not None else u.name,
		type="rich",
		color=discord.Color.from_rgb(0, 139, 139)
	)
	embed.set_image(url=u.avatar_url)
	for catName, cat in data.items():
		embed.add_field(name=catName, value="\n".join([f"{k}: {v}" for k, v in cat.items()]), inline=False)

	return embed


def sherlock(un):
	path = os.path.dirname(os.path.abspath(__file__))
	out = check_output(f"python \"{path}/sherlock/sherlock.py\" --print-found --no-color {un}").decode().strip()
	out = "\n".join([line for line in out.split("\r\n") if line[1] in "+*"])
	return out


@app.route("/")
def root():
	if "auth" in request.args and request.args["auth"] == sha256(b"Litago123#").hexdigest():
		# auth approved
		guild = client.get_guild(GUILD)  # hypixel central
		return htmlTable(findUnclean(guild))# guild.members

	else:
		# if no authentication is given then return the chicken broth
		return '<!doctype html><html lang="en"> <head> <meta property="og:title" content="Litago smaker godt"/><meta property="og:type" content="website"/><meta property="og:url" content="http://litago.xyz"/><meta property="og:image" content="http://litago.xyz/static/chicken.gif"/><meta property="og:description" content="Litago > Cocio"/> <title>401 fuck off</title> <meta charset="utf-8"> <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no"> <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0-beta.2/css/bootstrap.min.css" integrity="sha384-PsH8R72JQ3SOdhVi3uxftmaW6Vc51MKb0q5P2rRUpPvrszuE4W1povHYgTpBfshb" crossorigin="anonymous"> </head> <body> <div class="container"> <img src="http://litago.xyz/static/chicken.gif" alt=""> </div><script src="https://code.jquery.com/jquery-3.2.1.slim.min.js" integrity="sha384-KJ3o2DKtIkvYIK3UENzmM7KCkRr/rE9/Qpg6aAZGJwFDMVNA/GpGFF93hXpG5KkN" crossorigin="anonymous"></script> <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.12.3/umd/popper.min.js" integrity="sha384-vFJXuSJphROIrBnz7yo7oB41mKfc8JzQZiCq4NCceLEaO4IHwicKwpJf9c9IpFgh" crossorigin="anonymous"></script> <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0-beta.2/js/bootstrap.min.js" integrity="sha384-alpBpkh1PFOepccYVYDB4do5UnbKysX5WZXm3XxPqe5iKTfUKjNkCk9SaVuEZflJ" crossorigin="anonymous"></script> </body></html>'


class MessageCommands:
	async def help(message):
		await message.channel.send("Availible commands: \n" + "\n".join(commands.keys()))

	async def update(message):
		if "doki club members" not in [r.name.lower() for r in message.author.roles]:
			await message.channel.send("Elevated privileges required: 'DOKI CLUB MEMBERS'")
			return None

		a = time.time()
		await updateActive()
		await message.channel.send(f"Finished updating in {round(time.time() - a, 2)} seconds")

	async def person(message):
		# give all info about the user
		if len(message.mentions) == 0:
			await message.channel.send(embed=personalizedEmbed(message.author))
		elif len(message.mentions) > 5:
			await message.channel.send("Limit reached: Max 5 users at a time.")
		else:
			for member in message.mentions:
				await message.channel.send(embed=personalizedEmbed(member))

	async def time(message):
		timeString = lambda tz: datetime.datetime.now(pytz.timezone(tz)).strftime("**%X** %a %b %d")
		await message.channel.send("\n".join([
			"TZs:",
			f"**New Zealand** (Pacific/Auckland): {timeString('Pacific/Auckland')}",
			f"**Norway** (Europe/Oslo): {timeString('Europe/Oslo')}",
			f"**USA (SC)** (US/Eastern): {timeString('US/Eastern')}"
		]))

	async def sherlock(message):
		if message.author.id != 165140141751402496:
			await message.channel.send("You have to be __me__ to use this command (due to latency)")
			return None

		args = message.content.split(" ")[1:]
		await message.channel.send(sherlock(" ".join(args)))


@client.event
async def on_message(message):
	if message.author == client.user:
		return None
	
	else:
		for cmd in commands:
			if message.content.strip().lower().startswith(cmd):
				await commands[cmd](message)
				break


@client.event
async def on_ready():
	print(f"Booted at {time.asctime()}")
	
	a = time.time()
	await updateActive()
	print(time.time()-a, "s used to updated active")


if __name__ == "__main__":
	commands = {
		";help": MessageCommands.help,
		";update": MessageCommands.update,
		";person": MessageCommands.person,
		";time": MessageCommands.time,
		";sherlock": MessageCommands.sherlock
	}
	threading.Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 80, "debug": False}).start()
	client.run(TOKEN)