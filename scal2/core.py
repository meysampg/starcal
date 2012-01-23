# -*- coding: utf-8 -*-
#
# Copyright (C) 2009-2011 Saeed Rasooli <saeed.gnu@gmail.com> (ilius)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, 
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program. If not, see <http://www.gnu.org/licenses/gpl.txt>.
# Also avalable in /usr/share/common-licenses/GPL on Debian systems
# or /usr/share/licenses/common/GPL3/license.txt on ArchLinux

import time
#print time.time(), __file__ ## FIXME
from time import localtime
import sys, os, subprocess, traceback
from StringIO import StringIO
from os.path import isfile, isdir, exists, dirname, join, split, splitext


from scal2.paths import *
from scal2.locale_man import * ## prepareLanguage, loadTranslator, getMonthName
from scal2.plugin_man import *
from scal2.time_utils import *
from scal2.os_utils import *
from scal2.json_utils import *
from scal2.utils import cmpVersion


try:
    __file__
except NameError:
    import inspect, scal2
    __file__ = join(dirname(inspect.getfile(scal2)), 'core.py')


VERSION = '1.9.4'
APP_NAME = 'starcal2'
COMMAND = 'starcal2'
homePage = 'http://starcal.sourceforge.net/'
primaryMode = 0 ## suitable place ???????????
osName = getOsName()
################################################################################

if exists(confDir):
    if not isdir(confDir):
        os.rename(confDir, confDir+'-old')
        os.mkdir(confDir)
        os.rename(confDir+'-old', confPath)
else:
    os.mkdir(confDir)


try:
    os.mkdir(plugConfDir)
except:
    pass

try:
    os.mkdir(join(confDir, 'log'))
except:
    pass

################################################################################

try:
    import logging
    import logging.config

    logConfText = open(join(rootDir, 'conf', 'logging-user.conf')).read()
    for varName in ('confDir',):
        logConfText = logConfText.replace(varName, eval(varName))

    logging.config.fileConfig(StringIO(logConfText))
    log = logging.getLogger('starcal2')
except:
    from scal2.utils import FallbackLogger
    log = FallbackLogger()

def myRaise(File=None):
    i = sys.exc_info()
    (typ, value, tback) = sys.exc_info()
    text = 'line %s: %s: %s\n'%(tback.tb_lineno, typ.__name__, value)
    if File:
        text = 'File "%s", '%File + text
    log.error(text)

def myRaiseTback(f=None):
    (typ, value, tback) = sys.exc_info()
    log.error("".join(traceback.format_exception(typ, value, tback)))

from scal2.cal_modules import modules, moduleNames, modNum, jd_to, to_jd, convert, DATE_GREG


################################################################################
####################### class and function defenitions #########################
################################################################################

popen_output = lambda cmd: subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]

to_jd_primary = lambda y, m, d: modules[primaryMode].to_jd(y, m, d)

def getCurrentJd():## time() and mktime(localtime()) both return GMT, not local
    (y, m, d) = localtime()[:3]
    return to_jd(y, m, d, DATE_GREG)

getEpochFromDate = lambda y, m, d, mode: getEpochFromJd(to_jd(y, m, d, mode))

def getWeekDateHmsFromEpoch(epoch):
   (jd, hour, minute, sec) = getJhmsFromEpoch(epoch)
   (absWeekNumber, weekDay) = getWeekDateFromJd(jd)
   return (absWeekNumber, weekDay, hour, minute, sec)

def getJdListFromEpochRange(startEpoch, endEpoch):
    startJd = getJdFromEpoch(startEpoch)
    endJd = getJdFromEpoch(endEpoch-0.01) + 1
    return range(startJd, endJd)

def getJdRangeForMonth(year, month, mode):
    day = getMonthLen(year, month, mode)
    return (to_jd(year, month, 1, mode),
            to_jd(year, month, day, mode) + 1)




## jwday: Calculate day of week from Julian day
## 0 = Sunday
## 1 = Monday
jwday = lambda jd: (jd + 1) % 7

getWeekDay = lambda y, m, d: jwday(to_jd(y, m, d, primaryMode)-firstWeekDay)

