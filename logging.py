import sys, time, traceback

class Logger: # {{{1

   # Class constants. {{{2
   LEVEL_ERROR = 0
   LEVEL_WARNING = 1
   LEVEL_INFO = 2
   LEVEL_DEBUG = 3
   LEVEL_ALL = 4

   # Instance properties. {{{2
   logLevel = 4
   fileHandle = sys.stdout
   outputEncoding = 'UTF-8'

   def setLevel(self, level): # {{{2
      """ Set the logging level (messages with a higher level will be omitted). """
      self.logLevel = level

   def setFile(self, filename):  # {{{2
      """ Set the file to which messages will be logged (sys.stdout by default). """
      self.fileHandle = open(filename, 'a')

   def log(self, level, message, *args): # {{{2
      """ Log a formatted message with a custom level. """
      self.__printMessage(level, message % args)

   def debug(self, message, *args): # {{{2
      """ Log a message under the debug logging level. """
      self.__printMessage(self.LEVEL_DEBUG, message % args)

   def info(self, message, *args): # {{{2
      """ Log a message under the info logging level. """
      self.__printMessage(self.LEVEL_INFO, message % args)

   def warning(self, message, *args): # {{{2
      """ Log a message under the warning logging level. """
      self.__printMessage(self.LEVEL_WARNING, message % args)
      self.__printException()

   def error(self, message, *args): # {{{2
      """ Log a message under the error logging level. """
      self.__printMessage(self.LEVEL_ERROR, message % args)
      self.__printException()

   def __printMessage(self, level, message): # {{{2
      if level <= self.logLevel:
         if level == self.LEVEL_ERROR:
            message = 'ERROR ' + message
         elif level == self.LEVEL_WARNING:
            message = 'WARNING ' + message
         elif level == self.LEVEL_INFO:
            message = 'INFO ' + message
         elif level == self.LEVEL_DEBUG:
            message = 'DEBUG ' + message
         if self.fileHandle not in (sys.stdout, sys.stderr):
            message = time.strftime('%Y-%m-%d %H:%M:%S ') + message
         message = message.encode(self.outputEncoding)
         self.fileHandle.write(message + '\n')
         self.fileHandle.flush()

   def __printException(self):
      ei = sys.exc_info()
      if ei != (None, None, None):
         traceback.print_exception(ei[0], ei[1], ei[2], None, self.fileHandle)

# vim: et ts=3 sw=3 fdm=marker
