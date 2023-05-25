# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
from review import Review
import pdb
import collections

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']


class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.reviews = {}
        self.banned = set()
        self.adversary_counts = collections.defaultdict(int)
        self.warnings = collections.defaultdict(int)



    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel
        

    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs). 
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel. 
        '''
        # Ignore messages from the bot 
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    # We don't really use handle_dm
    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            self.reports.pop(author_id)

    #This one is the main one
    async def handle_channel_message(self, message):

        if message.author.name in self.banned:
            await message.channel.send('Sorry, your account has been banned.')
            return
        
        if message.channel.name == f'group-{self.group_num}-mod':
            await self.handle_mod_message(message)

        # Only handle messages sent in the "group-#" channel
        if not message.channel.name == f'group-{self.group_num}': # split into helper function to handle group and mod
            return
        
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
            return
        
        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        if self.reports[author_id].report_complete():
            return

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)


        # If the report is complete or cancelled, remove it from our map and process it
        if self.reports[author_id].report_complete():
            if self.reports[author_id].cancel_or_separate():
                self.reports.pop(author_id)
                return
            report = self.reports[author_id]
            # Forward the message to the mod channel
            mod_channel = self.mod_channels[message.guild.id]
            self.reviewing = True
            # await mod_channel.send(f'Report filed:\n{message.author.name}: "{report.data}"')
            await mod_channel.send('Report filed!')
            await mod_channel.send(f'Abuser:\n{report.get_abuser()}')
            await mod_channel.send(f'Abusive Message:\n{report.get_abusive_message()}')
            await mod_channel.send(f'Report Data:\n{report.get_data()}')
            message.content = 'REPORT_START'
            await self.handle_mod_message(message)

        # # Forward the message to the mod channel
        # mod_channel = self.mod_channels[message.guild.id]
        # await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        # scores = self.eval_text(message.content)
        # await mod_channel.send(self.code_format(scores))

    async def handle_mod_message(self, message):
        # if not self.reviewing:
        #     return
        mod_channel = self.mod_channels[message.guild.id]

        author_id = message.author.id
        print('AUTHOR ID: ', author_id)
        print('AUTHOR NAME: ', message.author.name)
        responses = []

        if message.content == 'REPORT_START':
        # If we don't currently have an active report for this user, add one
            self.reviews[author_id] = Review(self)

        # Only respond to messages if they're part of a reviewing flow
        if author_id not in self.reviews:
            return
        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reviews[author_id].handle_message(message)

        for r in responses:
            await mod_channel.send(r)
        if self.reviews[author_id].banned() or self.reviews[author_id].complete_danger():
            abuser = self.reports[author_id].get_abuser()
            print('WE SHOULD BAN: ', abuser)
            self.banned.add(abuser)

        if self.reviews[author_id].review_complete():
            self.reports.pop(author_id)
            review = self.reviews.pop(author_id)
            self.reviewing = False
    
    def eval_text(self, message):
        ''''
        TODO: Once you know how you want to evaluate messages in your channel, 
        insert your code here! This will primarily be used in Milestone 3. 
        '''
        return message

    
    def code_format(self, text):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return "Evaluated: '" + text+ "'"


client = ModBot()
client.run(discord_token)