getWeekDayN = lambda i: weekDayName[(i+firstWeekDay)%7]
## 0 <= i < 7    (0 = first day)
def getWeekDayAuto(i, abr=False):
    if abr:
        return weekDayNameAb[(i+firstWeekDay)%7]
    else:
        return weekDayName[(i+firstWeekDay)%7]
        

datesDiff=lambda y1,m1,d1,y2,m2,d2: to_jd(y2,m2,d2,primaryMode)\
    - to_jd(y1,m1,d1,primaryMode)

dayOfYear=lambda y, m, d: datesDiff(y, 1, 1, y, m, d)+1
        
def getLocaleFirstWeekDay():
    #log.debug('first_weekday', popen_output(['locale', 'first_weekday']))
    return int(popen_output(['locale', 'first_weekday']))-1
    #return int(popen_output('LANG=%s locale first_weekday'%lang))-1
    ##retrun int(trans('calendar:week_start:0').split(':')[-1]) 
    ## "trans" must read from gtk-2.0.mo !!
        
        
## week number in year
def getWeekNumber(year, month, day, adjustZero=True):
    jd = to_jd(year, month, day, primaryMode)
    jd0 = to_jd(year, 1, 1, primaryMode)
    first = jwday(jd-firstWeekDay) - 1
    if weekNumberMode==7:
        weekNumber = (jd - jd0 + first%7) / 7 + 1
    else:
        weekNumber = (jd - jd0 + first%7) / 7 + (first < weekNumberMode-firstWeekDay)
        if adjustZero and weekNumber==0:
            weekNumber = getWeekNumber(*jd_to(jd-7, primaryMode)) + 1
    return weekNumber

def getJdFromWeek(year, weekNumber):## FIXME
    ## weekDay == 0
    wd0 = getWeekDay(year, 1, 1) - 1
    wn0 = getWeekNumber(year, 1, 1, False)
    jd0 = to_jd(year, 1, 1, primaryMode)
    return jd0 - wd0 + (weekNumber-wn0)*7
    

getWeekDateFromJd = lambda jd: divmod(jd - firstWeekDay + 1, 7)
## return (absWeekNumber, weekDay)

getAbsWeekNumberFromJd = lambda jd: getWeekDateFromJd(jd)[0]

getStartJdOfAbsWeekNumber = lambda absWeekNumber: absWeekNumber*7 + firstWeekDay - 1
def getJdRangeOfAbsWeekNumber(absWeekNumber):
    jd = getStartJdOfAbsWeekNumber(absWeekNumber)
    return (jd, jd+7)


getMonthLen = lambda year, month, mode: modules[mode].getMonthLen(year, month)

def getNextMonth(year, month):
    assert month <= 12
    if month==12:
        return (year+1, 1)
    else:
        return (year, month+1)

def getPrevMonth(year, month):
    assert month >= 1
    if month==1:
        return (year-1, 12)
    else:
        return (year, month-1)
        

def getLocaleWeekNumberMode():##????????????
    return (int(popen_output(['locale', 'week-1stweek']))-1)%8
    ## will be 7 for farsi (OK)
    ## will be 6 for english (usa) (NOT OK, must be 4)
    #return int(popen_output('LANG=%s locale first_weekday'%lang))-1
    ## locale week-1stweek:
    ##    en_US.UTF-8             7
    ##    en_GB.UTF-8             4
    ##    fa_IR.UTF-8             0




def validatePlugList():
    global allPlugList, plugIndex
    n = len(allPlugList)
    i = 0
    while i<n:
        if allPlugList[i]==None:
            allPlugList.pop(i)
            n -= 1
            try:
                plugIndex.remove(i)
            except ValueError:
                pass
        else:
            i += 1
    #####
    n = len(allPlugList)
    m = len(plugIndex)
    i = 0
    while i<m:
        if plugIndex[i]<n:
            i += 1
        else:
            plugIndex.pop(i)
            m -= 1

