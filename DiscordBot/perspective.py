from googleapiclient import discovery
import json
import os
import sys

api_key = None

def get_toxicity_probability(message):
    
    token_path = 'tokens.json'
    if not os.path.isfile(token_path):
        raise Exception(f"{token_path} not found!")
    with open(token_path) as f:
        # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
        tokens = json.load(f)
        if not tokens['perspective']:
            return None
        api_key = tokens['perspective']

    client = discovery.build(
    "commentanalyzer",
    "v1alpha1",
    developerKey=api_key,
    discoveryServiceUrl="https://commentanalyzer.googleapis.com/$discovery/rest?version=v1alpha1",
    static_discovery=False,
    )

    analyze_request = {
    'comment': { 'text': message},
    'requestedAttributes': {'TOXICITY': {}, 'SEVERE_TOXICITY': {}, 'IDENTITY_ATTACK': {}, 'INSULT': {}, 'PROFANITY':{}, 'THREAT': {} }
    }

    response = client.comments().analyze(body=analyze_request).execute()
    # print(json.dumps(response, indent=2))
    # print(response['attributeScores']['TOXICITY']['spanScores'][0]['score']['value'])
    return { "toxicity": response['attributeScores']['TOXICITY']['spanScores'][0]['score']['value'], # toxicity probability
             "severe_toxicity": response['attributeScores']['SEVERE_TOXICITY']['spanScores'][0]['score']['value'],
             "identity_attack": response['attributeScores']['IDENTITY_ATTACK']['spanScores'][0]['score']['value'],
             "insult": response['attributeScores']['INSULT']['spanScores'][0]['score']['value'],
             "profanity": response['attributeScores']['PROFANITY']['spanScores'][0]['score']['value'],
             "threat": response['attributeScores']['THREAT']['spanScores'][0]['score']['value'] }

# s = ''
# for arg in sys.argv[1:]:
#     s += arg
#     s += ' '
# print(get_toxicity_probability(s))