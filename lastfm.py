# vim: set fileencoding=utf-8 foldmethod=marker foldlevel=1 :

"""
This module enables you to communicate with the Last.fm web service to find a
user's loved/banned tracks, to find artists similar to a given artist and to
love/ban tracks on behalf of a user. To love/ban tracks you will need your own
API key and secret, which you can get from http://www.last.fm/api/account

Because the functions in this module can be very slow, they print their
progress to standard error. To disable this behavior you can set the module
variable PRINT_PROGRESS to false.
"""

PRINT_PROGRESS = True

import htmlentitydefs
import re
import urllib

if PRINT_PROGRESS:
	import sys

def get_loved_tracks(username): # {{{1
	"""
	Get the loved tracks for the given username from Last.fm. Uses screen
	scraping because the official API only allows you to get the last 50
	loved tracks.
	"""
	return __get_tracks(username, 'loved')

def get_banned_tracks(username): # {{{1
	"""
	Get the banned tracks for the given username from Last.fm. Uses screen
	scraping because the official API only allows you to get the last 50
	banned tracks.
	"""
	return __get_tracks(username, 'banned')

def get_similar_artists(artist, limit=100): # {{{1
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
		artist_key = __normalize_name(artist)
		param = urllib.quote(artist_key != '' and artist_key or artist)
		handle = urllib.urlopen(address % (param, limit))
		lines = handle.read().split("\n")
		handle.close()
		for record in [line.split(",") for line in lines]:
			if len(record) == 3:
				similarity, uuid, similar_artist = record
				similar_artist = __htmlentitydecode(similar_artist)
				similar_key = __normalize_name(similar_artist)
				if similar_artist != '' and similar_artist != artist and \
						(artist_key == '' or similar_key == '' or similar_key != artist_key):
					results.append({ 'similarity': float(similarity), 'uuid': uuid, \
							'name': similar_artist, 'key': similar_key })
		results.sort(lambda x, y: -cmp(x['similarity'], y['similarity']))
	return results

def love_tracks(options, tracks): # {{{1
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
	return __set_tracks(options, tracks, 'love')

def ban_tracks(options, tracks): # {{{1
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
	return __set_tracks(options, tracks, 'ban')

def __get_tracks(username, type): # {{{1
	tracks = []
	address = 'http://www.last.fm/user/%s/library/%s?page=%i'
	regex = '<td[^>]*class="subjectCell"[^>]*>\s*<a[^>]*>(.*?)</a>\s+–\s+<a[^>]*>(.*?)</a>\s*</td>'
	pagenr = 1
	lastpage = None
	while pagenr == 1 and lastpage == None or pagenr <= lastpage:
		if PRINT_PROGRESS:
			sys.stderr.write('\rDownloading page %i of %s with %s tracks' % ( \
					pagenr, lastpage == None and '?' or str(lastpage), type))
		handle = urllib.urlopen(address % (username, type, pagenr))
		source = handle.read()
		handle.close()
		for (artist, track) in re.findall(regex, source, re.IGNORECASE):
			artist = __htmlentitydecode(artist)
			track = __htmlentitydecode(track)
			tracks.append((artist, track))
		if pagenr == 1 and lastpage == None:
			match = re.search('<a\s.*?class="lastpage">(\d+)</a>', source, re.IGNORECASE)
			lastpage = match and int(match.group(1)) or 1
		pagenr += 1
	if PRINT_PROGRESS:
		sys.stderr.write('\rFinished downloading %i %s tracks from Last.fm\n' % ( \
				len(tracks), type))
	return tracks

def __set_tracks(options, tracks, action): # {{{1
	"""
	A private helper method to love and ban tracks, because the code
	involved in doing so is almost exactly the same.
	"""
	# Only import the pylast module when it's needed.
	import pylast
	username = options.get('username')
	password = pylast.md5(options.get('password'))
	api_key = options.get('api_key')
	api_secret = options.get('api_secret')
	generator = pylast.SessionKeyGenerator(api_key, api_secret)
	session_key = generator.get_session_key(username, password)
	failed_tracks = []
	for index, [artist, title] in enumerate(tracks):
		try:
			if PRINT_PROGRESS:
				sys.stderr.write('\r%s track %i of %i' % (
					action == 'love' and 'Loving' or 'Banning', index+1, len(tracks)))
			track = pylast.Track(artist, title, api_key, api_secret, session_key)
			if action == 'love': track.love()
			if action == 'ban': track.ban()
		except:
			failed_tracks.append([artist, title])
	if PRINT_PROGRESS:
		sys.stderr.write('\n')
	return failed_tracks

def __normalize_name(string): # {{{1
	"""
	Normalize the names of artists before querying Last.fm:

	 * strips everything except letters, numbers, dashes and spaces,
	 * trims whitespace from the start & end,
	 * compacts multiple whitespace characters into one space.
	"""
	string = string.lower()
	string = re.sub('[^a-z0-9 -]', '', string)
	string = re.sub('\s+', ' ', string)
	return string

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
