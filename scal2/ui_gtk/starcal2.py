#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009-2011 Saeed Rasooli <saeed.gnu@gmail.com> (ilius)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License,    or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program. If not, see <http://www.gnu.org/licenses/gpl.txt>.
# Also avalable in /usr/share/common-licenses/GPL on Debian systems
# or /usr/share/licenses/common/GPL3/license.txt on ArchLinux
from time import time, localtime
#print time(), __file__ ## FIXME

import sys

if sys.version_info[0] != 2:
    print 'Run this script with Python 2.x'
    sys.exit(1)

import os
from os.path import join, dirname, isfile, isdir
from subprocess import Popen

sys.path.insert(0, dirname(dirname(dirname(__file__))))
from scal2.paths import *
from scal2.utils import myRaise, restart

if not isdir(confDir):
    try:
        __import__('scal2.ui_gtk.config_importer')
    except:
        myRaise()
    restart()

from scal2.utils import toStr, toUnicode
from scal2 import core

from scal2 import locale_man
from scal2.locale_man import rtl, lang ## import scal2.locale_man after core
#_ = locale_man.loadTranslator(False)## FIXME
from scal2.locale_man import tr as _

from scal2.core import rootDir, pixDir, deskDir, myRaise, getMonthName

core.showInfo()

from scal2 import event_man
from scal2 import ui
from scal2.ui import showYmArrows

import gobject ##?????
from gobject import timeout_add, timeout_add_seconds

import gtk
from gtk import gdk

from scal2.ui_gtk.utils import hideList, showList, set_tooltip, imageFromFile, setupMenuHideOnLeave, \
                               labelStockMenuItem, labelImageMenuItem, modify_bg_all, openWindow

from scal2.ui_gtk.color_utils import rgbToGdkColor
from scal2.ui_gtk import listener
import scal2.ui_gtk.export
import scal2.ui_gtk.selectdate

from scal2.ui_gtk.drawing import newTextLayout, newOutlineSquarePixbuf
from scal2.ui_gtk.mywidgets.clock import FClockLabel
#from ui_gtk.mywidgets2.multi_spin_button import DateButtonOption
from scal2.ui_gtk import preferences
from scal2.ui_gtk.preferences import PrefItem, gdkColorToRgb, gfontEncode, pfontEncode
from scal2.ui_gtk.customize import CustomizableWidgetWrapper, MainWinItem, CustomizeDialog
from scal2.ui_gtk.monthcal import MonthCal

from scal2.ui_gtk.event.common import addNewEvent
from scal2.ui_gtk.event.occurrence_view import DayOccurrenceView
from scal2.ui_gtk.event.main import EventManagerDialog

from scal2.ui_gtk.timeline import TimeLineWindow
from scal2.ui_gtk.weekcal import WeekCalWindow


iconSizeList = [
    ('Menu', gtk.ICON_SIZE_MENU),
    ('Small Toolbar', gtk.ICON_SIZE_SMALL_TOOLBAR),
    ('Button', gtk.ICON_SIZE_BUTTON),
    ('Large Toolbar', gtk.ICON_SIZE_LARGE_TOOLBAR),
    ('DND', gtk.ICON_SIZE_DND),
    ('Dialog', gtk.ICON_SIZE_DIALOG),
] ## in size order
iconSizeDict = dict(iconSizeList)


ui.uiName = 'gtk'


def show_event(widget, event):
    print type(widget), event.type.value_name, event.get_value()#, event.send_event


def liveConfChanged():
    tm = time()
    if tm-ui.lastLiveConfChangeTime > ui.saveLiveConfDelay:
        timeout_add(int(ui.saveLiveConfDelay*1000), ui.saveLiveConfLoop)
    ui.lastLiveConfChangeTime = tm


# How to define icon of custom stock????????????
#gtk.stock_add((
#('gtk-evolution', 'E_volution', gdk.BUTTON1_MASK, 0, 'gtk20')

class MonthLabel(gtk.EventBox):
    highlightColor = gdk.Color(45000, 45000, 45000)
    getItemStr = lambda self, i: _(i+1, fillZero=2)
    getActiveStr = lambda self, s: '<span color="%s">%s</span>'%(ui.menuActiveLabelColor, s)
    #getActiveStr = lambda self, s: '<b>%s</b>'%s
    def __init__(self, mode, active=0):
        ##assert 0<=active<12##??????????
        gtk.EventBox.__init__(self)
        #self.set_border_width(1)#???????????
        """
        print 'fg:STATE_NORMAL', gdkColorToRgb(self.style.fg[gtk.STATE_NORMAL])
        print 'fg:STATE_ACTIVE', gdkColorToRgb(self.style.fg[gtk.STATE_ACTIVE])
        print 'fg:STATE_PRELIGHT', gdkColorToRgb(self.style.fg[gtk.STATE_PRELIGHT])
        print 'fg:STATE_SELECTED', gdkColorToRgb(self.style.fg[gtk.STATE_SELECTED])
        print 'fg:STATE_INSENSITIVE', gdkColorToRgb(self.style.fg[gtk.STATE_INSENSITIVE])
        print
        print 'bg:STATE_NORMAL', gdkColorToRgb(self.style.bg[gtk.STATE_NORMAL])
        print 'bg:STATE_ACTIVE', gdkColorToRgb(self.style.bg[gtk.STATE_ACTIVE])
        print 'bg:STATE_PRELIGHT', gdkColorToRgb(self.style.bg[gtk.STATE_PRELIGHT])
        print 'bg:STATE_SELECTED', gdkColorToRgb(self.style.bg[gtk.STATE_SELECTED])
        print 'bg:STATE_INSENSITIVE', gdkColorToRgb(self.style.bg[gtk.STATE_INSENSITIVE])
        print
        ## Not differs for different gtk themes, unless you get theme after "realize"
        """
        self.mode = mode
        self.module = core.modules[mode]
        s = _(self.module.getMonthName(active+1))
        if ui.boldYmLabel:
            s = '<b>%s</b>'%s
        self.label = gtk.Label(s)
        self.label.set_use_markup(True)
        self.add(self.label)
        menu = gtk.Menu()
        menu.set_border_width(0)
        menuLabels = []
        for i in range(12):
            if ui.monthRMenuNum:
                text = '%s: %s'%(self.getItemStr(i), _(self.module.getMonthName(i+1)))
            else:
                text = _(self.module.getMonthName(i+1))
            if i==active:
                text = self.getActiveStr(text)
            label = gtk.Label(text)
            #label.set_justify(gtk.JUSTIFY_LEFT)
            label.set_alignment(0, 0.5)
            label.set_use_markup(True)
            item = gtk.MenuItem()
            item.set_right_justified(True) ##?????????
            item.add(label)
            item.connect('activate', self.itemActivate, i)
            menu.append(item)
            menuLabels.append(label)
        menu.show_all()
        self.menu = menu
        self.menuLabels = menuLabels
        self.connect('button-press-event', self.buttonPress)
        self.active = active
        self.setActive(active)
        ##########
        #self.menu.connect('map', lambda obj: self.drag_highlight())
        #self.menu.connect('unmap', lambda obj: self.drag_unhighlight())
        #########
        self.connect('enter-notify-event', self.highlight)
        self.connect('leave-notify-event', self.unhighlight)
        ####### update menu width
        if rtl:
            get_menu_pos = lambda widget: (screenW, 0, True)
            menu.popup(None, None, get_menu_pos, 3, 0)
            menu.hide()
    def setActive(self, active):
    ## (Performance) update menu here, or make menu entirly before popup ????????????????
        #assert 0<=active<12
        module = self.module
        if ui.monthRMenuNum:
            self.menuLabels[self.active].set_label('%s: %s'%
                (self.getItemStr(self.active), _(module.getMonthName(self.active+1))))
            s = _(module.getMonthName(active+1))
            self.menuLabels[active].set_label(self.getActiveStr('%s: %s'%(self.getItemStr(active), s)))
        else:
            self.menuLabels[self.active].set_label(_(module.getMonthName(self.active+1)))
            s = _(module.getMonthName(active+1))
            self.menuLabels[active].set_label(self.getActiveStr(s))
        if ui.boldYmLabel:
            self.label.set_label('<b>%s</b>'%s)
        else:
            self.label.set_label(s)
        if not locale_man.langSh in ('', 'en'):
            set_tooltip(self, module.getMonthName(active+1)) ## not translation
        self.active = active
    def changeMode(self, mode):
        module = core.modules[mode]
        self.mode = mode
        self.module = module
        if ui.boldYmLabel:
            self.label.set_label('<b>%s</b>'%_(module.getMonthName(self.active+1)))
        else:
            self.label.set_label(_(module.getMonthName(self.active+1)))
        if ui.monthRMenuNum:
            for i in range(12):
                self.menuLabels[i].set_label('%s: %s'%(self.getItemStr(i), _(module.getMonthName(i+1))))
        else:
            for i in range(12):
                self.menuLabels[i].set_label(_(module.getMonthName(i+1)))
    def itemActivate(self, item, index):
        self.setActive(index)
        self.emit('changed', index)
    def buttonPress(self, widget, event):
        global focusTime
        if event.button==3:
            (x, y) = self.window.get_origin()
            y += self.allocation.height
            if rtl:
                mw = self.menu.allocation.width
                #print 'menu.allocation.width', mw
                if mw>1:
                    x -= (mw - self.allocation.width)
            #x -= 7 ## ????????? because of menu padding
            focusTime = time()
            self.menu.popup(None, None, lambda widget: (x, y, True), event.button, event.time)
            return True
        else:
            return False
    def highlight(self, widget=None, event=None):
        #self.drag_highlight()
        if self.window==None:
            return
        cr = self.window.cairo_create()
        cr.set_source_color(self.highlightColor)
        #print tuple(self.allocation), tuple(self.label.allocation)
        (x, y, w, h) = self.allocation
        cr.rectangle(0, 0, w, 1)
        cr.fill()
        cr.rectangle(0, h-1, w, 1)
        cr.fill()
        cr.rectangle(0, 0, 1, h)
        cr.fill()
        cr.rectangle(w-1, 0, 1, h)
        cr.fill()
        cr.clip()
    def unhighlight(self, widget=None, event=None):
        #self.drag_unhighlight()
        if self.window==None:
            return
        (x, y, w, h) = self.allocation
        self.window.clear_area(0, 0, w, 1)
        self.window.clear_area(0, h-1, w, 1)
        self.window.clear_area(0, 0, 1, h)
        self.window.clear_area(w-1, 0, 1, h)




