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
from openaiapi import *
from perspective import *

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

       
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD): 
             # If not an active reporting flow, evaluate the message and send score to mod channel
            mod_channel = self.mod_channels[message.guild.id]
            scores = self.eval_text(message.content)
            await mod_channel.send(self.code_format(message.content, scores))

            # calculate bullying vs. banter
            if scores['toxicity'] > 0.5:
                calculating_msg = await mod_channel.send('Calculating bullying vs. banter likelihood...')
                await mod_channel.send(await self.banter_or_bully(message, 10))
                await calculating_msg.edit(content="Bullying vs. banter report completed!")
            return

        # Only respond to messages if they're part of a reporting flow
        
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
            if self.reports[author_id].cancelled():
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
        author_name = message.author.name
        # print('AUTHOR ID: ', author_id)
        # print('AUTHOR NAME: ', author_name)
        responses = []
        
        if message.content == 'adversaries':
            reply = 'Dictionary of adversarial reportings:\n' + str(self.adversary_counts)
            await mod_channel.send(reply)
            return
        
        if message.content == 'warnings':
            reply = 'Dictionary of warnings:\n' + str(self.warnings)
            await mod_channel.send(reply)
            return

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
            # print('WE SHOULD BAN: ', abuser)
            self.banned.add(abuser)

        if self.reviews[author_id].adversarial():
            # print('THIS AUTHOR IS ADVERSARIAL: ', author_id)
            self.adversary_counts[author_name] += 1
            # print("NEW MAPPY: ", self.adversary_counts)

        if self.reviews[author_id].warning():
            abuser = self.reports[author_id].get_abuser()
            self.warnings[abuser] += 1

        if self.reviews[author_id].review_complete():
            self.reports.pop(author_id)
            review = self.reviews.pop(author_id)
            self.reviewing = False
    
    def eval_text(self, message):
        ''''
        TODO: Once you know how you want to evaluate messages in your channel, 
        insert your code here! This will primarily be used in Milestone 3. 
        '''
        scores = {}
        probabilities = get_toxicity_probability(message)
        if not probabilities:
            return
        scores = probabilities
        if probabilities['toxicity'] > .5: # measuring toxicity category
            harassment = detect_harassment(message)
            scores['Harassment'] = harassment

        return scores

    
    def code_format(self, message, scores):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        reply = "Evaluated: '" + message + "'\n"
        reply += "Scores: " + str(scores)
        return reply

    async def banter_or_bully(self, message, num_last_messages):
        # get last n messages
        messages = [message async for message in message.channel.history(limit=num_last_messages)]
        messages.reverse()
        print(message.channel.history(limit=num_last_messages))
        
        # avg toxicity score across messages
        avg_aggression = {}
        for message in messages:
            perspective_scores = self.eval_text(message.content)
            author = message.author.name # alias of user who sent msg

            if author not in avg_aggression:
                avg_aggression[author] = { 'num_msgs': 0, 'toxicity_avg': 0, 'num_identity_attack': 0, 'num_threat': 0 }
            
            avg_aggression[author]['num_msgs'] += 1 # track num messages
            avg_aggression[author]['toxicity_avg'] += perspective_scores['toxicity'] # track toxicity

            # track 'more severe' message categories: threat or identity attack
            if perspective_scores['identity_attack'] > 0.5:
                avg_aggression[author]['num_identity_attack'] += 1
            if perspective_scores['threat'] > 0.5:
                avg_aggression[author]['num_threat'] += 1 

        # average scores across messages
        for author in avg_aggression:
            avg_aggression[author]['toxicity_avg'] /= avg_aggression[author]['num_msgs']

        # format metrics

        # TODO: add final outcome of whether this is bullying or banter:
        # - if one user has much higher toxicity score
        # - if one user has more threats/identity attacks
        
        return self.format_banter_or_bully(avg_aggression)
    
    def format_banter_or_bully(self, avg_aggression):
        reply = ""
        for author in avg_aggression:
            toxicity_avg = avg_aggression[author]['toxicity_avg']
            num_msgs = avg_aggression[author]['num_msgs']
            severe_msgs = avg_aggression[author]['num_identity_attack'] + avg_aggression[author]['num_threat'] 
            reply += f'User {author} had an average toxicity score of {toxicity_avg} and {severe_msgs} threats/identity attacks over the last {num_msgs} messages \n'
        return reply
    
client = ModBot()
client.run(discord_token)