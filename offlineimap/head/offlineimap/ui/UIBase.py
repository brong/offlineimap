# UI base class
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import offlineimap.version
import re, time, sys, traceback, threading, thread
from StringIO import StringIO

debugtypes = {'imap': 'IMAP protocol debugging',
              'maildir': 'Maildir repository debugging'}

globalui = None
def setglobalui(newui):
    global globalui
    globalui = newui
def getglobalui():
    global globalui
    return globalui

class UIBase:
    def __init__(s, config, verbose = 0):
        s.verbose = verbose
        s.config = config
        s.debuglist = []
        s.debugmessages = {}
        s.debugmsglen = 50
        s.threadaccounts = {}
    
    ################################################## UTILS
    def _msg(s, msg):
        """Generic tool called when no other works."""
        raise NotImplementedError

    def warn(s, msg, minor = 0):
        if minor:
            s._msg("warning: " + msg)
        else:
            s._msg("WARNING: " + msg)

    def registerthread(s, account):
        """Provides a hint to UIs about which account this particular
        thread is processing."""
        if s.threadaccounts.has_key(thread.get_ident()):
            raise ValueError, "Thread already registered (old %s, new %s)" % \
                  (s.getthreadaccount(s), account)
        s.threadaccounts[thread.get_ident()] = account

    def unregisterthread(s, thr):
        """Recognizes a thread has exited."""
        if s.threadaccounts.has_key(thr):
            del s.threadaccounts[thr]

    def getthreadaccount(s):
        if s.threadaccounts.has_key(thread.get_ident()):
            return s.threadaccounts[thread.get_ident()]
        return None

    def debug(s, debugtype, msg):
        thisthread = threading.currentThread()
        if s.debugmessages.has_key(thisthread):
            s.debugmessages[thisthread].append("%s: %s" % (debugtype, msg))
        else:
            s.debugmessages[thisthread] = ["%s: %s" % (debugtype, msg)]

        while len(s.debugmessages[thisthread]) > s.debugmsglen:
            s.debugmessages[thisthread] = s.debugmessages[thisthread][1:]
            
        if debugtype in s.debuglist:
            s._msg("DEBUG[%s]: %s" % (debugtype, msg))

    def add_debug(s, debugtype):
        global debugtypes
        if debugtype in debugtypes:
            if not debugtype in s.debuglist:
                s.debuglist.append(debugtype)
                s.debugging(debugtype)
        else:
            s.invaliddebug(debugtype)

    def debugging(s, debugtype):
        global debugtypes
        s._msg("Now debugging for %s: %s" % (debugtype, debugtypes[debugtype]))

    def invaliddebug(s, debugtype):
        s.warn("Invalid debug type: %s" % debugtype)

    def getnicename(s, object):
        prelimname = str(object.__class__).split('.')[-1]
        # Strip off extra stuff.
        return re.sub('(Folder|Repository)', '', prelimname)

    def isusable(s):
        """Returns true if this UI object is usable in the current
        environment.  For instance, an X GUI would return true if it's
        being run in X with a valid DISPLAY setting, and false otherwise."""
        return 1

    ################################################## INPUT

    def getpass(s, accountname, config, errmsg = None):
        raise NotImplementedError

    def folderlist(s, list):
        return ', '.join(["%s[%s]" % (s.getnicename(x), x.getname()) for x in list])

    ################################################## WARNINGS
    def msgtoreadonly(s, destfolder, uid, content, flags):
        if not (config.has_option('general', 'ignore-readonly') and config.getboolean("general", "ignore-readonly")):
            s.warn("Attempted to synchronize message %d to folder %s[%s], but that folder is read-only.  The message will not be copied to that folder." % \
                   (uid, s.getnicename(destfolder), destfolder.getname()))

    def flagstoreadonly(s, destfolder, uidlist, flags):
        if not (config.has_option('general', 'ignore-readonly') and config.getboolean("general", "ignore-readonly")):
            s.warn("Attempted to modify flags for messages %s in folder %s[%s], but that folder is read-only.  No flags have been modified for that message." % \
                   (str(uidlist), s.getnicename(destfolder), destfolder.getname()))

    def deletereadonly(s, destfolder, uidlist):
        if not (config.has_option('general', 'ignore-readonly') and config.getboolean("general", "ignore-readonly")):
            s.warn("Attempted to delete messages %s in folder %s[%s], but that folder is read-only.  No messages have been deleted in that folder." % \
                   (str(uidlist), s.getnicename(destfolder), destfolder.getname()))

    ################################################## MESSAGES

    def init_banner(s):
        """Called when the UI starts.  Must be called before any other UI
        call except isusable().  Displays the copyright banner.  This is
        where the UI should do its setup -- TK, for instance, would
        create the application window here."""
        if s.verbose >= 0:
            s._msg(offlineimap.version.banner)

    def connecting(s, hostname, port):
        if s.verbose < 0:
            return
        if hostname == None:
            hostname = ''
        if port != None:
            port = ":%d" % port
        displaystr = ' to %s%s.' % (hostname, port)
        if hostname == '' and port == None:
            displaystr = '.'
        s._msg("Establishing connection" + displaystr)

    def acct(s, accountname):
        if s.verbose >= 0:
            s._msg("***** Processing account %s" % accountname)

    def acctdone(s, accountname):
        if s.verbose >= 0:
            s._msg("***** Finished processing account " + accountname)

    def syncfolders(s, srcrepos, destrepos):
        if s.verbose >= 0:
            s._msg("Copying folder structure from %s to %s" % \
                   (s.getnicename(srcrepos), s.getnicename(destrepos)))

    ############################## Folder syncing
    def syncingfolder(s, srcrepos, srcfolder, destrepos, destfolder):
        """Called when a folder sync operation is started."""
        if s.verbose >= 0:
            s._msg("Syncing %s: %s -> %s" % (srcfolder.getname(),
                                             s.getnicename(srcrepos),
                                             s.getnicename(destrepos)))

    def validityproblem(s, folder):
        s.warn("UID validity problem for folder %s; skipping it" % \
               folder.getname())

    def loadmessagelist(s, repos, folder):
        if s.verbose > 0:
            s._msg("Loading message list for %s[%s]" % (s.getnicename(repos),
                                                        folder.getname()))

    def messagelistloaded(s, repos, folder, count):
        if s.verbose > 0:
            s._msg("Message list for %s[%s] loaded: %d messages" % \
                   (s.getnicename(repos), folder.getname(), count))

    ############################## Message syncing

    def syncingmessages(s, sr, sf, dr, df):
        if s.verbose > 0:
            s._msg("Syncing messages %s[%s] -> %s[%s]" % (s.getnicename(sr),
                                                          sf.getname(),
                                                          s.getnicename(dr),
                                                          df.getname()))

    def copyingmessage(s, uid, src, destlist):
        if s.verbose >= 0:
            ds = s.folderlist(destlist)
            s._msg("Copy message %d %s[%s] -> %s" % (uid, s.getnicename(src),
                                                     src.getname(), ds))

    def deletingmessage(s, uid, destlist):
        if s.verbose >= 0:
            ds = s.folderlist(destlist)
            s._msg("Deleting message %d in %s" % (uid, ds))

    def deletingmessages(s, uidlist, destlist):
        if s.verbose >= 0:
            ds = s.folderlist(destlist)
            s._msg("Deleting %d messages (%s) in %s" % \
                   (len(uidlist),
                    ", ".join([str(u) for u in uidlist]),
                    ds))

    def addingflags(s, uid, flags, destlist):
        if s.verbose >= 0:
            ds = s.folderlist(destlist)
            s._msg("Adding flags %s to message %d on %s" % \
                   (", ".join(flags), uid, ds))

    def deletingflags(s, uid, flags, destlist):
        if s.verbose >= 0:
            ds = s.folderlist(destlist)
            s._msg("Deleting flags %s to message %d on %s" % \
                   (", ".join(flags), uid, ds))

    ################################################## Threads

    def getThreadDebugLog(s, thread):
        if s.debugmessages.has_key(thread):
            message = "\nLast %d debug messages logged for %s prior to exception:\n"\
                       % (len(s.debugmessages[thread]), thread.getName())
            message += "\n".join(s.debugmessages[thread])
        else:
            message = "\nNo debug messages were logged for %s." % \
                      thread.getName()
        return message

    def delThreadDebugLog(s, thread):
        if s.debugmessages.has_key(thread):
            del s.debugmessages[thread]

    def getThreadExceptionString(s, thread):
        message = "Thread '%s' terminated with exception:\n%s" % \
                  (thread.getName(), thread.getExitStackTrace())
        message += "\n" + s.getThreadDebugLog(thread)
        return message

    def threadException(s, thread):
        """Called when a thread has terminated with an exception.
        The argument is the ExitNotifyThread that has so terminated."""
        s._msg(s.getThreadExceptionString(thread))
        s.delThreadDebugLog(thread)
        s.terminate(100)

    def getMainExceptionString(s):
        sbuf = StringIO()
        traceback.print_exc(file = sbuf)
        return "Main program terminated with exception:\n" + \
               sbuf.getvalue() + "\n" + \
               s.getThreadDebugLog(threading.currentThread())

    def mainException(s):
        s._msg(s.getMainExceptionString())

    def terminate(s, exitstatus = 0):
        """Called to terminate the application."""
        sys.exit(exitstatus)

    def threadExited(s, thread):
        """Called when a thread has exited normally.  Many UIs will
        just ignore this."""
        s.delThreadDebugLog(thread)
        s.unregisterthread(thread)

    ################################################## Other

    def sleep(s, sleepsecs):
        """This function does not actually output anything, but handles
        the overall sleep, dealing with updates as necessary.  It will,
        however, call sleeping() which DOES output something.

        Returns 0 if timeout expired, 1 if there is a request to cancel
        the timer, and 2 if there is a request to abort the program."""

        abortsleep = 0
        while sleepsecs > 0 and not abortsleep:
            abortsleep = s.sleeping(1, sleepsecs)
            sleepsecs -= 1
        s.sleeping(0, 0)               # Done sleeping.
        return abortsleep

    def sleeping(s, sleepsecs, remainingsecs):
        """Sleep for sleepsecs, remainingsecs to go.
        If sleepsecs is 0, indicates we're done sleeping.

        Return 0 for normal sleep, or 1 to indicate a request
        to sync immediately."""
        s._msg("Next refresh in %d seconds" % remainingsecs)
        if sleepsecs > 0:
            time.sleep(sleepsecs)
        return 0
