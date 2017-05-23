#!/usr/bin/python
# -*- coding: utf-8 -*- 
# @File Name: read_json.py
# @Created:   2017-05-21 13:02:49  seo (simon.seo@nyu.edu) 
# @Updated:   2017-05-22 13:52:54  Simon Seo (simon.seo@nyu.edu)

# -*- coding: utf-8 -*-
"""
Created on Tue Apr 25 12:31:38 2017

@author: song-isong-i
"""

import json
import os
import unicodecsv as csv

#read all the json files in the folder and save the data sorted by posts into csv
def read_profiles(json_dir, csv_dir, output_file_name='posts.csv'):
    print('reading profiles...')
    with open(os.path.join(csv_dir, output_file_name), "wb") as o_posts:
        writer = csv.writer(o_posts, lineterminator='\n') 
        if not os.path.exists(json_dir):
            raise Exception('Please provide directory of profile JSONs')
        for f in os.listdir(json_dir):
            if f != '.DS_Store':
                with open(json_dir+f) as json_data:
                    d = json.load(json_data)
                    sort_by_posts(d, writer)

def sort_by_posts(dic, writer):
    posts = dic['posts']
    threshold = 60*60*24
    max_date = 0 #most recent
    
    #don't save if no post
    if len(posts) == 0: return

    for p in posts:
        date = p['date'] #9
        if date > max_date:
            max_date = date
    max_threshold_date = max_date - threshold
    print("max_date {}, threshold {}, max_threshold_date {}".format(max_date, threshold, max_threshold_date))
    for p in posts:
        date            = p['date'] #9
        if date > max_threshold_date:
            continue

        post = []
        username        = p['username'] #2
        user_id         = p['user_id'] #3
        full_name       = p['full_name'] #4
        profile_pic_url = p['profile_pic_url'] #5
        media_count     = p['media_count'] #6
        follower_count  = p['follower_count'] #7
        pic_url         = str(p['pic_url']) #0
        like_count      = p['like_count'] #1
        comment_count   = p['comment_count'] #8
        date            = p['date'] #9
        caption         = str(p['caption']) #10
        tags            = p['tags'] #11
        post = [pic_url, like_count, username, user_id, full_name, profile_pic_url, media_count, follower_count, comment_count, date, caption, tags]           
        writer.writerow(post)
            

        
        