class IntLabel(gtk.EventBox):
    highlightColor = gdk.Color(45000, 45000, 45000)
    #getActiveStr = lambda self, s: '<b>%s</b>'%s
    getActiveStr = lambda self, s: '<span color="%s">%s</span>'%(ui.menuActiveLabelColor, s)
    def __init__(self, height=9, active=0):
        gtk.EventBox.__init__(self)
        #self.set_border_width(1)#???????????
        self.height = height
        #self.delay = delay
        if ui.boldYmLabel:
            s = '<b>%s</b>'%_(active)
        else:
            s = _(active)
        self.label = gtk.Label(s)
        self.label.set_use_markup(True)
        self.add(self.label)
        menu = gtk.Menu()
        ##########
        item = gtk.MenuItem()
        arrow = gtk.Arrow(gtk.ARROW_UP, gtk.SHADOW_IN)
        item.add(arrow)
        arrow.set_property('height-request', 10)
        #item.set_border_width(0)
        #item.set_property('height-request', 10)
        #print item.style_get_property('horizontal-padding') ## OK
        ###???????????????????????????????????
        #item.config('horizontal-padding'=0)
        #style = item.get_style()
        #style.set_property('horizontal-padding', 0)
        #item.set_style(style)
        menu.append(item)
        item.connect('select', self.arrowSelect, -1)
        item.connect('deselect', self.arrowDeselect)
        item.connect('activate', lambda wid: False)
        ##########
        menuLabels = []
        for i in range(height):
            label = gtk.Label()
            label.set_use_markup(True)
            item = gtk.MenuItem()
            item.add(label)
            item.connect('activate', self.itemActivate, i)
            menu.append(item)
            menuLabels.append(label)
        menu.connect('scroll-event', self.menuScroll)
        ##########
        item = gtk.MenuItem()
        arrow = gtk.Arrow(gtk.ARROW_DOWN, gtk.SHADOW_IN)
        arrow.set_property('height-request', 10)
        item.add(arrow)
        menu.append(item)
        item.connect('select', self.arrowSelect, 1)
        item.connect('deselect', self.arrowDeselect)
        ##########
        menu.show_all()
        self.menu = menu
        self.menuLabels = menuLabels
        self.connect('button-press-event', self.buttonPress)
        self.active = active
        self.setActive(active)
        self.start = 0
        self.remain = 0
        self.ymPressTime = 0
        self.etime = 0
        self.step = 0
        ##########
        #self.menu.connect('map', lambda obj: self.drag_highlight())
        #self.menu.connect('unmap', lambda obj: self.drag_unhighlight())
        #########
        #self.modify_base(gtk.STATE_NORMAL, gdk.Color(-1, 0, 0))#??????????
        self.connect('enter-notify-event', self.highlight)
        self.connect('leave-notify-event', self.unhighlight)
    def setActive(self, active):
        if ui.boldYmLabel:
            self.label.set_label('<b>%s</b>'%_(active))
        else:
            self.label.set_label(_(active))
        self.active = active
    def updateMenu(self, start=None):
        if start==None:
            start = self.active - self.height/2
        self.start = start
        for i in range(self.height):
            if start+i==self.active:
                self.menuLabels[i].set_label(self.getActiveStr(_(start+i)))
            else:
                self.menuLabels[i].set_label(_(start+i))
    def itemActivate(self, widget, item):
        self.setActive(self.start+item)
        self.emit('changed', self.start+item)
    def buttonPress(self, widget, event):
        global focusTime
        if event.button==3:
            self.updateMenu()
            (x, y) = self.window.get_origin()
            y += self.allocation.height
            x -= 7 ## ????????? because of menu padding
            focusTime = time()
            self.menu.popup(None, None, lambda widget: (x, y, True), event.button, event.time)
            return True
        else:
            return False
    def arrowSelect(self, item, plus):
        self.remain = plus
        timeout_add(int(ui.labelMenuDelay*1000), self.arrowRemain, plus)
    def arrowDeselect(self, item):
        self.remain = 0
    def arrowRemain(self, plus):
        t = time()
        #print t-self.etime
        if self.remain==plus:
            if t-self.etime<ui.labelMenuDelay-0.02:
                if self.step>1:
                    self.step = 0
                    return False
                else:
                    self.step += 1
                    self.etime = t #??????????
                    return True
            else:
                self.updateMenu(self.start+plus)
                self.etime = t
                return True
        else:
            return False
    def menuScroll(self, widget, event):
        d = event.direction.value_nick
        if d=='up':
            self.updateMenu(self.start-1)
        elif d=='down':
            self.updateMenu(self.start+1)
        else:
            return False
    def highlight(self, widget=None, event=None):
        #self.drag_highlight()
        if self.window==None:
            return
        cr = self.window.cairo_create()
        cr.set_source_color(self.highlightColor)
        (x, y, w, h) = self.allocation
        cr.rectangle(0, 0, w, 1)
        cr.fill()
        cr.rectangle(0, h-1, w, 1)
        cr.fill()
        cr.rectangle(0, 0, 1, h)
        cr.fill()
        cr.rectangle(w-1, 0, 1, h)
        cr.fill()
        cr.clip()
    def unhighlight(self, widget=None, event=None):
        #self.drag_unhighlight()
        if self.window==None:
            return
        (x, y, w, h) = self.allocation
        self.window.clear_area(0, 0, w, 1)
        self.window.clear_area(0, h-1, w, 1)
        self.window.clear_area(0, 0, 1, h)
        self.window.clear_area(w-1, 0, 1, h)


class DateLabel(gtk.Label):
    def __init__(self, text=None, onPopupFunc=None):
        gtk.Label.__init__(self, text)
        self.onPopupFunc = onPopupFunc
        self.set_selectable(True)
        #self.set_cursor_visible(False)## FIXME
        self.set_can_focus(False)
        self.set_use_markup(True)
        self.connect('populate-popup', self.popupPopulate)
        self.clipboard = gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD)
        ####
        self.menu = gtk.Menu()
        ##
        itemCopyAll = gtk.ImageMenuItem(_('Copy _All'))
        itemCopyAll.set_image(gtk.image_new_from_stock(gtk.STOCK_COPY, gtk.ICON_SIZE_MENU))
        itemCopyAll.connect('activate', self.copyAll)
        self.menu.add(itemCopyAll)
        ##
        itemCopy = gtk.ImageMenuItem(_('_Copy'))
        itemCopy.set_image(gtk.image_new_from_stock(gtk.STOCK_COPY, gtk.ICON_SIZE_MENU))
        itemCopy.connect('activate', self.copy)
        self.itemCopy = itemCopy
        self.menu.add(itemCopy)
        ##
        self.menu.show_all()
    def popupPopulate(self, label, menu):
        self.itemCopy.set_sensitive(self.get_property('cursor-position') > self.get_property('selection-bound'))## FIXME
        self.menu.popup(None, None, None, 3, 0)
        if self.onPopupFunc:
            self.onPopupFunc()
    def copy(self, item):
        start = self.get_property('selection-bound')
        end = self.get_property('cursor-position')
        self.clipboard.set_text(toStr(toUnicode(self.get_text())[start:end]))
    copyAll = lambda self, label: self.clipboard.set_text(self.get_label())




