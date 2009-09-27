# encoding=utf-8

# Standard library modules.
import random
import re

# Local modules.
import lastfm

class MyFM: # {{{1

   lastfm_retries = 3
   album_mode = False
   index = LibraryIndex()

   def __init__(self, logger = None): # {{{2
      # self.index = LibraryIndex()
      self.logger = logger

   def getLovedTracks(self, username): # {{{2
      """
      Get the loved and/or banned tracks by the given user on Last.fm and use
      them to improve the weighted random choice towards the user's favorite
      artists and tracks. Banned tracks are never played.
      """
      self.lovedTracks = []
      self.lovedArtists = []
      self.bannedTracks = []
      for [artist, title] in lastfm.get_loved_tracks(username):
         self.lovedTracks.append(createkey(artist, title))
         key = createkey(artist)
         if artist != 'Various Artists' and key not in self.lovedArtists:
            self.lovedArtists.append(key)
      for [artist, title] in lastfm.get_banned_tracks(username):
         self.bannedTracks.append(createkey(artist, title))

   def getNextTracks(self, playlist): # {{{2
      """
      Pick the next track based on the file(s) currently in the play list. When
      "album mode" is enabled a list of filenames for a whole album is
      returned, otherwise a list with a single filename is returned.
      """
      filenames = []
      track = self.index.findTrackInfo(playlist[-1])
      artists = {}
      if track.get('artist', '') != '':
         self.__findArtistsOnLastFm(track['artist'], artists)
      genres = self.__findArtistsByGenre(track, artists)
      self.__demotePlayedArtists(playlist, artists)
      artist = weightedrandomchoice(artists.items())
      if not self.album_mode or not self.__getNextAlbum(artist, filenames):
         self.__getNextTrack(track, artists, artist, filenames)
      return filenames

   def __findArtistsOnLastFm(self, artist, artists): # {{{2
      """
      Fill a dictionary with similar artists for the given artist from Last.fm.
      The keys of the dictionary are simplified artist names and the values are
      numbers between 0..100 representing the similarity.
      """
      retries = 0
      while retries < self.lastfm_retries:
         try:
            for record in lastfm.get_similar_artists(artist, logger = self.logger):
               if self.index.artistExists(record['name']):
                  artists[simplifyname(record['name'])] = record['similarity']
            break
         except IOError:
            self.logger.warning('Lost connection to Last.fm! Retrying ..')
            retries += 1
      else:
         self.logger.warning('Lost connection to Last.fm %i times in a row!', retries)

   def __findArtistsByGenre(self, track, artists): # {{{2
      """
      Fill a dictionary with similar artists for the given track based on the
      genre of the track (or other tracks by the same artist). The keys of the
      dictionary are simplified artist names and the values are all 1 so that
      artists from Last.fm are preferred over artists based on genre.
      """
      genres = genrelist(track.get('genre', ''))
      # In case the track has an artist field without a genre field, but at
      # least one other track by the same artist does have a genre.
      if track.get('artist', '') != '':
         genres.update(self.index.findGenresForArtist(track['artist']))
      filteredGenres = []
      for genre in genres:
         genreKey = simplifyname(genre)
         if genre != '' and genreKey not in filteredGenres:
            filteredGenres.append(genreKey)
            for artistKey in self.index.findArtistsInGenre(genre):
               if artistKey not in artists:
                  artists[artistKey] = 1
      return filteredGenres

   def __demotePlayedArtists(self, playlist, artists): # {{{2
      """
      Make it less likely that tracks from artists who are already in the play
      list are selected. We don't ban them because that would make it very hard
      to find similar tracks after a while.
      """
      artistsToDemote = []
      for filename in playlist:
         track = self.index.findTrackInfo(filename)
         artistsToDemote.append(simplifyname(track.get('artist', '')))
      numDemoted = 0
      for artistKey, similarity in artists.iteritems():
         if artistKey in artistsToDemote:
            numDemoted += 1
            artists[artistKey] /= 10
      if numDemoted > 0:
         self.logger.debug('Demoted %i artists because they have recently been played.', numDemoted)

   # XXX The above code should work, the code below is garbage. {{{1

   def __getNextTrack(self, track, artists, artist, filenames):
      """
      Pick the next track based on the file(s) currently in the play list.
      """
      # TODO Consider loved tracks from similar artists for random choice
      tracks = []
      for artist in artists:
         tracks.extend(self.index)
      # ^^^ similarTracks = self.__findSimilarTracks(index, artists)
      similarTracks = self.ignorePlayedTracks(client, repeatfactor, similarTracks)
      self.__ignoreBannedTracks(bannedtracks, similarTracks, logger)
      # TODO Make threshold configurable?
      if len(similarTracks) <= 3 and track.get('genre', '') != '':
         logger.info("Adding track based on same genre `%s'.", track['genre'])
         for track in index.findtracksingenre(track['genre']):
            similarTracks.append([1, track])
         similarTracks = self.ignorePlayedTracks(client, repeatfactor, similarTracks)
         self.__ignoreBannedTracks(bannedtracks, similarTracks, logger)
      if len(similarTracks) >= 1:
         self.__markLovedTracks(similarTracks, lovedtracks, lovedartists, logger)
         tracktoadd = weightedrandomchoice(similarTracks)
         client.add(tracktoadd['file'])
         logger.info('Added %s by %s to play list.', tracktoadd.get('title', 'No Title tag'), tracktoadd.get('artist', 'No Artist tag'))
         logger.debug('From file "%s".', tracktoadd['file'])
      else:
         logger.info('Failed to find similar track based on artist nor genre!')

   def __getNextAlbum(self, lastTrack, selectedArtist, fileNames):
      # Similarity sources:
      #  * total / len(tracks)
      selectedTracks = []
      previousGenres = []
      # Create a list of all tracks in all albums by the selected artist.
      for albumName in self.index.findAlbumsByArtist(selectedArtist):
         for track in self.index.findTracksInAlbum(albumName):
            selectedTracks.append([1, track])
      # Try to improve the weights of the selected tracks.
      self.__markLovedTracks(selectedTracks)
      self.__markTracksFromSameGenres(previousGenres, selectedTracks)
      # self.__demotePlayed s/Artists/Tracks/g (playList, similarArtists)
      # Sum the weights of the tracks in each album.
      albums = []
      for weight, trackInfo in selectedTracks:
         albumKey = simplifyname(trackInfo['album'])
         albums[albumKey] = albums.get(albumKey, 0) + weight
      # Pick an album based on the summed weights.
      selectedAlbum = weightedrandomchoice(albums.items())

      # weight: sum of track weights?!
      map(fun, albums)
      similaralbums = findsimilaralbums(index, similarartists)
      if len(similaralbums) <= 1:
         logger.info('Could not find any albums from similar artists, trying one lose track now.')
         logger.info('I will try an album again after that.')
         return False
      albumtoadd = weightedrandomchoice(similaralbums)
      trackstoload = index.findTracksInAlbum(albumtoadd[0], albumtoadd[1])
      logger.info("Adding %i tracks in album `%s' by artist `%s'", len(trackstoload), albumtoadd[1], albumtoadd[0])
      for track in trackstoload:
         client.add(track['file'])
      return True

   def __markTracksFromSameGenres(self, previousGenres, selectedTracks):
      for record in selectedTracks:
         weight, trackInfo = record
         for genreName in genrelist(trackInfo.get('genre', '')):
            genreKey = simplifyname(genreName)
            if genreKey in previousGenres:
               record[0] = weight + weight/5
      pass # TODO!

   def __markLovedTracks(self, selectedTracks):
      """
      Go through the similar tracks and increase the weights of favorite tracks
      and artists.
      """
      numLovedTracks = 0
      numLovedArtists = 0
      for record in selectedTracks:
         similarity, track = record
         if track.get('artist', '') != '' and track.get('title', '') != '' and \
               createkey(track['artist'], track['title']) in self.lovedTracks:
            record[0] = similarity + 25
            numLovedTracks += 1
         elif track.get('artist', '') != '' and \
               createkey(track['artist']) in self.lovedArtists:
            record[0] = similarity + 10
            numLovedArtists += 1
      if numLovedTracks > 0:
         self.logger.debug('Marked %i loved tracks from Last.fm', numLovedTracks)
      if numLovedArtists > 0:
         self.logger.debug('Marked %i tracks by loved artists from Last.fm', numLovedArtists)

   def __ignoreBannedTracks(self, selectedTracks):
      """
      Go through the similar tracks and remove all banned tracks.
      """
      i, numBannedTracks = 0, 0
      while i < len(selectedTracks):
         weight, track = similarTracks[index]
         if track.get('artist', '') != '' and track.get('title', '') != '' and \
               createkey(track['artist'], track['title']) in self.bannedTracks:
            del selectedTracks[i]
            numBannedTracks += 1
         else:
            i += 1
      if numBannedTracks > 0:
         self.logger.debug('Ignored %i banned track(s) from Last.fm', numBannedTracks)

