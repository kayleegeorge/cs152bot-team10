from enum import Enum, auto
import discord
import re

class State(Enum):
    REVIEW_START = auto()
    ABUSE_TYPE = auto()
    MESSAGE_IDENTIFIED = auto()
    REVIEW_COMPLETE = auto()
    PROMPT_OFFENSE = auto()
    PROMPT_IN_GENERAL = auto()
    TRUSTWORTHY = auto()
    ZERO_TOLERANCE = auto()
    HARASS_TYPE = auto()
    OFFENSIVE_CONTENT_TYPE = auto()
    IMMINENT_DANGER = auto()
    BAN = auto()
    ANY_SIGNS = auto()
    PROTECTED = auto()

class Review:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.data = {}
        self.state = State.REVIEW_START
        self.client = client
        self.message = None
    
    async def handle_message(self, message):

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REVIEW_COMPLETE
            return ["Review cancelled."]
        
        if self.state == State.REVIEW_START:
            reply =  "Thank you for starting the manual review process.\n"
            self.state = State.ABUSE_TYPE

            reply += "Please select a category of abuse (enter number): \n(1) Harassment/Bullying\n(2) Imminent Danger\n(3) Other"
            return [reply]
        
        if self.state == State.ABUSE_TYPE:
            if re.search('2', message.content):
                self.state = State.REVIEW_COMPLETE
                return ["This message will be reported to authorities."]
            if re.search('1', message.content):
                self.state = State.PROMPT_OFFENSE
                return ["Is this the first offense against the target? Answer Y or N."]
            self.state = State.REVIEW_COMPLETE
            return ["This message will be escalated to the appropriate moderation team."]
        
        if self.state == State.PROMPT_OFFENSE:
            if re.search('Y', message.content):
                self.state = State.PROMPT_IN_GENERAL
                return ["First offense in general? Answer Y or N."]
            if re.search('N',message.content):
                self.state = State.TRUSTWORTHY
                return ["Is the user being reported by trustworthy reporters?"]
            return ["Try again."]
        
        if self.state == State.PROMPT_IN_GENERAL:
            if re.search('Y', message.content):
                self.state = State.ZERO_TOLERANCE
                return ["Does the message contain zero-tolerance language? Answer Y or N."] #TODO this zero tolerance thing
            if re.search('N',message.content):
                self.state = State.TRUSTWORTHY
                return ["Is the user being reported by trustworthy reporters?"]
            return ["Try again."]
        
        if self.state == State.ZERO_TOLERANCE:
            if re.search('Y', message.content):
                self.state = State.BAN
                reply = 'The user will be banned, and we will send a message to the reporter that this action has been taken.\n'
                reply += 'Does the severity of this message warrant escalation?'
                return [reply] 
            if re.search('N',message.content):
                self.state = State.ANY_SIGNS
                return ["Does the message contain any signs of abuse?"]
            return ["Try again."]
        
        if self.state == State.ANY_SIGNS:
            if re.search('Y', message.content):
                self.state = State.PROTECTED
                reply = 'Does the content of the message target protected topics?' #TODO link to protected
                return [reply] 
            if re.search('N',message.content):
                self.state = State.REVIEW_COMPLETE
                return ["No action. We may record the reporter for potential adversarial reporting."]
            return ["Try again."]
        
        if self.state == State.PROTECTED:
            if re.search('Y', message.content):
                self.state = State.BAN
                reply = 'This message will be internally classified as harassment.\n'
                reply += 'The user will be banned, and we will send a message to the reporter that this action has been taken.\n'
                reply += 'Does the severity of this message warrant escalation? (Y/N)'
                return [reply] 
            if re.search('N',message.content):
                self.state = State.REVIEW_COMPLETE
                reply = 'This message will be internally classified as bullying.\n'
                reply += 'We will send the user a warning about this behavior and record this incident onto their account.' #TODO do this too
                return[reply]         
            return ["Try again."]
        
        if self.state == State.TRUSTWORTHY:
            if re.search('Y', message.content):
                self.state = State.BAN
                reply = 'The user will be banned, and we will send a message to the reporter that this action has been taken.\n'
                reply += 'Does the severity of this message warrant escalation? (Y/N)'
                return [reply] 
            if re.search('N',message.content):
                self.state = State.REVIEW_COMPLETE
                return ["No action. We may record the reporter for potential adversarial reporting."]
            return ["Try again."]
        
        if self.state == State.BAN:
            if re.search('Y', message.content):
                self.state = State.REVIEW_COMPLETE
                return ["This message will be escalated to the appropriate moderation team."]
            if re.search('N',message.content):
                self.state = State.REVIEW_COMPLETE
                return ["Done."]
            return ["Try again."]
        

        if self.state == State.REVIEW_COMPLETE:
            return ["Review filed. Thank you for your time."]

    def review_complete(self):
        return self.state == State.REVIEW_COMPLETE
    


    