## What is "GTK Window Decorator" ??????????
class WinController(gtk.HBox):
    BUTTON_MIN         = 0
    BUTTON_MAX         = 1
    BUTTON_CLOSE       = 2
    #BUTTON_STICK
    #BUTOON_ABOVE
    #BUTTON_BELOW
    SEP                = 4
    IMAGE_NAMES        = (
        ('button-min.png', 'button-min-focus.png'),
        ('button-max.png', 'button-max-focus.png'),
        ('button-close.png', 'button-close-focus.png'),
    )
    IMAGE_INACTIVE = 'button-inactive.png'
    TOOLTIPS = (_('Minimize Window'), _('Maximize Window'), _('Close Window'))
    def __init__(self, gWin, reverse=False, button_size=23, spacing=0):
        gtk.HBox.__init__(self, spacing=spacing)
        """cache=[]
        for i in range(3):### 3 or more ??????????
            im0 = gtk.Image()
            im0.set_from_file('%s/wm/%s'%(pixDir, self.IMAGE_NAMES[i][0]))
            im1 = gtk.Image()
            im1.set_from_file('%s/wm/%s'%(pixDir, self.IMAGE_NAMES[i][1]))
            cache.append((im0,im1))
        self.image_cache = cache
        self.image_inactive = gtk.Image()
        self.image_inactive.set_from_file('%s/wm/%s'%(pixDir, self.IMAGE_INACTIVE))"""
        ###########
        if ui.winTaskbar:
            buttons=[self.SEP, self.BUTTON_MIN, self.BUTTON_CLOSE]
        else:
            buttons=[self.SEP, self.BUTTON_CLOSE]
        if reverse:
            buttons.reverse()
        self.buttons = buttons
        self.images = [None]*3 ## 3 or more??????????
        for b in buttons:
            ev = gtk.EventBox()
            if b==self.SEP:
                self.pack_start(ev, 1, 1)
            else:
                im = gtk.Image()
                im.set_from_file('%s/wm/%s'%(pixDir, self.IMAGE_NAMES[b][0]))
                im.set_size_request(button_size, button_size)
                self.images[b] = im
                ev.add(im)
                ev.connect('enter-notify-event', self.buttonEnterNotify, b)
                ev.connect('leave-notify-event', self.buttonLeaveNotify, b)
                ev.connect('button-press-event', self.buttonPress, b)
                ev.connect('button-release-event', self.buttonRelease, b)
                set_tooltip(ev, self.TOOLTIPS[b])
                self.pack_start(ev, 0, 0)
        self.set_property('can-focus', True)
        ##################
        self.gWin = gWin
        ##gWin.connect('focus-in-event', self.windowFocusIn)
        ##gWin.connect('focus-out-event', self.windowFocusOut)
        self.winFocused = True
    #def motion_notify(self, widget, event):
    #    print 'motion_notify', time()
    def buttonEnterNotify(self, widget, event, num):
        self.images[num].set_from_file('%s/wm/%s'%(pixDir, self.IMAGE_NAMES[num][1]))
    def buttonLeaveNotify(self, widget, event, num):
        if self.winFocused:
            self.images[num].set_from_file('%s/wm/%s'%(pixDir, self.IMAGE_NAMES[num][0]))
        else:
            self.images[num].set_from_file('%s/wm/%s'%(pixDir, self.IMAGE_INACTIVE))
        return False
    def buttonPress(self, widget, event, num):
        self.images[num].set_from_file('%s/wm/%s'%(pixDir, self.IMAGE_NAMES[num][0]))
        return True
    def buttonRelease(self, widget, event, num):
        if event.button!=1:
            return False
        if 0 <= event.x < widget.allocation.width and 0 <= event.y < widget.allocation.height:
            if num==self.BUTTON_MIN:
                self.gWin.iconify()
            elif num==self.BUTTON_MAX:
                if self.gWin.isMaximized:
                    self.gWin.unmaximize()
                    self.gWin.isMaximized = False
                else:
                    self.gWin.maximize()
                    self.gWin.isMaximized = True
            elif num==self.BUTTON_CLOSE:
                self.gWin.emit('delete-event', event)
        return False
    def windowFocusIn(self, widget=None, event=None):
        for b in self.buttons:
            if b!=self.SEP:
                self.images[b].set_from_file('%s/wm/%s'%(pixDir, self.IMAGE_NAMES[b][0]))
        self.winFocused = True
        return False
    def windowFocusOut(self, widget=None, event=None):
        for b in self.buttons:
            if b!=self.SEP:
                self.images[b].set_from_file('%s/wm/%s'%(pixDir, self.IMAGE_INACTIVE))
        self.winFocused = False
        return False




class CustomizableToolbar(gtk.Toolbar, MainWinItem):
    styleList = ('Icon', 'Text', 'Text below Icon', 'Text beside Icon')
    def __init__(self, mainWin):
        gtk.Toolbar.__init__(self)
        self.mainWin = mainWin
        self.setIconSizeName(ui.toolbarIconSize)
        self.add_events(gdk.POINTER_MOTION_MASK)
        ###
        optionsWidget = gtk.VBox()
        ##
        hbox = gtk.HBox()
        hbox.pack_start(gtk.Label(_('Style:')), 0, 0)
        self.styleCombo = gtk.combo_box_new_text()
        for item in self.styleList:
            self.styleCombo.append_text(_(item))
        hbox.pack_start(self.styleCombo, 0, 0)
        styleNum = self.styleList.index(ui.toolbarStyle)
        self.styleCombo.set_active(styleNum)
        self.set_style(styleNum)
        optionsWidget.pack_start(hbox, 0, 0)
        ##
        hbox = gtk.HBox()
        hbox.pack_start(gtk.Label(_('Icon Size:')), 0, 0)
        self.iconSizeCombo = gtk.combo_box_new_text()
        for (i, item) in enumerate(iconSizeList):
            self.iconSizeCombo.append_text(_(item[0]))
            if item[0]==ui.toolbarIconSize:
                self.iconSizeCombo.set_active(i)
        hbox.pack_start(self.iconSizeCombo, 0, 0)
        optionsWidget.pack_start(hbox, 0, 0)
        self.iconSizeHbox = hbox
        ##
        MainWinItem.__init__(self, 'toolbar', _('Toolbar'), optionsWidget=optionsWidget)
        self.iconSizeCombo.connect('changed', self.iconSizeComboChanged)
        self.styleCombo.connect('changed', self.styleComboChanged)
        self.styleComboChanged()
        ##
        #print 'toolbar state', self.get_state()## STATE_NORMAL
        #self.set_state(gtk.STATE_ACTIVE)## FIXME
        #self.set_property('border-width', 0)
        #style = self.get_style()
        #style.border_width = 10
        #self.set_style(style)
    getIconSizeName = lambda self: iconSizeList[self.iconSizeCombo.get_active()][0]
    setIconSizeName = lambda self, size_name: self.set_icon_size(iconSizeDict[size_name])
    ## gtk.Toolbar.set_icon_size was previously Deprecated, but it's not Deprecated now!!
    def iconSizeComboChanged(self, combo=None):
        self.setIconSizeName(self.getIconSizeName())
    def styleComboChanged(self, combo=None):
        style = self.styleCombo.get_active()
        self.set_style(style)
        self.show_all()
        self.iconSizeHbox.set_sensitive(style!=1)
    def addButton(self, item, enable):
        button = gtk.ToolButton(gtk.image_new_from_stock(item.stock, gtk.ICON_SIZE_DIALOG), item.text)
        button.set_is_important(True)
        set_tooltip(button, item.tooltip)
        button.connect('clicked', getattr(self.mainWin, item.method))
        self.insert(button, -1)
        self.items.append(CustomizableWidgetWrapper(button, item.name, item.tooltip, enable=enable))
    def updateVars(self):
        ui.toolbarItems = [(child._name, child.enable) for child in self.items]
        ui.toolbarIconSize = self.getIconSizeName()
        ui.toolbarStyle = self.styleList[self.styleCombo.get_active()]
    def confStr(self):
        text = ''
        for mod_attr in ('ui.toolbarItems', 'ui.toolbarIconSize', 'ui.toolbarStyle'):
            text += '%s=%r\n'%(mod_attr, eval(mod_attr))
        return text
    def moveItemUp(self, i):
        button = self.items[i].widget
        self.remove(button)
        self.insert(button, i-1)
        self.items.insert(i-1, self.items.pop(i))



'''
class MainWinToolbar(CustomizableToolbar):
    def __init__(self):
        CustomizableToolbar.__init__(self)
        if not ui.toolbarItems:
            ui.toolbarItems = range(len(preferences.toolbarItems))
        for i in ui.toolbarItems:
            try:
                item = preferences.toolbarItems[i]
            except IndexError:
                myRaise()
            else:
                self.addButton(item[0], item[1], item[2], eval(item[3]))
        #if self.trayMode!=1:## FIXME
        #    self.addButton(gtk.STOCK_QUIT, 'Quit', self.quit)
        """
        hbox = gtk.HBox()
        hbox.pack_start(toolbar, 1, 1)
        if ui.showDigClockTb:
            self.clock = FClockLabel(preferences.clockFormat)
            hbox.pack_start(self.clock, 0, 0)
        else:
            self.clock = None
        self.toolbBox = hbox
        """
'''

