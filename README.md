# Instagram Hashtag Crawler
This crawler was made because most of the crawlers out there seems to either require a browser or a developer account. This Instagram crawler utilizes a private API of Instagram and thus no developer account is required.

Refer to a similar script I wrote. It might be more helpful in terms of documentation: [simonseo/instacrawler-privateapi](https://github.com/simonseo/instagram-hashtag-crawler)

## Installation
First install [Instagram Private API](https://github.com/ping/instagram_private_api). Kudos for a great project!
```
$ pip install git+https://github.com/ping/instagram_private_api.git
```

Now run `__init__.py`. It'll provide you with the command options. If this shows up, everything probably works
```
$ python __init__.py
usage: __init__.py [-h] -u USERNAME -p PASSWORD [-f TARGETFILE] [-t TARGET]
```

## Get Crawlin'
To get crawlin', you need to provide your Instagram username and password, and either an Instagram Hashtag without the hash (target) or a text file of the hashtags in each row (targetfile).
Wait a bit and a folder will be made with all the hashtags crawled.

## Options
Inside `__init__.py`, there is a config dictionary. Each config option is explained in the comments.
Note that `min_collect_media` and `max_collect_media` is trumped if `min_timestamp` is provided as a number.
```
config = {
	'profile_path' : './hashtags',                          # Path where output data gets saved
	'min_collect_media' : 1,                                # how many media items to be collected per hashtag. If time is specified, this is ignored
	'max_collect_media' : 2000,                             # how many media items to be collected per hashtag. If time is specified, this is ignored
	# 'min_timestamp' : int(time() - 60*60*24*30*2)           # up to how recent you want the posts to be in seconds. If you do not want to use this, put None as value
	'min_timestamp' : None
}
```