class LibraryIndex:

   # TODO Either __albumsByArtists or __tracksInAlbums is redundant!

   def load(self, tracks):
      self.__tracksByArtists = {}
      self.__artistsInGenres = {}
      self.__albumsByArtists = {}
      self.__infoForFileNames = {}
      for trackInfo in tracks:
         # Save the track info under the filename.
         self.__infoForFileNames[trackInfo['filename']] = track
         # Save the track info under the artist name.
         artistKey = simplifyname(trackInfo.get('artist', ''))
         if artistKey != '':
            if artistKey not in self.__tracksByArtists:
               self.__tracksByArtists[artistKey] = []
            self.__tracksByArtists[artistKey].append(trackInfo)
         # Save the artist name under the track genre(s)?
         genres = genrelist(trackInfo.get('genre', ''))
         if artistKey != '' and genres != []:
            for genreName in genres:
               genreKey = simplifyname(genreName)
               if genreKey not in self.__artistsInGenres:
                  self.__artistsInGenres[genreKey] = []
               if artistKey not in self.__artistsInGenres[genreKey]:
                  self.__artistsInGenres[genreKey].append(artistKey)
         albumKey = simplifyname(trackInfo.get('album', ''))
         if artistKey != '' and albumKey != '':
            # Save the album under the artist name.
            if not self.__albumsByArtists.has_key(artistKey):
               self.__albumsByArtists[artistKey] = {}
            if albumKey not in self.__albumsByArtists[artistKey]:
               self.__albumsByArtists[artistKey][albumKey] = []
            # Save the track under the album name.
            self.__albumsByArtists[artistKey][albumKey].append(trackInfo)

   def artistExists(self, artist):
      return self.__tracksByArtists.has_key(simplifyname(artist))

   def findTrackInfo(self, filename):
      return self.__infoForFileNames.get(filename, {})

   def findTracksByArtist(self, artist):
      artistKey = simplifyname(artist)
      return self.__tracksByArtists.get(artistKey, [])

   def findArtistsInGenre(self, genre):
      return self.__artistsInGenres.get(simplifyname(genre), [])

   def findGenresForArtist(self, artist):
      genres = {}
      for track in self.findTracksByArtist(artist):
         for genre in genrelist(track.get('genre', '')):
            genres[simplifyname(genre)] = genre
      return genres.values()

   def findAlbumsByArtist(self, artist):
      artistKey = simplifyname(artist)
      return self.__albumsByArtists.get(artistKey, {}).keys()

   def findTracksInAlbum(self, artist, albumName):
      artistKey = simplifyname(artist)
      albumKey = simplifyname(albumName)
      albums = self.__albumsByArtists.get(artistKey, {})
      tracks = albums.get(albumKey, [])
      tracks.sort(self.__sortAlbumTracks)
      return tracks

   def __sortAlbumTracks(self, x, y):
      return cmp(self.__getTrackNr(x), self.__getTrackNr(y))

   # FIXME This is MPD specific -- make ['track'] an integer instead.

   def __getTrackNr(self, track):
      if track.get('track', '') != '':
         match = re.match('^\d+', track['track'])
         return int(match.group())
      return 0