def loadAllPlugins():
    #log.debug('----------------------- loadAllPlugins')
    global allPlugList, plugIndex
    #exec(open(userPlugConf).read())## FIXME
    ## Assert that user configuarion for plugins is OK
    validatePlugList()
    ########################
    names = [split(plug.path)[1] for plug in allPlugList]
    ##newPlugs = []#????????
    for direc in (plugDir, plugDirUser):
        if not isdir(direc):
            continue
        for fname in os.listdir(direc):
            if fname=='__init__.py' or fname in names:##??????????
                continue 
            path = '%s/%s'%(direc, fname)
            name = splitext(fname)[0]
            #if path in paths:# The plugin is not new, currently exists in allPlugList
                #log.warning('plugin "%s" already exists.'%path)
                #continue
            if not isfile(path):
                continue
            plug = loadPlugin(path)
            if plug==None:
                continue
            #try:
            plugIndex.append(len(allPlugList))
            allPlugList.append(plug)
            #except:
            #    myRaise(__file__)
    ## Assert again that final plugins are OK
    validatePlugList()

def getHolidayPlugins():
    hPlugs = []
    for i in plugIndex:
        plug = allPlugList[i]
        if hasattr(plug, 'holidays'):
            hPlugs.append(plug)
    return hPlugs

def updatePlugins():
    for i in plugIndex:
        plug = allPlugList[i]
        if plug.enable:
            plug.load()
        else:
            plug.clear()


def getPluginsTable():## returns a list of (i, enable, show_date, description)
    table = []
    for i in plugIndex:
        plug = allPlugList[i]
        table.append([i, plug.enable, plug.show_date, plug.desc])
    return table


def getDeletedPluginsTable():## returns a list of (i, description)
    table = []
    for (i, plug) in enumerate(allPlugList):
        try:
            plugIndex.index(i)
        except ValueError:
            table.append((i, plug.desc))
    return table

getAllPlugListRepr = lambda: '[\n' + '\n'.join(['  %r,'%plug for plug in allPlugList]) + '\n]'


#########################################################


def ymdRange((y1, m1, d1), (y2, m2, d2), mode=None):
    if y1==y2 and m1==m2:
        return [(y1, m1, d) for d in range(d1, d2)]
    if mode==None:
        mode=DATE_GREG
    j1 = int(to_jd(y1, m1, d1, mode))
    j2 = int(to_jd(y2, m2, d2, mode))
    l = []
    for j in range(j1, j2):
        l.append(jd_to(j, mode))
    return l

def urlToPath(url):
    if len(url)<7:
        return url
    if url[:7]!='file://':
        return url
    path=url[7:]
    if path[-2:]=='\r\n':
        path=path[:-2]
    elif path[-1]=='\r':
        path=path[:-1]
    ## here convert html unicode symbols to utf8 string:
    if not '%' in path:
        return path
    path2=''
    n=len(path)
    i=0
    while i<n:
        if path[i]=='%' and i<n-2:
            path2 += chr(int(path[i+1:i+3], 16)) ## OR chr(eval('0x%s'%path[i+1:i+3]))
            i += 3
        else:
            path2 += path[i]
            i += 1
    return path2




def getSysDate(mode=None):
    if mode is None:
        mode = primaryMode
    if mode==DATE_GREG:
        return localtime()[:3]
    else:
        (gy, gm, gd) = localtime()[:3]
        return convert(gy, gm, gd, DATE_GREG, mode)

def mylocaltime(sec=None, mode=None):
    if mode==None:##DATE_GREG
        return list(localtime(sec))
    t = list(localtime(sec))
    t[:3] = convert(t[0], t[1], t[2], DATE_GREG, mode)
    return t

'''
def gmtime(sec=None, mode=None):
    if mode==None:##DATE_GREG
        return time.gmtime(sec)
    t = time.gmtime(sec)
    t[:3] = convert(t[0], t[1], t[2], DATE_GREG, mode)
    return t

def mktime(t, mode=None):
    if mode==None:##DATE_GREG
        return time.mktime(t)
    t[:3] = convert(t[0], t[1], t[2], mode, DATE_GREG)
    return time.mktime(t)
'''

def validDate(mode, y, m, d):## move to cal-modules
    if mode is None:
        mode = primaryMode
    if y<0:
        return False
    if m<1 or m>12:
        return False
    if d > getMonthLen(y, m, mode):
        return False
    return True

compressLongInt = lambda num: struct.pack('L', num).rstrip('\x00').encode('base64')[:-3].replace('/', '_')
getCompactTime = lambda maxDays=1000, minSec=0.1: compressLongInt(long(time.time()%(maxDays*24*3600) / minSec))

