from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    IDENTIFY_TARGET = auto()
    HARASS_TYPE = auto()
    OFFENSIVE_CONTENT_TYPE = auto()
    EMERGENCY = auto()
    DANGER = auto()
    CANCELLED = auto()
    FREQUENCY = auto()
    COORDINATED_PROMPT = auto()
    FINAL_ACTIONS = auto()
    COORDINATED_LOOP = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.data = {}
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.abuser = None
        self.abusive_message = None
    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''
        if message.content == self.CANCEL_KEYWORD:
            self.state = State.CANCELLED
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content) # trying to identify and match message content.
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED
            # self.data['message'] = message
            self.abuser = message.author.name
            self.abusive_message = message.content
            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                    "Please select a category of abuse (enter number): \n(1) Spam/Fraud\n (2) General Offensive Content\n (3) Bullying/Harassment\n (4) Imminent Danger"]
        
        if self.state == State.MESSAGE_IDENTIFIED:
            if re.search('3', message.content):
                self.state = State.IDENTIFY_TARGET
                return ["Who was this abuse target at?\n 'Me' or Other? (if other, please specify username)"]
            if re.search('4', message.content):
                self.state = State.DANGER
                return ["Please specify the type of danger: \n(1) Credible threats to safety\n(2) Encouragement of self-harm"]
            self.state = State.COORDINATED_PROMPT
            reply = 'Separate flow.\n'
            reply += 'Do you suspect this to be part of a coordinated attack? (Y/N)'
            return [reply]
        
        if self.state == State.DANGER:
            if re.search('1', message.content):
                self.data['danger'] = 'Credible threats to safety'
            if re.search('2', message.content):
                self.data['danger'] = 'Encouragement of self-harm'
            self.state = State.EMERGENCY
            self.data['emergency'] = True
            reply = "Thank you for reporting. Our content moderators will review the messages and decide on appropriate action. Please reach out to 911 if this is an emergency. Help is available at 988 (Suicide and Crisis Lifeline)."
            reply += "What further action would you like to pursue? (select all that apply) \n"
            reply += "(1) Block user \n (2) Report to authorities"
            return [reply]

        if self.state == State.IDENTIFY_TARGET:
            if message.content == 'Me':
                self.data['target'] = message.author.name
            else:
                self.data['target'] = message.content
                
            reply = 'Target identified: ' + self.data['target'] + '\n' #TODO validate user in the case where target is other
            reply += "Please select the type of bullying/harassment (enter number): \n"
            reply += " (1) Credible threats to safety \n (2) Targeted Offensive Content \n (3) Encouragement of self-harm \n (4) Extortion (sexual or otherwise)"
            self.state = State.HARASS_TYPE
            return [reply]
        
        if self.state == State.HARASS_TYPE:
            if re.search('2', message.content):
                reply = "Please select type of offensive content: \n"
                reply += '(1) Dehumanizing/derogatory remarks \n (2) Unsolicited Sexual Content \n (3) Violent Content \n (4) Targeted Hate Speech'
                self.state = State.OFFENSIVE_CONTENT_TYPE
                self.data['emergency'] = False
                return [reply]
            self.state = State.EMERGENCY
            self.data['emergency'] = True
            reply = "Thank you for reporting. Our content moderators will review the messages and decide on appropriate action. Please reach out to 911 if this is an emergency. Help is available at 988 (Suicide and Crisis Lifeline)."
            reply += "What further action would you like to pursue? (select all that apply) \n"
            reply += "(1) Block user \n (2) Report to authorities"
            return [reply]
        
        if self.state == State.OFFENSIVE_CONTENT_TYPE:
            if re.search('1', message.content):
                self.data['offensiveType'] = 'Dehumanizing/derogatory remarks'
            elif re.search('2', message.content):
                self.data['offensiveType'] = 'Unsolicited Sexual Content'
            elif re.search('3', message.content):
                self.data['offensiveType'] = 'Violent Content'
            elif re.search('4', message.content):
                self.data['offensiveType'] = 'Targeted Hate Speech'
            self.state = State.FREQUENCY
            return ['Please select the frequency of abuse. \n(1) First time\n(2) Consistent']

        if self.state == State.FREQUENCY:
            if re.search('1', message.content):
                self.data['frequency'] = 'First time'
            if re.search('2', message.content):
                self.data['frequency'] = 'Consistent'
            self.state = State.COORDINATED_PROMPT
            return ['Do you suspect this to be part of a coordinated attack? (Y/N)']
        
        if self.state == State.COORDINATED_PROMPT:
            if re.search('N', message.content):
                self.state = State.FINAL_ACTIONS
                reply = 'Thank you for reporting. Our content moderators will review the message and decide on appropriate action.'
                reply += ' This may include removal of the post or account. Please select any further action you would like to take.\n'
                reply += 'Type 1 for delete message, type 2 for block user, type 12 for both, type anything else for no action.'
                return [reply]
            if re.search('Y', message.content):
                self.state = State.COORDINATED_LOOP
                reply = 'Please list the suspected attackers. Delimit usernames using commas, i.e.: \nuser1,user2,user3'
                return [reply]

        if self.state == State.COORDINATED_LOOP:
            attackers = message.content.split(',')
            self.data['coordinated_attackers'] = attackers
            self.state = State.FINAL_ACTIONS
            reply = 'Thank you for reporting. Our content moderators will review the message and decide on appropriate action.'
            reply += ' This may include removal of the post or account. Please select any further action you would like to take.\n'
            reply += 'Type 1 for delete message, type 2 for block user, type 12 for both, type anything else for no action.'
            return [reply]

        if self.state == State.FINAL_ACTIONS:
            reply = ''
            if re.search('1', message.content):
                self.data['deleteRequested'] = True
                reply += 'The message will be deleted.\n' 
            if re.search('2', message.content):
                self.data['blockRequested'] = True
                reply += 'The user will be blocked.\n'
            if len(reply) != 0:
                reply += 'Report filed. Thank you for your time.'
                self.state = State.REPORT_COMPLETE
                return [reply]
            self.state = State.REPORT_COMPLETE


        if self.state == State.EMERGENCY:
            self.state = State.REPORT_COMPLETE
            if re.search('1', message.content):
                return ['User blocked.']
            else:
                return ['Reported to authorities.']

        if self.state == State.REPORT_COMPLETE:
            return ["Report filed. Thank you for your time."]

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE or self.state == State.CANCELLED
    
    def cancelled(self):
        return self.state == State.CANCELLED

    def get_abuser(self):
        return self.abuser

    def get_abusive_message(self):
        return self.abusive_message
    
    def get_data(self):
        return self.data

    