# Miscellaneous functions. {{{1

def createkey(*args):
   """ Simplify a list of strings (one or more of artist name, album name,
   track title) into a single string using the simplifyname() function. """
   return '-'.join(map(simplifyname, args))

# TODO Rename simplifyname() to simplify().
# FIXME Don't strip Unicode characters!

def simplifyname(string):
   """
   simplifyname artist names for fuzzy matching.
   """
   global _cachednames
   if _cachednames.has_key(string):
      return _cachednames[string]
   else:
      result = string.lower()
      result = re.sub('^the\s+', '', result)
      result = re.sub(',\s+the$', '', result)
      result = re.sub('[^a-z0-9 -]', '', result)
      result = re.sub('\s+', ' ', result)
      _cachednames[string] = result
      return result

_cachednames = {}

def simplecompare(left, right):
   """
   Compare two strings using the simplifyname() function and return True when
   they are equal.
   """
   return simplifyname(left) == simplifyname(right)

def weightedrandomchoice(items):
   """
   Pick a weighted random value from a list of lists, where each list contains
   a numeric weight followed by any type of associated value.
   """
   total = 0
   random.shuffle(items)
   for item in items:
      total += item[1]
   threshold = random.uniform(0, 0.9) * total
   for item in items:
      threshold -= item[1]
      if threshold <= 0:
         return item[0]

def unique(list):
    result = []
    for item in list:
        if item not in result:
            result.append(item)
    return result

def genrelist(value):
   list = isinstance(value, str) and [value] or value
   return filter(lambda s: len(s) != 0, list)

# }}}1

if __name__ == '__main__':
   artist = 'Justus Köhncke'
   album = 'Safe and Sound'
   print 'simplifyname(%s) = %s' % (str(artist), simplifyname(artist))
   print 'createkey(%s, %s) = %s' % (str(artist), str(album), createkey(artist, album))

# vim: et ts=3 sw=3 fdm=marker