showInfo = lambda: log.debug('StarCalendar %s, OS: %s, Python %s'%(VERSION, getOsFullDesc(), sys.version.replace('\n', ' ')))

################################################################################
#################### End of class and function defenitions #####################
################################################################################

if len(sys.argv)>1:
    if sys.argv[1] in ('--help', '-h'):
        print('No help implemented yet!')
        sys.exit(0)
    elif sys.argv[1]=='--version':
        print(VERSION)
        sys.exit(0)


#holidayWeekDay=6 ## 6 means last day of week ( 0 means first day of week)
#thDay = (tr('First day'), tr('2nd day'), tr('3rd day'), tr('4th day'),\
#    tr('5th day'), tr('6th day'), tr('Last day'))
#holidayWeekEnable = True


pyVersion = sys.version_info[:2]
if pyVersion==(2, 6):
    sys.path.insert(0, '%s/lib/python2.6'%rootDir)
elif pyVersion==(2, 5):
    sys.path.insert(0, '%s/lib/python2.5'%rootDir)
elif pyVersion==(2, 4):
    sys.path.insert(0, '%s/lib/python2.4'%rootDir)
del pyVersion


################################################################################
###################### Default Configuration ###################################
allPlugList = []
plugIndex = []

lang = ''
langSh = 'en'
holidayWeekDays = [0] ## 0 means Sunday (5 means Friday)
## [5] or [4,5] in Iran
## [0] in most of contries
firstWeekDayAuto = True
firstWeekDay = 0 ## 0 means Sunday (6 means Saturday)
weekNumberModeAuto = False #????????????
weekNumberMode = 7
# 0: First week contains first Sunday of year
# 4: First week contains first Thursday of year (ISO 8601, Gnome Clock)
# 6: First week contains first Saturday of year
# 7: First week contains first day of year
# 8: as Locale
## 1971(53), 1972(52), 1977, 1982, 1983, 1988, 1993, 1994
## 1999(53),2000(52),2005(53),2010(53),2011(52),2016(53),2021,2022,2027,2028
################################################################################
################################################################################

#confPathDef = '/etc/starcal2/core.conf' ## ????????????????????????
#if isfile(confPathDef):## ????????????????????????
#    try:
#        exec(open(confPathDef).read())
#        #execfile(confPathDef)
#    except:
#        myRaise(__file__)

################################################################################
#################### Loading user core configuration ###########################

localeConfPath = join(confDir, 'locale.conf')
if isfile(localeConfPath):
    try:
        exec(open(localeConfPath).read())
    except:
        myRaise(__file__)

langSh = prepareLanguage(lang)
tr = loadTranslator()

sysConfPath = join(sysConfDir, 'core.conf')
if isfile(sysConfPath):
    try:
        exec(open(sysConfPath).read())
    except:
        myRaise(__file__)

confPath = join(confDir, 'core.conf')
if isfile(confPath):
    try:
        exec(open(confPath).read())
    except:
        myRaise(__file__)


################################################################################


licenseText = tr('licenseText')
if licenseText in ('licenseText', ''):
    licenseText = open('%s/license'%rootDir).read()

aboutText = tr('aboutText')
if aboutText in ('aboutText', ''):
    aboutText = open('%s/about'%rootDir).read()



weekDayName = (tr('Sunday'), tr('Monday'), tr('Tuesday'), tr('Wednesday'), tr('Thursday'), tr('Friday'), tr('Saturday'))
weekDayNameAb = (tr('Sun'), tr('Mon'), tr('Tue'), tr('Wed'), tr('Thu'), tr('Fri'), tr('Sat'))


loadAllPlugins()## FIXME


#if firstWeekDayAuto and os.sep=='/':## only if unix
#    firstWeekDay = getLocaleFirstWeekDay()

#if weekNumberModeAuto and os.sep=='/':## FIXME
#    weekNumberMode = getLocaleWeekNumberMode()

lastEventId = 0
lastEventGroupId = 0
lastEventAccountId = 0

useCompactJson = False## FIXME
dataToJson =  lambda data: dataToCompactJson(data) if useCompactJson else dataToPrettyJson(data)