class YearMonthLabelBox(gtk.HBox, MainWinItem):
    def __init__(self):
        gtk.HBox.__init__(self)
        #self.set_border_width(2)
        self.wgroup = [[] for i in range(ui.shownCalsNum)]
        self.yearLabel = [None for i in range(ui.shownCalsNum)]
        self.monthLabel = [None for i in range(ui.shownCalsNum)]
        #############################
        def addNewArrow():
            arrow = gtk.Button()
            arrow.set_relief(2)
            arrow.set_can_focus(False)
            self.pack_start(arrow, 0, 0)
            self.wgroup[0].append(arrow)
            return arrow
        if showYmArrows:
            self.arrowPY = addNewArrow()## PY = Previous Year
        self.yearLabel[0] = IntLabel()
        self.yearLabel[0].connect('changed', self.yearLabelChange, 0)
        self.pack_start(self.yearLabel[0], 0, 0)
        self.wgroup[0].append(self.yearLabel[0])
        if showYmArrows:
            self.arrowNY = addNewArrow()## NY = Next Year
            sep = gtk.VSeparator()
            self.pack_start(sep, 1, 1)
            self.wgroup[0].append(sep)
            self.arrowPM = addNewArrow()## PM = Previous Month
        self.monthLabel[0] = MonthLabel(core.primaryMode)
        self.monthLabel[0].connect('changed', self.monthLabelChange)
        self.pack_start(self.monthLabel[0], 0, 0)
        self.wgroup[0].append(self.monthLabel[0])
        if showYmArrows:
            self.arrowNM = addNewArrow()## NM = Next Month
            self.updateArrows()
        #############################
        for i in range(1, ui.shownCalsNum):
            sep = gtk.VSeparator()
            self.pack_start(sep, 1, 1)
            self.wgroup[i-1].append(sep)
            self.wgroup[i].append(sep) ##??????????
            #if i==1: self.vsep0 = sep
            ###############
            label = IntLabel()
            self.yearLabel[i] = label
            label.connect('changed', self.yearLabelChange, i)
            self.pack_start(label, 0, 0)
            self.wgroup[i].append(label)
            ###############
            label = gtk.Label('')
            label.set_property('width-request', 5)
            self.pack_start(label, 0, 0)
            self.wgroup[i].append(label)
            ###############
            label = MonthLabel(ui.shownCals[i]['mode'])
            self.monthLabel[i] = label
            label.connect('changed', self.monthLabelChange)
            self.pack_start(label, 0, 0)
            self.wgroup[i].append(label)
        #############################
        if showYmArrows:
            self.arrowPY.connect('pressed', self.yearButtonPress,-1)
            self.arrowNY.connect('pressed', self.yearButtonPress, 1)
            self.arrowPY.connect('activate', self.yearButtonPress,-1, False)
            self.arrowNY.connect('activate', self.yearButtonPress, 1, False)
            self.arrowPY.connect('released', self.arrowRelease)
            self.arrowNY.connect('released', self.arrowRelease)
            self.arrowPM.connect('pressed', self.monthButtonPress,-1)
            self.arrowNM.connect('pressed', self.monthButtonPress, 1)
            self.arrowPM.connect('activate', self.monthButtonPress,-1, False)
            self.arrowNM.connect('activate', self.monthButtonPress, 1, False)
            self.arrowPM.connect('released', self.arrowRelease)
            self.arrowNM.connect('released', self.arrowRelease)
            #############################
            set_tooltip(self.arrowPY, _('Previous Year'))
            set_tooltip(self.arrowNY, _('Next Year'))
            set_tooltip(self.arrowPM, _('Previous Month'))
            set_tooltip(self.arrowNM, _('Next Month'))
        MainWinItem.__init__(self, 'labelBox', _('Year & Month Labels'))
    def monthPlus(self, plus=1):
        ui.monthPlus(plus)
        self.onDateChange()
        self.emit('date-change')
    def monthButtonPress(self, widget, plus, remain=True):
        self.ymPressTime = time()
        self.remain = remain
        self.monthPlus(plus)
        timeout_add(300, self.monthButtonRemain, plus)
    def monthButtonRemain(self, plus):
        if self.remain and time()-self.ymPressTime>=0.3:
            self.monthPlus(plus)
            timeout_add(150, self.monthButtonRemain, plus)
    def yearPlus(self, plus=1):
        ui.yearPlus(plus)
        self.onDateChange()
        self.emit('date-change')
    def yearButtonPress(self, widget, plus, remain=True):
        self.ymPressTime = time()
        self.remain = remain
        self.yearPlus(plus)
        timeout_add(300, self.yearButtonRemain, plus)
    def yearButtonRemain(self, plus):
        if self.remain and time()-self.ymPressTime>=0.3:
            self.yearPlus(plus)
            timeout_add(150, self.yearButtonRemain, plus)
    def arrowRelease(self, widget):
        self.remain = False
    def yearLabelChange(self, ylabel, item, num):
        mode = ui.shownCals[num]['mode']
        (y, m, d) = ui.cell.dates[mode]
        ui.changeDate(item, m, d, mode)
        self.onDateChange()
        self.emit('date-change')
    def monthLabelChange(self, mlabel, item):
        (y, m, d) = ui.cell.dates[mlabel.mode]
        ui.changeDate(y, item+1, d, mlabel.mode)
        self.onDateChange()
        self.emit('date-change')
    def updateArrows(self):
        if showYmArrows:
            if isinstance(preferences.prevStock, str):
                self.arrowPY.set_image(gtk.image_new_from_stock(preferences.prevStock, gtk.ICON_SIZE_SMALL_TOOLBAR))
                self.arrowPM.set_image(gtk.image_new_from_stock(preferences.prevStock, gtk.ICON_SIZE_SMALL_TOOLBAR))
            elif isinstance(preferences.prevStock, gtk._gtk.ArrowType):
                if self.arrowPY.child!=None:
                    self.arrowPY.remove(self.arrowPY.child)
                arrow = gtk.Arrow(preferences.prevStock, gtk.SHADOW_IN)
                self.arrowPY.add(arrow)
                arrow.show()
                ######
                if self.arrowPM.child!=None:
                    self.arrowPM.remove(self.arrowPM.child)
                arrow = gtk.Arrow(preferences.prevStock, gtk.SHADOW_IN)
                self.arrowPM.add(arrow)
                arrow.show()
            #################
            if isinstance(preferences.nextStock, str):
                self.arrowNY.set_image(gtk.image_new_from_stock(preferences.nextStock, gtk.ICON_SIZE_SMALL_TOOLBAR))
                self.arrowNM.set_image(gtk.image_new_from_stock(preferences.nextStock, gtk.ICON_SIZE_SMALL_TOOLBAR))
            elif isinstance(preferences.nextStock, gtk._gtk.ArrowType):
                if self.arrowNY.child!=None:
                    self.arrowNY.remove(self.arrowNY.child)
                arrow = gtk.Arrow(preferences.nextStock, gtk.SHADOW_IN)
                self.arrowNY.add(arrow)
                arrow.show()
                ######
                if self.arrowNM.child!=None:
                    self.arrowNM.remove(self.arrowNM.child)
                arrow = gtk.Arrow(preferences.nextStock, gtk.SHADOW_IN)
                self.arrowNM.add(arrow)
                arrow.show()
    def updateTextWidth(self):
        ############### update width of month labels
        lay = newTextLayout(self)
        width = []
        for module in core.modules:
            wm = 0
            for m in range(12):
                name = _(module.getMonthName(m))
                if ui.boldYmLabel:
                    lay.set_markup('<b>%s</b>'%name)
                else:
                    lay.set_text(name) ## OR lay.set_markup
                w = lay.get_pixel_size()[0]
                if w > wm:
                    wm = w
            width.append(wm)
        for i in range(ui.shownCalsNum):
            self.monthLabel[i].set_property('width-request', width[ui.shownCals[i]['mode']])
    def onConfigChange(self):
        self.updateTextWidth()
        self.updateArrows()
        #####################
        for i in range(len(self.monthLabel)):
            self.monthLabel[i].changeMode(ui.shownCals[i]['mode'])
        #####################
        for i in range(ui.shownCalsNum):
            if ui.shownCals[i]['enable']:
                showList(self.wgroup[i])
            else:
                hideList(self.wgroup[i])
        #if not ui.shownCals[0]['enable']:##???????
        #    self.vsep0.hide()
    def onDateChange(self):
        for (i, item) in enumerate(ui.shownCals):
            if item['enable']:
                (y, m, d) = ui.cell.dates[item['mode']]
                self.monthLabel[i].setActive(m-1)
                self.yearLabel[i].setActive(y)




class StatusBox(gtk.HBox, MainWinItem):
    def __init__(self, mainWin):
        gtk.HBox.__init__(self)
        self.mainWin = mainWin
        MainWinItem.__init__(self, 'statusBar', _('Status Bar'))
        self.dateLabel = []
        for i in range(ui.shownCalsNum):
            label = DateLabel(None, mainWin.populatePopup)
            self.dateLabel.append(label)
            self.pack_start(label, 1, 0, 0)
            ####### How to make label's cursor to be invisible ???????????????
            ####### like gtk.TextView.set_cursor_visible
            #eb = gtk.EventBox()
            #eb.add(label)
            #self.pack_start(eb, 1, 0, 0)
            #eb.connect('realize', lambda wid: eb.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.BOAT)))
            ## eb.window==None, label.window==None
        sbar = gtk.Statusbar()
        if rtl:
            self.set_direction(gtk.TEXT_DIR_LTR)
            sbar.set_direction(gtk.TEXT_DIR_LTR)
        sbar.set_property('width-request', 18)
        sbar.connect('button-press-event', self.mainWin.startResize)
        self.pack_start(sbar, 0, 0)
    def onDateChange(self):
        n = len(ui.shownCals) # ui.shownCalsNum
        nm = core.modNum
        if n < nm:
            for i in range(n, nm):
                label = DateLabel(None, self.mainWin.populatePopup)
                self.dateLabel.append(label)
                self.pack_start(label, 1, 0, 0)
        elif n > nm:
            for i in range(nm, n):
                self.dateLabel.pop(i).destroy()
        #print 'shownCals', ui.shownCals
        for i in range(n):
            if ui.shownCals[i]['enable']:
                self.dateLabel[i].show()
                mode = ui.shownCals[i]['mode']
                text = ui.cell.format(preferences.dateBinFmt, mode)
                if i==0:
                    self.dateLabel[i].set_label('<b>%s</b>'%text)
                else:
                    self.dateLabel[i].set_label(text)
            else:
                self.dateLabel[i].hide()

