# -*- coding: utf-8 -*-
"""
/***************************************************************************
 RasterProperties
                                 A QGIS plugin
 Displays raster extent, resolution, and basic statistics
                              -------------------
        begin                : 2016-07-13
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Konrad Hafen
        email                : khafen74@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import *
from qgis.core import *
from osgeo import gdal

# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from raster_properties_dialog import RasterPropertiesDialog
import os


class RasterProperties:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'RasterProperties_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = RasterPropertiesDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Raster Properties')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'RasterProperties')
        self.toolbar.setObjectName(u'RasterProperties')

        self.layerIndex = 0
        self.layer = None
        self.dlg.cb_layer.setCurrentIndex(self.layerIndex)
        self.dlg.cb_layer.currentIndexChanged.connect(self.update_properties)

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('RasterProperties', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToRasterMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/RasterProperties/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Raster Properties'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginRasterMenu(
                self.tr(u'&Raster Properties'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar


    def update_properties(self, index):
        if index > -1:
            self.layerIndex = index
            self.layer = QgsMapLayerRegistry.instance().mapLayersByName( self.dlg.cb_layer.currentText() )[0]
            self.set_information()
            self.set_extent()
            self.set_statistics()

    def set_extent(self):
        e = self.layer.extent()
        self.dlg.le_top.setText(str(e.yMaximum()))
        self.dlg.le_bottom.setText(str(e.yMinimum()))
        self.dlg.le_left.setText(str(e.xMinimum()))
        self.dlg.le_right.setText(str(e.xMaximum()))
        self.dlg.le_width.setText(str((e.xMaximum() - e.xMinimum())/self.layer.width()))
        self.dlg.le_height.setText(str((e.yMaximum() - e.yMinimum())/self.layer.height()))

    def set_information(self):
        #do stuff here
        fmttypes = {0:'Unknown', 1:'Byte', 2:'UInt16', 3:'Int16', 4:'UInt32', 5:'Int32', 6:'Float32', 7:'Float64', 8:'Float64', 9:'CInt16', 10:'CInt32', 11:'CFloat32', 12:'CFloat64'}
        filepath = self.layer.dataProvider().dataSourceUri()
        (folder, file) = os.path.split(filepath)
        self.dlg.le_folder.setText(folder)
        self.dlg.le_file.setText(file)
        self.dlg.le_rows.setText(str(self.layer.width()))
        self.dlg.le_cols.setText(str(self.layer.height()))
        ds = gdal.Open(filepath)
        band = ds.GetRasterBand(1)
        self.dlg.le_data.setText(str(fmttypes[band.DataType]))

    def set_statistics(self):
        doc = QTextDocument()
        cursor = QTextCursor(doc)
        provider = self.layer.dataProvider()
        frmt = QTextCharFormat()
        frmt.setFontPointSize(10.0)

        for band in range(1, self.layer.bandCount()+1):
            stats = provider.bandStatistics(band, QgsRasterBandStats.All, self.layer.extent(), 0)
            bandName = self.layer.bandName(band)
            frmt.setFontPointSize(11.0)
            frmt.setFontWeight(99)
            cursor.insertText('Band: ' + str(band), frmt)
            frmt.setFontPointSize(10.0)
            frmt.setFontWeight(1)
            cursor.insertText('\n      Name:\t' + str(bandName) + '\n'
                              '      Min:\t' + str(round(stats.minimumValue,2)) + '\n'
                              '      Max:\t' + str(round(stats.maximumValue,2)) + '\n'
                              '      Mean:\t' + str(round(stats.mean,2)) + '\n'
                              '      Std. Dev:\t' + str(round(stats.stdDev,2)) + '\n'
                              '      Sum:\t' + str(round(stats.sum,2)) + '\n', frmt)

        self.dlg.textBrowser.setDocument(doc)

    def run(self):
        """Run method that performs all the real work"""
        self.dlg.cb_layer.clear()

        layers = self.iface.legendInterface().layers()
        layer_list = []
        for layer in layers:
            if QgsMapLayer.RasterLayer == layer.type():   # vectorLayer

                layer_list.append(layer.name())

        self.dlg.cb_layer.addItems(layer_list)
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()