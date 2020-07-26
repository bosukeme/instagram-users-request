import re
import requests
from requests_html import HTMLSession

from bs4 import BeautifulSoup
import pandas as pd
import datetime
from pymongo import MongoClient
import time
import pickle

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}



MONGO_URL="mongodb://Bloverse:uaQTRSp6d9czpcCg@64.227.12.212:27017/social_profiling?authSource=admin&readPreference=primary&appname=MongoDB%20Compass&ssl=false"
mongo_url2="mongodb+srv://bloverse:b1XNYDtSQNEv5cAn@bloverse-production.fbt75.mongodb.net/inspirations?retryWrites=true&w=majority"

client= MongoClient(MONGO_URL, connect=False)
db = client.instagram_user

client2= MongoClient(mongo_url2, connect=False)
db2 = client2.inspirations




#entities=['ronaldo', 'microsoft', 'messi', 'dell', 'lampard', 'pfizer', 'chelsea', 'sanofi', 'buhari', 'twitter']


def load_entities():
    
    article_collection = db2.Article

    entities=list(article_collection.find({}, {"_id":0, "entities":1}))
    entities=list((val for dic in entities for val in dic.values()))
    
    entities= [a for b in entities for a in b][:13250] ##return a single list
    print("len chisom: ", len(entities))

    
    return entities

    


def processed_entities():
    print("Starting.... hang in there")
    entities=load_entities()

    entity_df=pd.DataFrame()
    entity_df['entities']=entities
    
    
    processed_entities_collection=db.processed_entity_collection
    processed_entities= list(processed_entities_collection.find({}, {"_id":0, "entities":1}))
    processed_entities=list((val for dic in processed_entities for val in dic.values()))
    
    new_ent=[]
    for entity in entity_df['entities']:
        if entity not in processed_entities:
            processed_entities_collection.insert_one({'entities':entity}) 
            new_ent.append(entity)
            
    entities=list(processed_entities_collection.find({}, {"_id":0, "entities":1}))
    entities=list((val for dic in entities for val in dic.values()))


    print("new entities: ",len(new_ent))
    return new_ent
            

def get_all(new_ent):
    ##edit here later
    handle_every=[]
    name_every=[]
    
    
    for ent in new_ent[:10]:
        try:
            url='https://searchusers.com/search/' + ent #'ukeme'
            print(url)

            session= HTMLSession()
            response=session.get(url)
            users=response.html.find('.timg')
            #print(users)
            all_users=[a.text for a in users]

            all_list=[a.split('\n') for a in all_users]


            handle_list=[item[0].strip('@') for item in all_list][:5]
            
            name_list=[item[1] if len(item)>1 else "nill" for item in all_list][:5]
            
            num_of_likes= get_number_of_likes(handle_list)

            save_entity= [ent for a in range(len(handle_list))]
            
            df= save_as_df(save_entity, handle_list, name_list, num_of_likes)
            print(df)
            save_to_mongodb(df)

        except:
            pass

        #handle_every.append(handle_list)
        #name_every.append(name_list)
        
    #return handle_every, name_every
    
    
def get_number_of_likes(handle_list): 
    
    try:    
       # handle_every=[b for a in handle_every for b in  a]
        num_of_likes=[]
        for j in handle_list:
            
            
            
            try:
                #print(headers)
                #headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
                #headers = {'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/33.0.1750.152 Chrome/33.0.1750.152 Safari/537.36"}
                with requests.Session() as c:
                    url= 'https://searchusers.com/'+ 'user/' + j 
                    
                    search=c.get(url, headers=headers)
                    soup = BeautifulSoup(search.content, 'html.parser')
                    
                    nposts2 = soup.findAll('div',  {'class': 'tallyb'}) ##get where the number of likes is called 
                    
                    nposts2=str(nposts2[1]) ##convert it to a string

                    nposts2= re.findall(r'\d+', nposts2) ##get only the number
                    
                    nposts2=int(''.join(nposts2)) ##convert it to an integer
                    print('....getting likes for....', j)
                    print()

                    num_of_likes.append(nposts2) ##append it to our empty list
            except:
                num_of_likes.append(int(0)) ##append zero for users who locked their accounts
    except:
        pass

    return num_of_likes
        


        

        
def save_as_df(save_entity, handle_list, name_list, num_of_likes):  
    
   # handle_every=[b for a in handle_every for b in  a[:2]]
    
   # name_every=[b for a in name_every for b in  a[:2]]
    
    
    ##save all to a dataframe       
    df=pd.DataFrame()
    df['entities']=save_entity
    df['handle']=handle_list
    df['full name']=name_list
    df['likes_per_post']=num_of_likes

    ##filter by a digit
    df=df[df['likes_per_post']>500]

    #print(df)
    return df


def save_to_mongodb(df):
    
    
    # Load in the instagram_user collection from MongoDB
    instagram_user_collection = db.instagram_user_collection # similarly if 'testCollection' did not already exist, Mongo would create it
    
    cur = instagram_user_collection.find() ##check the number before adding
    print('We had %s instagram_user entries at the start' % cur.count())
    
     ##search for the entities in the processed colection and store it as a list
    instagram_users=list(instagram_user_collection.find({},{ "_id": 0, "handle": 1})) 
    instagram_users=list((val for dic in instagram_users for val in dic.values()))


    #loop throup the handles, and add only new enteries
    for entity, handle, name, likes in df[['entities','handle', 'full names', 'likes_per_post']].itertuples(index=False):
        if handle  not in instagram_users:
            instagram_user_collection.insert_one({"entities":entity, "handle":handle, "full name":name, "likes_per_post":likes}) ####save the df to the collection
    
    
  
    cur = instagram_user_collection.find() ##check the number after adding
    print('We have %s spacy entity entries at the end' % cur.count())
    
    
   
def call_all_func():
    
    #chi_entities=load_entities()
    new_ent=processed_entities()
    #handle_every, name_every= get_all(entities)
    get_all(new_ent)

    #num_of_likes=get_number_of_likes(handle_every)
    #df=save_as_df(handle_every, name_every, num_of_likes)
    #save_to_mongodb(df)
    #df = df.to_json()
    
    print('we are done ')
    
    #return df
    
#call_all_func()
