#!/usr/bin/env python
# encoding: utf-8

# dhdog.py - Auto-refresh desktop background image for dual-head display
# Author: Donie Leigh <donie.leigh@gmail.com>
# License: BSD

import gtk
import os, gettext
import subprocess as sp
import cPickle as pickle

(COL_CMD, COL_EVENT, COL_ENABLE) = range(3)

class Watchdog:
    '''DualHead Watchdog'''

    emptyRow = ('', 'both', True)
    configDir = os.path.expanduser('~/.config/dhdog')
    configFile = os.path.join(configDir, 'data')
    isSettingsDirty = False
    appDir = os.path.split(os.path.realpath(__file__))[0]
    iconFile = os.path.join(appDir, 'puppy.png')
    licenseFile = os.path.join(appDir, 'LICENSE')

    def __init__(self):
        self.loadSettings()

        self.statusicon = gtk.StatusIcon()
        self.statusicon.set_from_file(self.iconFile) 
        self.statusicon.connect("popup-menu", self.showPopupMenu)
        self.statusicon.set_tooltip("Desktop background image sitter")

        # Listen to changing events of dual-head display
        screen = gtk.gdk.Screen()
        screen.connect('monitors-changed', self.onDisplayChanged, 'monitors-changed')
        screen.connect('size-changed', self.onDisplayChanged, 'size-changed')

    def loadSettings(self):
        try:
            f = open(self.configFile, 'r')
            self.settings = pickle.load(f)
            f.close()
        except IOError,e:
            self.settings = []
		
    def onDisplayChanged(self, screen, evt):
        '''Callback for display changing events'''
        for row in self.settings:
            if row[COL_ENABLE] is True and row[COL_EVENT] in ['both', evt] and len(row[COL_CMD].strip())>0:
                try:
                    p = sp.Popen(row[COL_CMD], stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE, shell=True)
                except Exception, e:
                    print e
                else:
                    if p.returncode not in [0, None]:
                        x = p.communicate()
                        print p.returncode, x[1]

    def showPopupMenu(self, icon, button, time):
        '''Show popup menu when status icon is right clicked'''
        menu = gtk.Menu()

        configItem = gtk.MenuItem('Settings')
        aboutItem = gtk.MenuItem("About")
        quitItem = gtk.MenuItem("Quit")
        
        configItem.connect('activate', self.showSettingsDialog)
        aboutItem.connect("activate", self.showAboutDialog)
        quitItem.connect("activate", gtk.main_quit)
        
        menu.append(configItem)
        menu.append(aboutItem)
        menu.append(quitItem)
        
        menu.show_all()
        
        menu.popup(None, None, gtk.status_icon_position_menu, button, time, self.statusicon)

    def showSettingsDialog(self, widget):
        '''Show settings dialog'''
        if hasattr(self, 'settingDlg'):
            self.settingDlg.present()
            return

        self.settingDlg = gtk.Dialog('DualHead Watchdog Settings', None, 0, (gtk.STOCK_CLOSE, gtk.RESPONSE_REJECT, gtk.STOCK_SAVE, gtk.RESPONSE_ACCEPT))

        scroll = gtk.ScrolledWindow()
        self.settingDlg.vbox.pack_start(scroll, True, True, 0)
        scroll.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        store = gtk.ListStore(str,str,bool)
        for row in self.settings:
            store.append(row)
        self.treeView = gtk.TreeView(store)
        scroll.add(self.treeView)
        self.treeView.connect('button-press-event', self.onButtonPressed)
        self.treeView.set_rules_hint(True)

        colCmd = gtk.TreeViewColumn(_('Command'))
        colType = gtk.TreeViewColumn(_('Event Type'))
        colEnable = gtk.TreeViewColumn(_('Enable'))
        self.treeView.append_column(colCmd)
        self.treeView.append_column(colType)
        self.treeView.append_column(colEnable)

        colRdr = gtk.CellRendererText()
        colRdr.set_property('editable', True)
        colRdr.connect('edited', self.onCellEdited, COL_CMD)
        colCmd.pack_start(colRdr, False)
        colCmd.add_attribute(colRdr, 'text', COL_CMD)
        colCmd.set_min_width(430)
        # colCmd.add_attribute(colRdr, 'editable', 1)
        colCmd.set_resizable(True)

        colRdr = gtk.CellRendererCombo()
        typeStore = gtk.ListStore(str)
        for stype in [['both'], ['monitors-changed'], ['size-changed']]:
            typeStore.append(stype)
        colRdr.set_property('editable', True)
        colRdr.set_property('model', typeStore)
        colRdr.set_property('text-column', 0)
        colRdr.connect("edited", self.onCellEdited, COL_EVENT)
        colType.pack_start(colRdr, True)
        colType.add_attribute(colRdr, 'text', COL_EVENT)
        colType.set_resizable(True)
        colType.set_min_width(140)

        colRdr = gtk.CellRendererToggle()
        colRdr.connect('toggled', self.onCheckboxToggled, COL_ENABLE)
        colEnable.pack_start(colRdr, True)
        colEnable.add_attribute(colRdr, 'active', COL_ENABLE)
        colEnable.set_resizable(False)
        colEnable.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        colEnable.set_fixed_width(50)

        self.settingDlg.set_default_size(640, 480)
        self.settingDlg.show_all()
        # response = self.settingDlg.run()
        # if response == gtk.RESPONSE_ACCEPT:
        while True:
            if gtk.RESPONSE_ACCEPT == self.settingDlg.run():
                self.saveSettings()
                self.info(_('Settings saved.'), self.settingDlg)
            else:
                if self.isSettingsDirty is True and gtk.RESPONSE_YES == self.yesno(_('Settings has been changed, save it before quit ?'), self.settingDlg):
                    self.saveSettings()
                break
            
        self.settingDlg.destroy()
        del self.settingDlg

    def saveSettings(self):
        '''Save settings'''
        self.settings = [[c for c in r] for r in self.treeView.get_model()]
        try:
            os.makedirs(self.configDir)
        except OSError:
            pass
        f = open(self.configFile, 'w')
        pickle.dump(self.settings, f, pickle.HIGHEST_PROTOCOL)
        f.close()
        self.isSettingsDirty = False

    def onButtonPressed(self, treeView, event):
        '''Show context menu'''
        if event.button == 3:
            pathInfo = treeView.get_path_at_pos(int(event.x), int(event.y))
            if pathInfo is not None:
                path, col, cellx, celly = pathInfo
                treeView.grab_focus()
                treeView.set_cursor(path, col, 0)
                self.showContextMenu(event, path)
            else:
                self.showContextMenu(event, None)

    def showContextMenu(self, event, path):
        '''Show context menu'''
        menu = gtk.Menu()

        delItem = gtk.MenuItem('Delete')
        addItem = gtk.MenuItem('Add new entry')
        
        delItem.connect('activate', lambda w: self.treeView.get_model().remove(self.treeView.get_model().get_iter(path)))
        addItem.connect("activate", self.onAddEntry)
        
        if path is not None:
            menu.append(delItem)
        menu.append(addItem)
        
        menu.show_all()
        
        menu.popup(None, None, None, event.button, event.time)

    def onAddEntry(self, evt):
        iter = self.treeView.get_model().append(self.emptyRow)
        path = self.treeView.get_model().get_string_from_iter(iter)
        self.treeView.set_cursor(path, self.treeView.get_column(COL_CMD), True)

    def onCellEdited(self, cell, path, val, colIndex):
        '''Callback for cell modification'''
        self.treeView.get_model()[path][colIndex] = val
        self.isSettingsDirty = True

    def onCheckboxToggled(self, cell, path, colIndex):
        '''Callback for combo cell modification'''
        self.treeView.get_model()[path][colIndex] = not self.treeView.get_model()[path][colIndex]
        self.isSettingsDirty = True
        
    def showAboutDialog(self, widget):
        '''Show aboutItem dialog'''
        if hasattr(self, 'aboutDlg'):
            self.aboutDlg.present()
            return

        self.aboutDlg = gtk.AboutDialog()

        self.aboutDlg.set_destroy_with_parent(True)
        self.aboutDlg.set_name("DualHead Watchdog")
        self.aboutDlg.set_version("1.0")
        self.aboutDlg.set_logo(gtk.gdk.pixbuf_new_from_file(self.iconFile)) 
        self.aboutDlg.set_authors(["Donie Leigh <donie.leigh@gmail.com>"])
        self.aboutDlg.set_artists(['Wackypixel <http://www.wackypixel.com>'])
        self.aboutDlg.set_comments('Watchdog for dual-head display. This program will refresh desktop background image automatically when display status is changed.')
        self.aboutDlg.set_copyright('Copyright (c) 2013 Donie Leigh')
        self.aboutDlg.set_website('https://github.com/xbot/DualHead-Watchdog')
        self.aboutDlg.set_website_label('Project Website')
        try:
            licFile = open(self.licenseFile, 'r')
            self.aboutDlg.set_license(licFile.read())
            licFile.close()
        except IOError:
            self.aboutDlg.set_license(_('License file missing.'))
        self.aboutDlg.set_wrap_license(True)
                
        self.aboutDlg.run()
        self.aboutDlg.destroy()
        del self.aboutDlg

    def info(self, msg, parent):
        ''' Show normal information
        '''
        dlg = gtk.MessageDialog(parent, gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, str(msg))
        dlg.run()
        dlg.destroy()

    def yesno(self, msg, parent):
        ''' Ask for confirmation
        '''
        dlg = gtk.MessageDialog(parent, gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, str(msg))
        decision = dlg.run()
        dlg.destroy()
        return decision

if __name__ == "__main__":
    gettext.install('dhdog', 'locale')
    # Watchdog().showSettingsDialog(None)
    Watchdog()
    gtk.main()