class PluginsTextBox(gtk.VBox, MainWinItem):
    def __init__(self, populatePopupFunc=None):
        gtk.VBox.__init__(self)
        self.enableExpander = ui.pluginsTextInsideExpander
        #####
        self.textview = gtk.TextView()
        self.textview.set_wrap_mode(gtk.WRAP_WORD)
        self.textview.set_editable(False)
        self.textview.set_cursor_visible(False)
        self.textview.set_justification(gtk.JUSTIFY_CENTER)
        self.textbuff = self.textview.get_buffer()
        if populatePopupFunc:
            self.textview.connect('populate-popup', populatePopupFunc)
        ##
        self.expander = gtk.Expander()
        self.expander.connect('activate', self.expanderExpanded)
        if self.enableExpander:
            self.expander.add(self.textview)
            self.pack_start(self.expander, 0, 0)
            self.expander.set_expanded(ui.pluginsTextIsExpanded)
        else:
            self.pack_start(self.textview, 0, 0)
        #####
        optionsWidget = gtk.HBox()
        self.enableExpanderCheckb = gtk.CheckButton(_('Inside Expander'))
        self.enableExpanderCheckb.set_active(self.enableExpander)
        self.enableExpanderCheckb.connect('clicked', lambda check: self.setEnableExpander(check.get_active()))
        self.setEnableExpander(self.enableExpander)
        optionsWidget.pack_start(self.enableExpanderCheckb, 0, 0)
        ####
        MainWinItem.__init__(self, 'pluginsText', _('Plugins Text'), optionsWidget=optionsWidget)
    def expanderExpanded(self, exp):
        ui.pluginsTextIsExpanded = not exp.get_expanded()
        ui.saveLiveConf()
    getWidget = lambda self: self.expander if self.enableExpander else self.textview
    def setText(self, text):
        if text:
            self.textbuff.set_text(text)
            self.getWidget().show()
        else:## elif self.get_property('visible')
            self.textbuff.set_text('')## forethought
            self.getWidget().hide()
    def setEnableExpander(self, enable):
        #print 'setEnableExpander', enable
        if enable:
            if not self.enableExpander:
                self.remove(self.textview)
                self.expander.add(self.textview)
                self.pack_start(self.expander, 0, 0)
                self.expander.show_all()
        else:
            if self.enableExpander:
                self.expander.remove(self.textview)
                self.remove(self.expander)
                self.pack_start(self.textview, 0, 0)
                self.textview.show()
        self.enableExpander = enable
        self.onDateChange()
    def updateVars(self):
        ui.pluginsTextInsideExpander = self.enableExpander
    def confStr(self):
        text = ''
        for mod_attr in ('ui.pluginsTextInsideExpander',):
            text += '%s=%r\n'%(mod_attr, eval(mod_attr))
        return text
    def onDateChange(self):
        self.setText(ui.cell.pluginsText)

class EventViewMainWinItem(DayOccurrenceView, MainWinItem):## FIXME
    def __init__(self, populatePopupFunc=None):
        DayOccurrenceView.__init__(self, populatePopupFunc)
        MainWinItem.__init__(self, 'eventDayView', _('Events of Day'))
    def onDateChange(self):
        self.jd = ui.cell.jd
        self.updateWidget()
    def onConfigChange(self):
        self.updateWidget()
    ## should event occurances be saved in ui.cell object? FIXME


