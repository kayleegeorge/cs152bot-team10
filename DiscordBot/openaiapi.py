# This is example code using GPT-4 to do a basic classification of a text string
# It is super basic, your milestone 3 should do better than this
# This is a live API key that should be used only for the CS 152 project
# Please do not check the API key into a public GitHub repo or share it with anybody outside of your group

import os
import openai
import json
import sys # for testing

# print(openai.Model.list()) # Can used to verify GPT-4 access

# There should be a file called 'tokens.json' inside the same folder as this file
def detect_harassment(toxic_message):

    token_path = 'tokens.json'
    if not os.path.isfile(token_path):
        raise Exception(f"{token_path} not found!")
    with open(token_path) as f:
        # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
        tokens = json.load(f)
        if not tokens['openai']:
            return None
        openai.organization = tokens['openai']['org']
        openai.api_key = tokens['openai']['key']
        
    response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
    {"role": "system", "content": "You are a content moderation system. A separate pipeline has determined that a particular message is toxic. You are to determine whether the message contains language that targets one of the following topics: race, color, religion, sex, age, disability, national origin."},
    {"role": "user", "content": "I hate you because you are 26 years old."},
    {"role": "assistant", "content": "Yes"},
    {"role": "user", "content": "I hate you"},
    {"role": "assistant", "content": "No"},
    {"role": "user", "content": toxic_message}
    ]
    )
    output = response['choices'][0]['message']['content']
    return output
# print(response)
# s = ''
# for arg in sys.argv[1:]:
#     s += arg
#     s += ' '

# print(detect_harassment(s))