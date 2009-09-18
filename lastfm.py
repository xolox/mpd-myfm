# vim: et ts=3 sw=3 fdm=marker fdl=1 encoding=utf-8

"""
This module enables you to communicate with the Last.fm web service to find a
user's loved/banned tracks, to find artists similar to a given artist and to
love/ban tracks on behalf of a user. To love/ban tracks you will need your own
API key and secret, which you can get from http://www.last.fm/api/account
"""

# TODO Cache failure to love or ban

CACHE_DIRECTORY = '/tmp/lastfm.py'
SECONDS_BETWEEN_REQUESTS = 2
__LAST_REQUEST_TIME = 0

import htmlentitydefs
import os
import re
import time
import urllib

if not os.path.isdir(CACHE_DIRECTORY):
   os.mkdir(CACHE_DIRECTORY)

def get_loved_tracks(username, logger=None): # {{{1
   """
   Get the loved tracks for the given username from Last.fm. Uses screen
   scraping because the official API only allows you to get the last 50
   loved tracks.
   """
   return __get_tracks(username, 'loved', logger)

def get_banned_tracks(username, logger=None): # {{{1
   """
   Get the banned tracks for the given username from Last.fm. Uses screen
   scraping because the official API only allows you to get the last 50
   banned tracks.
   """
   return __get_tracks(username, 'banned', logger)

def get_similar_artists(artist, limit=100, logger=None): # {{{1
   """
   Get a list of artists similar to the given artist from Last.fm. Returns
   a list of dictionaries, where each dictionary contains the following
   fields:

    * "similarity": a number between 0 and 100,
    * "uuid": the universally unique identifier for artist,
    * "name": the name of the artist,
    * "key": the simplified name.

   The list is sorted from most to least similar artist.
   """
   address = 'http://ws.audioscrobbler.com/2.0/artist/%s/similar.txt?limit=%i'
   results = []
   if artist != '':
      artist_key = normalize_name(artist)
      param = urllib.quote(artist_key.encode('UTF-8'))
      __sleep(logger=logger)
      if logger:
         logger.debug("Searching for normalized artist name `%s' (original: `%s')", artist_key, artist)
      handle = urllib.urlopen(address % (param, limit))
      lines = handle.read().decode('utf-8').split('\n')
      handle.close()
      for record in [line.split(",") for line in lines]:
         if len(record) == 3:
            similarity, uuid, similar_artist = record
            similar_artist = __htmlentitydecode(similar_artist)
            similar_key = normalize_name(similar_artist)
            if similar_key != artist_key:
               results.append({ 'similarity': float(similarity), 'uuid': uuid, \
                     'name': similar_artist, 'key': similar_key })
      results.sort(lambda x, y: -cmp(x['similarity'], y['similarity']))
   return results

def love_tracks(options, tracks, logger=None): # {{{1
   """
   Love the given track(s) on Last.fm for the given user. The options
   argument should be a dictionary with the following fields:

    * "username": username of Last.fm account,
    * "password": password for Last.fm account,
    * "api_key": API key provided to you by Last.fm,
    * "api_secret": API secret provided to you by Last.fm.

   The tracks argument should be a list of tracks, where each track is a
   list containing two strings, the artist name and the track title. The
   result is a list like the tracks argument, with the tracks which
   failed.
   """
   return __set_tracks(options, tracks, 'love', logger)

def ban_tracks(options, tracks, logger=None): # {{{1
   """
   Ban the given track(s) on Last.fm for the given user. The options
   argument should be a dictionary with the following fields:

    * "username": username of Last.fm account,
    * "password": password for Last.fm account,
    * "api_key": API key provided to you by Last.fm,
    * "api_secret": API secret provided to you by Last.fm.

   The tracks argument should be a list of tracks, where each track is a
   list containing two strings, the artist name and the track title. The
   result is a list like the tracks argument, with the tracks which
   failed.
   """
   return __set_tracks(options, tracks, 'ban', logger)