class MainWin(gtk.Window):
    timeout = 1 ## second
    setMinHeight = lambda self: self.resize(ui.winWidth, 2)
    '''
    def do_realize(self):
        self.set_flags(self.flags() | gtk.REALIZED)
        self.window = gdk.Window(
            self.get_parent_window(),
            width=self.allocation.width,
            height=self.allocation.height,
            window_type=gdk.WINDOW_TOPLEVEL,
            wclass=gdk.INPUT_OUTPUT,
            event_mask=self.get_events() \
                | gdk.EXPOSURE_MASK | gdk.BUTTON1_MOTION_MASK | gdk.BUTTON_PRESS_MASK
                | gdk.POINTER_MOTION_MASK | gdk.POINTER_MOTION_HINT_MASK
        )
        self.window.set_user_data(self)
        self.style.attach(self.window)#?????? Needed??
        self.style.set_background(self.window, gtk.STATE_NORMAL)
        self.window.move_resize(*self.allocation)
        self.window.set_decorations(gdk.DECORE_CLOSE)
        self.window.set_functions(gdk.FUNC_CLOSE)
    '''
    #def maximize(self):
    #    pass
    def __init__(self, trayMode=3):
        ui.mainWin = self
        gtk.Window.__init__(self)##, gtk.WINDOW_POPUP) ## ????????????
        ##################
        ## trayMode:
            ## ('none', 'none')
            ## ('tray', 'normal')
            ## ('applet', 'gnome')
            ## ('applet', 'kde')
            ##
            ## 0: none (simple window)
            ## 1: applet
            ## 2: standard tray icon
        self.trayMode = trayMode
        ###
        ui.eventManDialog = EventManagerDialog()
        ui.timeLineWin = TimeLineWindow(width=rootWindow.get_geometry()[2])
        ui.weekCalWin = WeekCalWindow()
        ###########
        ##self.connect('window-state-event', selfStateEvent)
        self.set_title('%s %s'%(core.APP_DESC, core.VERSION))
        #self.connect('main-show', lambda arg: self.present())
        #self.connect('main-hide', lambda arg: self.hide())
        self.set_decorated(False)
        self.set_property('skip-taskbar-hint', not ui.winTaskbar) ## self.set_skip_taskbar_hint  ## FIXME
        self.set_role('starcal2')
        #self.set_focus_on_map(True)#????????
        #self.set_type_hint(gdk.WINDOW_TYPE_HINT_NORMAL)
        #self.connect('realize', self.onRealize)
        self.set_default_size(ui.winWidth, 1)
        try:
            self.move(ui.winX, ui.winY)
            print (ui.winX, ui.winY)
        except:
            pass
        #############################################################
        self.connect('focus-in-event', self.focusIn, 'Main')
        self.connect('focus-out-event', self.focusOut, 'Main')
        self.connect('button-press-event', self.buttonPress)
        self.connect('key-press-event', self.keyPress)
        self.connect('configure-event', self.configureEvent)
        self.connect('destroy', self.quit)
        #############################################################
        self.mcal = MonthCal()
        self.mcal.connect('popup-menu-cell', self.popupMenuCell)
        self.mcal.connect('popup-menu-main', self.popupMenuMain)
        self.mcal.connect('2button-press', ui.dayOpenEvolution)
        self.mcal.connect('pref-update-bg-color', self.prefUpdateBgColor)
        #############################################################
        """
        #self.add_events(gdk.VISIBILITY_NOTIFY_MASK)
        #self.connect('frame-event', show_event)
        ## Compiz does not send configure-event(or any event) when MOVING window(sends in last point,
        ## when moving completed)
        #self.connect('drag-motion', show_event)
        rootWindow.set_events(...
        rootWindow.add_filter(self.onRootWinEvent)
        #self.realize()
        #gdk.flush()
        #self.configureEvent(None, None)
        #self.connect('drag-motion', show_event)
        ######################
        ## ????????????????????????????????????????????????
        ## when button is down(before button-release-event), motion-notify-event does not recived!
        """
        ##################################################################
        self.focus = False
        self.focusOutTime = 0
        self.clockTr = None
        ############################################################################
        self.vbox = gtk.VBox()
        #########
        if ui.showWinController:
            self.buildWinCont()
        else:
            self.winCon = None
        ########
        self.pluginsTextBox = PluginsTextBox(self.populatePopup)
        self.eventDayView = EventViewMainWinItem(self.populatePopup)
        ############
        toolbar = CustomizableToolbar(self)
        if not ui.toolbarItems:
            ui.toolbarItems = [(item.name, True) for item in preferences.toolbarItemsData]
        for (name, enable) in ui.toolbarItems:
            try:
                item = preferences.toolbarItemsDataDict[name]
            except KeyError:
                myRaise()
            else:
                toolbar.addButton(item, enable)
        ############
        defaultItems = [
            toolbar,
            YearMonthLabelBox(),
            self.mcal,
            StatusBox(self),
            self.pluginsTextBox,
            self.eventDayView,
        ]
        defaultItemsDict = dict([(obj._name, obj) for obj in defaultItems])
        self.items = []
        for (name, enable) in ui.mainWinItems:
            try:
                item = defaultItemsDict[name]
            except:
                myRaise()
                continue
            item.enable = enable
            item.connect('size-request', self.childSizeRequest) ## or item.widget.connect
            item.connect('date-change', self.onDateChange)
            #modify_bg_all(item.widget, gtk.STATE_NORMAL, rgbToGdkColor(*ui.bgColor))
            self.items.append(item)
        self.customizeDialog = CustomizeDialog(items=self.items)
        self.vbox.pack_start(self.customizeDialog.widget, 0, 0)
        #######
        self.add(self.vbox)
        self.vbox.show()
        ####################
        self.isMaximized = False
        ####################
        ui.prefDialog = preferences.PrefDialog(self.trayMode)
        self.exportDialog = scal2.ui_gtk.export.ExportDialog()
        self.selectDateDialog = scal2.ui_gtk.selectdate.SelectDateDialog()
        self.selectDateDialog.connect('response-date', self.selectDateResponse)
        selectDateShow = self.selectDateShow
        ############### Building About Dialog
        about = gtk.AboutDialog()
        about.set_name(core.APP_DESC) ## or set_program_name
        about.set_version(core.VERSION)
        about.set_title(_('About ')+core.APP_DESC) ## must call after set_name and set_version !
        about.set_authors([_(line) for line in open(join(rootDir, 'authors-dialog')).read().splitlines()])
        about.set_comments(core.aboutText)
        about.set_license(core.licenseText)
        about.set_wrap_license(True)
        about.connect('delete-event', self.aboutHide)
        about.connect('response', self.aboutHide)
        about.set_website(core.homePage) ## A palin label (not link)
        about.set_logo(gdk.pixbuf_new_from_file(ui.logo))
        #about.set_skip_taskbar_hint(True)
        if ui.autoLocale:
            buttonbox = about.vbox.get_children()[1]## add Donate button ## FIXME
            #buttonbox.set_homogeneous(False)
            #buttonbox.set_layout(gtk.BUTTONBOX_SPREAD)
            buttons = buttonbox.get_children()## List of buttons of about dialogs
            buttons[1].set_label(_('C_redits'))
            buttons[2].set_label(_('_Close'))
            buttons[2].set_image(gtk.image_new_from_stock(gtk.STOCK_CLOSE,gtk.ICON_SIZE_BUTTON))
            buttons[0].set_label(_('_License'))
        self.about = about
        ########################################### Building main menu
        menu = gtk.Menu()
        ####
        item = gtk.ImageMenuItem(_('Resize'))
        item.set_image(imageFromFile('resize.png'))
        item.connect('button-press-event', self.startResize)
        menu.add(item)
        ####
        check = gtk.CheckMenuItem(label=_('_On Top'))
        check.connect('activate', self.keepAboveClicked)
        menu.add(check)
        check.set_active(ui.winKeepAbove)
        self.set_keep_above(ui.winKeepAbove)
        self.checkAbove = check
        #####
        check = gtk.CheckMenuItem(label=_('_Sticky'))
        check.connect('activate', self.stickyClicked)
        menu.add(check)
        check.set_active(ui.winSticky)
        if ui.winSticky:
            self.stick()
        self.checkSticky = check
        #####
        menu.add(labelStockMenuItem('Select _Today', gtk.STOCK_HOME, self.goToday))
        menu.add(labelStockMenuItem('Select _Date...', gtk.STOCK_INDEX, selectDateShow))
        menu.add(labelStockMenuItem('_Customize', gtk.STOCK_EDIT, self.customizeShow))
        menu.add(labelStockMenuItem('_Preferences', gtk.STOCK_PREFERENCES, self.prefShow))
        #menu.add(labelStockMenuItem('_Add Event', gtk.STOCK_ADD, ui.eventManDialog.addCustomEvent))
        menu.add(labelStockMenuItem('_Event Manager', gtk.STOCK_ADD, self.eventManShow))
        menu.add(labelImageMenuItem('Time Line', 'timeline-18.png', self.timeLineShow))
        menu.add(labelImageMenuItem('Week Calendar', 'weekcal-18.png', self.weekCalShow))
        menu.add(labelStockMenuItem(_('Export to %s')%'HTML', gtk.STOCK_CONVERT, self.exportClicked))
        menu.add(labelStockMenuItem('_About', gtk.STOCK_ABOUT, self.aboutShow))
        if self.trayMode!=1:
            menu.add(labelStockMenuItem('_Quit', gtk.STOCK_QUIT, self.quit))
        menu.show_all()
        self.menuMain = menu
        ############################################################
        self.trayInit()
        listener.dateChange.add(self)
        #if self.trayMode!=1:
        #    timeout_add_seconds(self.timeout, self.trayUpdate)
        #########
        self.connect('delete-event', self.dialogClose)
        ######################
        self.updateMenuSize()
        ui.prefDialog.updatePrefGui()
        self.clipboard = gtk.clipboard_get(gdk.SELECTION_CLIPBOARD)
        #########################################
        for plug in core.allPlugList:
            if plug.external and hasattr(plug, 'set_dialog'):
                plug.set_dialog(self)
        ###########################
        self.connectedWindows = [ui.eventManDialog, ui.timeLineWin, ui.weekCalWin]
        self.onConfigChange()
        #rootWindow.set_cursor(gdk.Cursor(gdk.LEFT_PTR))
    #def mainWinStateEvent(self, obj, event):
        #print dir(event)
        #print event.new_window_state
        #self.event = event
    def childSizeRequest(self, cal, req):
        self.setMinHeight()
    selectDateShow = lambda self, widget: self.selectDateDialog.show()
    def selectDateResponse(self, widget, y, m, d):
        ui.changeDate(y, m, d)
        self.onDateChange()
    def keyPress(self, arg, event):
        kname = gdk.keyval_name(event.keyval).lower()
        #print time(), 'MainWin.keyPress', kname
        if kname=='escape':
            self.dialogEsc()
        elif kname=='f1':
            self.aboutShow()
        elif kname in ('insert', 'plus', 'kp_add'):
            self.eventManShow()
        elif kname in ('q', 'arabic_dad'):## FIXME
            self.quit()
        else:
            #print kname
            for item in self.items:
                if item.enable and kname in item.myKeys:
                    item.emit('key-press-event', event)
        return True ## FIXME
    def buildWinCont(self):
        self.winCon = WinController(self, reverse=True)
        self.winCon.set_property('height-request', 15)
        self.vbox.pack_start(self.winCon, 0, 0)
        self.vbox.reorder_child(self.winCon, 0)
        self.winCon.show_all()
    def destroyWinCont(self):
        self.winCon.destroy()
        self.winCon = None
    def populatePopup(self, widget=None, event=None):
        ui.focusTime = time()
    def focusIn(self, widegt, event, data=None):
        self.focus = True
        if self.winCon:
            self.winCon.windowFocusIn()
    def focusOut(self, widegt, event, data=None):
        ## called 0.0004 sec (max) after focusIn (if swiched between two windows)
        dt = time()-ui.focusTime
        if dt>0.02: ## max=0.011 for first populate popup of textview
            self.focus = False
            timeout_add(2, self.focusOutDo)
    def focusOutDo(self):
        if not self.focus:# and t-self.focusOutTime>0.002:
            ab = self.checkAbove.get_active()
            self.set_keep_above(ab)
            if self.winCon:
                self.winCon.windowFocusOut()
        return False

    """
    def checkResize(self, widget, req):
        if ui.calHeight != req.height:# and ui.winWidth==req.width:
            if req.height==0:
                req.height=1
            ui.calHeight = req.height
    """
    def configureEvent(self, widget, event):
        liveConfChanged()
        ###
        (wx, wy) = self.get_position()
        (ww, wh) = self.get_size()
        #if ui.bgUseDesk and max(abs(ui.winX-wx), abs(ui.winY-wy))>1:## FIXME
        #    self.mcal.queue_draw()
        if self.get_property('visible'):
            (ui.winX, ui.winY) = (wx, wy)## FIXME
        ui.winWidth = ww
        #ui.focusTime = time() ##????????????
        return False
    def buttonPress(self, obj, event):
        b = event.button
        #print 'buttonPress', b
        if b==3:
            ui.focusTime = time()
            self.menuMain.popup(None, None, None, 3, event.time)
        elif b==1:
            (x, y, mask) = rootWindow.get_pointer()
            self.begin_move_drag(event.button, x, y, event.time)
        return False
    def startResize(self, widget, event):
        self.menuMain.hide()
        (x, y, mask) = rootWindow.get_pointer()
        self.begin_resize_drag(gdk.WINDOW_EDGE_SOUTH_EAST, event.button, x, y, event.time)
        return True
    def changeDate(self, year, month, day):
        ui.changeDate(year, month, day)
        self.onDateChange()
    goToday = lambda self, widget=None: self.changeDate(*core.getSysDate())
    def onDateChange(self, sender=None):
        #print 'MainWin.onDateChange', time()
        for item in self.items:
            if item.enable and item is not sender:
                item.onDateChange()
        #for j in range(len(core.plugIndex)):##????????????????????
        #    try:
        #        core.allPlugList[core.plugIndex[j]].date_change(*date)
        #    except AttributeError:
        #        pass
        self.setMinHeight()
        for j in range(len(core.plugIndex)):
            try:
                core.allPlugList[core.plugIndex[j]].date_change_after(*date)
            except AttributeError:
                pass
    def getEventAddToMenuItem(self):
        addToItem = labelStockMenuItem('_Add to', gtk.STOCK_ADD)
        menu2 = gtk.Menu()
        ##
        for group in ui.eventGroups:
            eventTypes = group.acceptsEventTypes
            item2 = gtk.ImageMenuItem()
            item2.set_label(group.title)
            ##
            image = gtk.Image()
            if group.icon:
                image.set_from_file(group.icon)
            else:
                image.set_from_pixbuf(newOutlineSquarePixbuf(group.color, 20))
            item2.set_image(image)
            ##
            if len(eventTypes)==1:
                item2.connect('activate', self.addToGroupFromMenu, group, eventTypes[0])
            else:
                menu3 = gtk.Menu()
                for eventType in eventTypes:
                    eventClass = event_man.classes.event.byName[eventType]
                    item3 = gtk.ImageMenuItem()
                    item3.set_label(eventClass.desc)
                    icon = eventClass.getDefaultIcon()
                    if icon:
                        item3.set_image(gtk.image_new_from_file(icon))
                    item3.connect('activate', self.addToGroupFromMenu, group, eventType)
                    menu3.add(item3)
                menu3.show_all()
                item2.set_submenu(menu3)
            menu2.add(item2)
        ##
        menu2.show_all()
        addToItem.set_submenu(menu2)
        return addToItem
    def popupMenuCell(self, mcal, etime, x, y):
        ui.focusTime = time()
        menu = gtk.Menu()
        ####
        menu.add(labelStockMenuItem('_Copy Date', gtk.STOCK_COPY, self.copyDate))
        menu.add(self.getEventAddToMenuItem())
        menu.add(gtk.SeparatorMenuItem())
        menu.add(labelStockMenuItem('Select _Today', gtk.STOCK_HOME, self.goToday))
        menu.add(labelStockMenuItem('Select _Date...', gtk.STOCK_INDEX, self.selectDateShow))
        if isfile('/usr/bin/evolution'):##??????????????????
            menu.add(labelImageMenuItem('In E_volution', 'evolution-18.png', ui.dayOpenEvolution))
        #if isfile('/usr/bin/sunbird'):##??????????????????
        #    menu.add(labelImageMenuItem('In _Sunbird', 'sunbird-18.png', ui.dayOpenSunbird))
        ####
        menu.show_all()
        (dx, dy) = mcal.translate_coordinates(self, x, y)
        (wx, wy) = self.window.get_origin()
        x = wx+dx
        y = wy+dy
        if rtl:
            #mw = menu.allocation.width
            #if mw < 2:# menu width
            mw = 145 ## FIXME
            x -= mw
        menu.popup(None, None, lambda m: (x, y, True), 3, etime)
    def popupMenuMain(self, mcal, etime, x, y):
        ui.focusTime = time()
        menu = self.menuMain
        (dx, dy) = mcal.translate_coordinates(self, x, y)
        (wx, wy) = self.window.get_origin()
        x = wx+dx
        y = wy+dy
        if rtl:
            mw = menu.allocation.width
            if mw < 2:# menu width
                mw = 145
            x -= mw
        menu.popup(None, None, lambda m: (x, y, True), 3, etime)
        #self.menuMainWidth = menu.allocation.width
    def addToGroupFromMenu(self, menu, group, eventType):
        #print 'addToGroupFromMenu', group.title, eventType
        title = _('Add ') + event_man.classes.event.byName[eventType].desc
        event = addNewEvent(group, eventType, title, parent=self, useSelectedDate=True)
        if event is None:
            return
        ui.newEvents.append((group.id, event.id))
        self.onConfigChange()
    def prefUpdateBgColor(self, cal):
        ui.prefDialog.colorbBg.set_color(ui.bgColor)
        ui.saveLiveConf()
    def keepAboveClicked(self, check):
        act = check.get_active()
        self.set_keep_above(act)
        ui.winKeepAbove = act
        ui.saveLiveConf()
    def stickyClicked(self, check):
        if check.get_active():
            self.stick()
            ui.winSticky = True
        else:
            self.unstick()
            ui.winSticky = False
        ui.saveLiveConf()
    def updateMenuSize(self):## DIRTY FIXME
        ## To calc/update menus size (width is used)
        getMenuPos = lambda widget: (screenW, 0, True)
        self.menuMain.popup(None, None, getMenuPos, 3, 0)
        self.menuMain.hide()
    def copyDate(self, obj=None, event=None):
        self.clipboard.set_text(ui.cell.format(preferences.dateBinFmt, core.primaryMode))
        #self.clipboard.store() ## ?????? No need!
    def copyDateToday(self, obj=None, event=None):
        self.clipboard.set_text(ui.todayCell.format(preferences.dateBinFmt, core.primaryMode))
        #self.clipboard.store() ## ?????? No need!
    def copyTime(self, obj=None, event=None):
        self.clipboard.set_text(ui.todayCell.format(preferences.clockFormatBin, core.primaryMode, localtime()[3:6]))
        #self.clipboard.store() ## ?????? No need!
    """
    def updateToolbarClock(self):
        if ui.showDigClockTb:
            if self.clock==None:
                self.clock = FClockLabel(preferences.clockFormat)
                self.toolbBox.pack_start(self.clock, 0, 0)
                self.clock.show()
            else:
                self.clock.format = preferences.clockFormat
        else:
            if self.clock!=None:
                self.clock.destroy()
                self.clock = None
    """
    def updateTrayClock(self, checkTrayMode=True):
        if checkTrayMode and self.trayMode!=3:
            return
        if ui.showDigClockTr:
            if self.clockTr==None:
                self.clockTr = FClockLabel(preferences.clockFormat)
                try:
                    self.trayHbox.pack_start(self.clockTr, 0, 0)
                except AttributeError:
                    self.clockTr.destroy()
                    self.clockTr = None
                else:
                    self.clockTr.show()
            else:
                self.clockTr.format = preferences.clockFormat
        else:
            if self.clockTr!=None:
                self.clockTr.destroy()
                self.clockTr = None
    aboutShow = lambda self, obj=None, data=None: openWindow(self.about)
    def aboutHide(self, widget, arg=None):## arg maybe an event, or response id
        self.about.hide()
        return True
    prefShow = lambda self, obj=None, data=None: openWindow(ui.prefDialog)
    customizeShow = lambda self, obj=None, data=None: openWindow(self.customizeDialog)
    eventManShow = lambda self, obj=None, data=None: openWindow(ui.eventManDialog)
    timeLineShow = lambda self, obj=None, data=None: openWindow(ui.timeLineWin)
    weekCalShow = lambda self, obj=None, data=None: openWindow(ui.weekCalWin)
    def trayInit(self):
        if self.trayMode==2:
            try:
                import appindicator
            except ImportError:
                self.sicon = gtk.StatusIcon()
                ##self.sicon.set_blinking(True) ## for Alarms ## some problem with gnome-shell
                #self.sicon.set_name('starcal2')## Warning: g_object_notify: object class `GtkStatusIcon' has no property named `name'
                self.sicon.set_title(core.APP_DESC)
                self.sicon.set_visible(True)## is needed ????????
                self.sicon.connect('activate', self.trayClicked)
                self.sicon.connect('popup-menu', self.trayPopup)
            else:
                from scal2.ui_gtk.starcal2_appindicator import IndicatorStatusIconWrapper
                self.sicon = IndicatorStatusIconWrapper(self)
            self.trayPix = gdk.Pixbuf(gdk.COLORSPACE_RGB, True, 8, ui.traySize, ui.traySize)
        else:
            self.sicon = None
    getMainWinMenuItem = lambda self: labelStockMenuItem('Main Window', None, self.trayClicked)
    getTrayPopupItems = lambda self: [
        labelStockMenuItem('Copy _Time', gtk.STOCK_COPY, self.copyTime),
        labelStockMenuItem('Copy _Date', gtk.STOCK_COPY, self.copyDateToday),
        labelStockMenuItem('Ad_just System Time', gtk.STOCK_PREFERENCES, self.adjustTime),
        #labelStockMenuItem('_Add Event', gtk.STOCK_ADD, ui.eventManDialog.addCustomEvent),## FIXME
        labelStockMenuItem(_('Export to %s')%'HTML', gtk.STOCK_CONVERT, self.exportClickedTray),
        labelStockMenuItem('_Preferences', gtk.STOCK_PREFERENCES, self.prefShow),
        labelStockMenuItem('_Event Manager', gtk.STOCK_ADD, self.eventManShow),
        labelImageMenuItem('Time Line', 'timeline-18.png', self.timeLineShow),
        labelStockMenuItem('_About', gtk.STOCK_ABOUT, self.aboutShow),
        gtk.SeparatorMenuItem(),
        labelStockMenuItem('_Quit', gtk.STOCK_QUIT, self.quit),
    ]
    def trayPopup(self, sicon, button, etime):
        core.focusTime = time()    ## needed?????
        menu = gtk.Menu()
        if os.sep == '\\':
            setupMenuHideOnLeave(menu)
        items = self.getTrayPopupItems()
        # items.insert(0, self.getMainWinMenuItem())## FIXME
        geo = self.sicon.get_geometry() ## Returns None on windows, why???
        if geo==None:## windows, taskbar is on buttom(below)
            items.reverse()
            get_pos_func = None
        else:
            y1 = geo[1][1]
            y = gtk.status_icon_position_menu(menu, self.sicon)[1]
            if y<y1:## taskbar is on bottom
                items.reverse()
            get_pos_func = gtk.status_icon_position_menu
        for item in items:
            menu.add(item)
        menu.show_all()
        menu.popup(None, None, get_pos_func, button, etime, self.sicon)
    def onCurrentDateChange(self, gdate):
        self.trayUpdate(gdate=gdate)
    def getTrayTooltip(self):
        ##tt = core.weekDayName[core.getWeekDay(*ddate)]
        tt = core.weekDayName[core.jwday(ui.todayCell.jd)]
        #if ui.pluginsTextTray:##?????????
        #    sep = _(',')+' '
        #else:
        sep = '\n'
        for item in ui.shownCals:
            if item['enable']:
                mode = item['mode']
                module = core.modules[mode]
                (y, m, d) = ui.todayCell.dates[mode]
                tt += '%s%s %s %s'%(sep, _(d), getMonthName(mode, m, y), _(y))
        if ui.pluginsTextTray:
            text = ui.todayCell.pluginsText
            if text!='':
                tt += '\n\n%s'%text.replace('\t', '\n') #????????????
        return tt
    def trayUpdate(self, gdate=None, checkTrayMode=True):
        if checkTrayMode and self.trayMode < 1:
            return
        if gdate is None:
            gdate = localtime()[:3]
        if core.primaryMode==core.DATE_GREG:
            ddate = gdate
        else:
            ddate = core.convert(gdate[0], gdate[1], gdate[2], core.DATE_GREG, core.primaryMode)
        imagePath = ui.trayImageHoli if ui.todayCell.holiday else ui.trayImage
        ######################################
        '''
        import Image, ImageDraw, ImageFont
        im = Image.open(imagePath)
        (w, h) = im.size
        draw = ImageDraw.Draw(im)
        text = _(ddate[2]).decode('utf8')
        font = ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf', 15)
        (fw, fh) = font.getsize(text)
        draw.text(
            ((w-fw)/2, (h-fh)/2),
            text,
            font=font,
            fill=ui.trayTextColor,
        )
        self.sicon.set_from_pixbuf(gdk.pixbuf_new_from_data(im.tostring(), gdk.COLORSPACE_RGB, True, 8, w, h, 4*w))
        '''
        pixbuf = gdk.pixbuf_new_from_file(imagePath)
        ##pixbuf.scale() #????????????
        ###################### PUTTING A TEXT ON A PIXBUF
        pmap = pixbuf.render_pixmap_and_mask(alpha_threshold=127)[0] ## pixmap is also a drawable
        textLay = newTextLayout(self, _(ddate[2]), ui.trayFont)
        (w, h) = textLay.get_pixel_size()
        s = ui.traySize
        if ui.trayY0 == None:
            y = s/4+int((0.9*s-h)/2)
        else:
            y = ui.trayY0
        pmap.draw_layout(pmap.new_gc(), (s-w)/2, y, textLay, gdk.Color(*ui.trayTextColor))## , foreground, background)
        self.trayPix.get_from_drawable(pmap, self.get_screen().get_system_colormap(), 0, 0, 0, 0, s, s)
        ######################################
        self.sicon.set_from_pixbuf(self.trayPix)
        ######################################
        set_tooltip(self.sicon, self.getTrayTooltip())
        return True
    def trayClicked(self, obj=None):
        if self.get_property('visible'):
            (ui.winX, ui.winY) = self.get_position()
            self.hide()
        else:
            self.move(ui.winX, ui.winY)
            ## every calling of .hide() and .present(), makes dialog not on top
            ## (forgets being on top)
            act = self.checkAbove.get_active()
            self.set_keep_above(act)
            if self.checkSticky.get_active():
                self.stick()
            self.deiconify()
            self.present()
    def dialogClose(self, widget=None, event=None):
        (ui.winX, ui.winY) = self.get_position()
        if self.trayMode==0 or not self.sicon:
            self.quit()
        elif self.trayMode>1:
            if self.sicon.is_embedded():
                self.hide()
            else:
                self.quit()
        return True
    def dialogEsc(self):
        (ui.winX, ui.winY) = self.get_position()
        if self.trayMode==0:
            self.quit()
        elif self.trayMode>1:
            if self.sicon.is_embedded():
                self.hide()
    def quit(self, widget=None, event=None):
        try:
            ui.saveLiveConf()
        except:
            myRaise()
        if self.trayMode>1 and self.sicon:
            self.sicon.set_visible(False) ## needed for windows ## before or after main_quit ?
        return gtk.main_quit()
    def restart(self):
        self.quit()
        os.environ['LANG'] = locale_man.sysLangDefault
        restart()
    def adjustTime(self, widget=None, event=None):
        Popen(preferences.adjustTimeCmd)
    exportClicked = lambda self, widget=None: self.exportDialog.showDialog(ui.cell.year, ui.cell.month)
    def exportClickedTray(self, widget=None, event=None):
        (y, m) = core.getSysDate()[:2]
        self.exportDialog.showDialog(y, m)
    def onConfigChange(self, senderWindow=None):
        #self.set_property('skip-taskbar-hint', not ui.winTaskbar) ## self.set_skip_taskbar_hint ## FIXME
        ## skip-taskbar-hint  need to restart ro be applied
        preferences.settings.set_property(
            'gtk-font-name',
            pfontEncode(ui.getFont()),
        )
        self.updateMenuSize()
        #self.updateToolbarClock()## FIXME
        self.updateTrayClock()
        if ui.showWinController:
            if self.winCon==None:
                self.buildWinCont()
        else:
            if self.winCon!=None:
                self.destroyWinCont()
        ui.cellCache.clear()
        for item in self.items:
            item.onConfigChange()
        self.trayUpdate()
        self.onDateChange()
        ###
        for window in self.connectedWindows:
            if window!=senderWindow:
                window.onConfigChange()


