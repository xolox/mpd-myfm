#!/usr/bin/env python

import random
import re
import unicodedata

import lastfm
import mpdlibrary

# TODO: make sure the number of songs by an artist does not influence the
#       chance of a song by that artist being chosen.

class Playlist_genrator(object):
    """
    Suplies functions to generate a playlist based on other songs in the playlist.
    """

    def __init__(self, library, lastfm_username=None, logger=None):
        """
        The `library` should be a list of dicts that can be used by mpdlibrary.
        """
        if logger:
            logger.info("Building the Music Player Daemon library index")
        self.library = mpdlibrary.Library(simplify_library(library), options={'filesystem': False})
        self.lastfm_username = lastfm_username
        self.logger = logger
        if lastfm_username:
            if logger:
                logger.info("Scraping last.fm for user's loved and banned tracks")
            self._loved_tracks = self._get_loved_tracks()
            self._banned_tracks = self._get_banned_tracks()
        else:
            self._loved_tracks = []
            self._banned_tracks = []

    def get_next_song(self, playlist):
        """
        Returns a mpdlibrary.Song object for the next song that should be added.
        """
        if not playlist:
            return self.get_random_item('songs')
        playlist = [mpdlibrary.Song(song, self.library) for song in playlist]
        songs = self.get_similar_items('songs', playlist)
        if not songs:
            return self.get_random_item('songs')
        results = []
        for similarity, song in songs:
            if song in self._loved_tracks:
                similarity *= 10
            if not song in playlist and not song in self._banned_tracks:
                results.append((similarity, song))
        return _weighted_random_choice(results)

    def get_next_album(self, playlist):
        """
        Returns an mpdlibrary.Album object for the next album that should be added.
        """
        if not playlist:
            return self.get_random_item('albums')
        albums = self.get_similar_items('albums', playlist)
        if not albums:
            return self.get_random_item('albums')
        return _weighted_random_choice(albums)

    def get_similar_items(self, item_name, playlist):
        """
        Returns a list of mpdlibrary objects from the similar artists `item_name`.

        `item_name` can be: songs, albums or genres.
        """
        if not playlist:
            return None
        for song in playlist:
            if not isinstance(song, mpdlibrary.Song):
                playlist = [song if isinstance(song, mpdlibrary.Song)
                        else mpdlibrary.Song(song, self.library)
                        for song in playlist]
                break
        items = []
        playlist_artists = [song.artist for song in playlist]
        similar_artists = self.get_similar_artists(playlist[-1].artist)
        genre_value = 1
        for artist in similar_artists:
            genre_value = artist.similarity / 2
            if artist in playlist_artists:
                artist.similarity *= 1 / (playlist_artists.index(artist) * 10)
            items.extend((artist.similarity, item) for item in artist.__getattribute__(item_name))
        if not items or len(similar_artists) <= 3:
            items.extend((genre_value, item) for genre in playlist[-1].genre.all()
                    for item in genre.__getattribute__(item_name))
        if not items:
            # Still no similar items found? You got some hipster track right there.
            return self.get_similar_items(item_name, playlist[:-1])
        return items

    def get_random_item(self, item_name):
        return random.choice(list(self.library.__getattribute__(item_name)()))

    def get_similar_artists(self, artist):
        """
        Returns a list of mpdlibrary.Artist objects representing similar
        artists. Only artists found in the library are returned.

        Returns an empty list when no artists could be found.
        """
        results = []
        similar_artists = lastfm.get_similar_artists(artist, logger=self.logger)
        if similar_artists:
            library_artists = list(self.library.artists())
            for lastfm_artist in similar_artists:
                name = simplify_name(lastfm_artist['name'])
                if name in library_artists:
                    similar_artist = mpdlibrary.Artist(name, self.library)
                    similar_artist.similarity = lastfm_artist['similarity']
                    results.append(similar_artist)
        return results

    def _get_loved_tracks(self):
        loved_tracks = lastfm.get_loved_tracks(self.lastfm_username, logger=self.logger)
        return self._lastfm_to_library_tacks(loved_tracks)

    def _get_banned_tracks(self):
        banned_tracks = lastfm.get_banned_tracks(self.lastfm_username, logger=self.logger)
        return self._lastfm_to_library_tacks(banned_tracks)

    def _lastfm_to_library_tacks(self, tracks):
        """
        Takes a list of tracks as they are scraped from lastfm and finds the
        appropriate library songs.
        """
        results = []
        library_artists = list(self.library.artists())
        for track in ((simplify_name(artist), simplify_name(track)) for artist, track in tracks):
            if track[0] in library_artists:
                artist = mpdlibrary.Artist(track[0], self.library)
                for song in artist.songs:
                    if song.title == track[1]:
                        results.append(song)
        return results


def _weighted_random_choice(items):
    """
    Returns one item from the list `items`.
    Items should be tuples where the first value is the weight and the second
    value is the item to return.
    """
    total = 0
    items.sort(reverse=True)
    for item in items:
        total += item[0]
    threshold = random.uniform(0, 0.6) * total
    for item in items:
        threshold -= item[0]
        if threshold <= 0:
            return item[1]

def simplify_library(library):
    for song in library:
        new_song = dict((key, simplify_name(value)) for key, value in song.items() if key != 'file')
        if 'file' in song:
            new_song['file'] = song['file']
        yield new_song

def simplify_name(string):
    """
    Simplify artist names for fuzzy matching.
    """
    if isinstance(string, list):
        return [simplify_name(s) for s in string]
    if isinstance(string, unicode):
        string = unicodedata.normalize('NFKD', string)
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

def simple_compare(left, right):
   """
   Compare two strings using the simplifyname() function and return True when
   they are equal.
   """
   return simplify_name(left) == simplify_name(right)