def __get_tracks(username, type, logger): # {{{1
   # Return cached results when they exist.
   cachefile = __cached_tracks_fname(username, type)
   if os.path.exists(cachefile):
      if logger:
        logger.info('Returning cached %s tracks from %s', type, cachefile)
      handle = open(cachefile, 'r')
      tracks = eval(handle.read())
      handle.close()
      return tracks
   # Otherwise get results from Last.fm.
   tracks = []
   address = 'http://www.last.fm/user/%s/library/%s?page=%i'
   pattern = '<td class="subjectCell">\s*<a href="[^"]+">(.+?)</a>.+?<a href="[^"]+">(.+?)</a>\s*</td>'
   pagenr = 1
   lastpage = None
   while lastpage == None or pagenr <= lastpage:
      __sleep()
      if logger:
         logger.debug('Downloading page %i of %s with %s tracks',
               pagenr, lastpage == None and '?' or str(lastpage), type)
      handle = urllib.urlopen(address % (username, type, pagenr))
      source = handle.read().decode('utf-8')
      handle.close()
      for (artist, track) in re.findall(pattern, source, re.DOTALL | re.IGNORECASE):
         tracks.append((__htmlentitydecode(artist), __htmlentitydecode(track)))
      if pagenr == 1 and lastpage == None:
         match = re.search('<a\s.*?class="lastpage">(\d+)</a>', source, re.IGNORECASE)
         lastpage = match and int(match.group(1)) or 1
      pagenr += 1
   if logger:
      logger.info('Finished downloading %i %s tracks from Last.fm', len(tracks), type)
   # Cache results before returning them.
   handle = open(cachefile, 'w')
   handle.write(str(tracks))
   handle.close()
   return tracks

def __set_tracks(options, tracks, action, logger): # {{{1
   """
   A private helper method to love and ban tracks, because the code
   involved in doing so is almost exactly the same.
   """
   # Only import the pylast module when it's needed.
   import pylast
   # Unpack the options dictionary.
   username = options.get('username')
   password = pylast.md5(options.get('password'))
   api_key = options.get('api_key')
   api_secret = options.get('api_secret')
   # Create a Last.fm session key.
   generator = pylast.SessionKeyGenerator(api_key, api_secret)
   session_key = generator.get_session_key(username, password)
   # Read the list of tracks that previously failed to get loved or banned?
   cachefile = __cached_failures_fname(username, action)
   previous_failures = []
   if os.path.exists(cachefile):
      handle = open(cachefile, 'r')
      previous_failures = eval(handle.read())
   # Love or ban the given tracks.
   failed_tracks = []
   cache_dirty = False
   for index, [artist, title] in enumerate(tracks):
      try:
         # Don't retry previously failed tracks.
         if (artist, title) not in previous_failures:
            if logger:
               logger.info('%s track %i of %i\n',
                  action == 'love' and 'Loving' or 'Banning', index+1, len(tracks))
            __sleep()
            track = pylast.Track(artist, title, api_key, api_secret, session_key)
            if action == 'love': track.love()
            elif action == 'ban': track.ban()
            cache_dirty = True
      except:
         failed_tracks.append([artist, title])
   # Delete the cached tracks because the cache is stale?
   if cache_dirty:
      cachefile = __cached_tracks_fname(username, action == 'love' and 'loved' or 'banned')
      if os.path.exists(cachefile): os.remove(cachefile)
   # Cache the tracks that failed?
   if len(failed_tracks) != 0:
      cachefile = __cached_failures_fname(username, action)
      handle = open(cachefile, 'w')
      handle.write(str(previous_failures + failed_tracks))
      handle.close()
   # Return the list of tracks that failed.
   return failed_tracks

def normalize_name(string): # {{{1
   """
   Normalize the names of artists before querying Last.fm.
   """
   lower = string.lower()
   ascii = re.sub(NON_WORD_PATTERN, ' ', lower)
   if ascii == '': ascii = lower
   return re.sub('\s+', ' ', ascii).strip()

NON_WORD_PATTERN = re.compile('\W+', re.UNICODE)

def __sleep(logger=None): # {{{1
   """
   Use time.sleep() to enforce a reasonable time
   between requests to the Last.fm web services.
   """
   global __LAST_REQUEST_TIME
   elapsed = time.time() - __LAST_REQUEST_TIME
   if elapsed < SECONDS_BETWEEN_REQUESTS:
      seconds = SECONDS_BETWEEN_REQUESTS - elapsed
      if logger:
         logger.debug('Sleeping for %.2f seconds before making a request', seconds)
      time.sleep(seconds)
   __LAST_REQUEST_TIME = time.time()

def __cached_tracks_fname(username, type): # {{{1
   return '%s/%s by %s' % (CACHE_DIRECTORY, type, username)

def __cached_failures_fname(username, action): # {{{1
   return '%s/failed to %s for %s' % (CACHE_DIRECTORY, action, username)

def __htmlentitydecode(string): # {{{1
   """ Replace HTML entities with the characters they represent. """
   return __pattern.subn(__htmlentitydecode_helper, string)[0]

# Compile the regular expression only once.
__pattern = re.compile("&(#?)(\d{1,5}|\w{1,8});")

def __htmlentitydecode_helper(match): # {{{1
   ent = match.group(2)
   if match.group(1) == '#':
      return unichr(int(ent))
   else:
      cp = htmlentitydefs.name2codepoint.get(ent)
      return cp and unichr(cp) or match.group()