###########################################################################3

gobject.type_register(MainWin)

for cls in (CustomizableToolbar, YearMonthLabelBox, StatusBox, PluginsTextBox, EventViewMainWinItem):
    gobject.type_register(cls)
    gobject.signal_new('date-change', cls, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [])

gobject.type_register(MonthLabel)
gobject.signal_new('changed', MonthLabel, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [int])

gobject.type_register(IntLabel)
gobject.signal_new('changed', IntLabel, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [int])






#core.COMMAND = sys.argv[0] ## OR __file__ ## ????????


if rtl:
    gtk.widget_set_default_direction(gtk.TEXT_DIR_RTL)


gtk.init_check()
gtk.window_set_default_icon_from_file(ui.logo)


clickWebsite = lambda widget, url: core.openUrl(url)
try:
    gtk.link_button_set_uri_hook(clickWebsite)
except:## old PyGTK (older than 2.10)
    pass

try:
    gtk.about_dialog_set_url_hook(clickWebsite)
except:## old PyGTK (older than 2.10)
    pass


"""
themeDir = join(rootDir, 'themes')
theme = 'Dark' # 'Default
if theme!=None:
    gtkrc = join(themeDir, theme, 'gtkrc')
    try:
        #gtk.rc_set_default_files([gtkrc])
        gtk.rc_parse(gtkrc)
        #gtk.rc_reparse_all()
        #exec(open(join(themeDir, theme, 'starcalrc')).read())
    except:
        myRaise(__file__)
"""



rootWindow = gdk.get_default_root_window() ## Good Place?????
##import atexit
##atexit.register(rootWindow.set_cursor, gdk.Cursor(gdk.LEFT_PTR)) ## ?????????????????????
#rootWindow.set_cursor(cursor=gdk.Cursor(gdk.WATCH)) ## ???????????????????
(screenW, screenH) = rootWindow.get_size()



def main():
    '''
    try:
        import psyco
    except ImportError:
        print('Warning: module "psyco" not found. It could speed up execution.')
        psyco_found=False
    else:
        psyco.full()
        print('Using module "psyco" to speed up execution.')
        psyco_found=True'''
    trayMode = 2
    action = ''
    if ui.showMain:
        action = 'show'
    if len(sys.argv)>1:
        if sys.argv[1]=='--no-tray': ## no tray icon
            trayMode = 0
            action = 'show'
        elif sys.argv[1]=='--hide':
            action = ''
        elif sys.argv[1]=='--show':
            action = 'show'
        #elif sys.argv[1]=='--html':#????????????
        #    action = 'html'
        #elif sys.argv[1]=='--svg':#????????????
        #    action = 'svg'
    mainWin = MainWin(trayMode=trayMode)
    #if action=='html':
    #    mainWin.exportHtml('calendar.html') ## exportHtml(path, months, title)
    #    sys.exit(0)
    #elif action=='svg':
    #    mainWin.export.exportSvg('%s/2010-01.svg'%deskDir, [(2010, 1)])
    #    sys.exit(0)
    if action=='show' or not mainWin.sicon:
        mainWin.present()
    ##rootWindow.set_cursor(gdk.Cursor(gdk.LEFT_PTR))#???????????
    return gtk.main()


if __name__ == '__main__':## this file may be called from starcal-gnome2-applet
    sys.exit(main())

