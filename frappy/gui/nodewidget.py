from collections import OrderedDict
import json

import frappy.gui.resources # pylint: disable=unused-import
from frappy.gui.qt import QFont, QFontMetrics, QLabel, QTextCursor, QWidget, \
        pyqtSlot, toHtmlEscaped, QVBoxLayout, QGridLayout, QPlainTextEdit, \
        QMenu, QCursor, QIcon, QInputDialog, pyqtSignal
from frappy.gui.util import Colors, loadUi
from frappy.gui.plotting import getPlotWidget
from frappy.gui.modulectrl import ModuleCtrl
from frappy.gui.paramview import ParameterView
from frappy.gui.modulewidget import ModuleWidget
from frappy.gui.moduleoverview import ModuleOverview

from frappy.errors import SECoPError

class Console(QWidget):
    def __init__(self, node, parent=None):
        super().__init__(parent)
        loadUi(self, 'console.ui')
        self._node = node
        self._clearLog()

    @pyqtSlot()
    def on_sendPushButton_clicked(self):
        msg = self.msgLineEdit.text().strip()

        if not msg:
            return

        self._addLogEntry(
            '<span style="font-weight:bold">Request:</span> '
            '<tt>%s</tt>' % toHtmlEscaped(msg),
            raw=True)
        #        msg = msg.split(' ', 2)
        try:
            reply = self._node.syncCommunicate(*self._node.decode_message(msg))
            if msg == 'describe':
                _, eid, stuff = self._node.decode_message(reply)
                reply = '%s %s %s' % (_, eid, json.dumps(
                    stuff, indent=2, separators=(',', ':'), sort_keys=True))
                self._addLogEntry(reply.rstrip('\n'))
            else:
                self._addLogEntry(reply.rstrip('\n'))
        except SECoPError as e:
            einfo = e.args[0] if len(e.args) == 1 else json.dumps(e.args)
            self._addLogEntry('%s: %s' % (e.name, einfo), error=True)
        except Exception as e:
            self._addLogEntry('error when sending %r: %r' % (msg, e), error=True)

        self.msgLineEdit.selectAll()

    @pyqtSlot()
    def on_clearPushButton_clicked(self):
        self._clearLog()

    def _clearLog(self):
        self.logTextBrowser.clear()

        self._addLogEntry('<div style="font-weight: bold">'
                          'SECoP Communication Shell<br/>'
                          '=========================<br/></div>',
                          raw=True)

    def _addLogEntry(self, msg, raw=False, error=False):
        if not raw:
            if error:
                msg = '<div style="color:#FF0000"><b><pre>%s</pre></b></div>' % toHtmlEscaped(
                    str(msg)).replace('\n', '<br />')
            else:
                msg = '<pre>%s</pre>' % toHtmlEscaped(
                    str(msg)).replace('\n', '<br />')

        content = ''
        if self.logTextBrowser.toPlainText():
            content = self.logTextBrowser.toHtml()
        content += msg

        self.logTextBrowser.setHtml(content)
        self.logTextBrowser.moveCursor(QTextCursor.End)

    def _getLogWidth(self):
        fontMetrics = QFontMetrics(QFont('Monospace'))
        # calculate max avail characters by using an m (which is possible
        # due to monospace)
        result = self.logTextBrowser.width() / fontMetrics.width('m')
        return result

class NodeWidget(QWidget):
    noPlots = pyqtSignal(bool)

    def __init__(self, node, parent=None):
        super().__init__(parent)
        loadUi(self, 'nodewidget.ui')

        self._node = node
        self._node.stateChange.connect(self._set_node_state)

        self._modules = OrderedDict()
        self._detailedModules = {}
        self._detailedParams = {}
        self._activePlots = {}

        self.top_splitter.setStretchFactor(0, 2)
        self.top_splitter.setStretchFactor(1, 10)
        self.top_splitter.setSizes([180, 500])

        self.middle_splitter.setCollapsible(self.middle_splitter.indexOf(self.view), False)
        self.middle_splitter.setStretchFactor(0, 20)
        self.middle_splitter.setStretchFactor(1, 1)

        self.infobox_splitter.setStretchFactor(0,3)
        self.infobox_splitter.setStretchFactor(1,2)

        self.consoleWidget.setTitle('Console')
        cmd = Console(node, self.consoleWidget)
        self.consoleWidget.replaceWidget(cmd)

        viewLayout = self.viewContent.layout()
        for module in node.modules:
            widget = ModuleWidget(node, module, self.view)
            widget.plot.connect(lambda param, module=module:
                                self.plotParam(module, param))
            widget.plotAdd.connect(lambda param, module=module:
                                   self._plotPopUp(module, param))
            self.noPlots.connect(widget.plotsPresent)
            self._modules[module] = widget
            details = ModuleCtrl(node, module)
            self._detailedModules[module] = details
            viewLayout.addWidget(details)
            details.setHidden(True)
            self._detailedParams[module] = {}
            for param in node.getParameters(module):
                view = ParameterView(node, module, param)
                self._detailedParams[module][param] = view
                view.setHidden(True)
                viewLayout.addWidget(view)
            viewLayout.addWidget(widget)

        self._initNodeInfo()


    def _initNodeInfo(self):
        self.tree = ModuleOverview(self._node)
        infolayout = QVBoxLayout()
        infolayout.setContentsMargins(0, 0, 0, 0)
        infolayout.addWidget(self.tree)
        self.infotree.setLayout(infolayout)
        # disabled until i find a way to deselect and go back to overview
        self.tree.itemChanged.connect(self.changeViewContent)
        self.tree.customContextMenuRequested.connect(self._treeContextMenu)

        self._description = QPlainTextEdit(
            self._node.properties.get('description','no description available'))
        self._description_label = QLabel('Description:')
        self._description.setReadOnly(True)
        self._host = QLabel(self._node.conn.uri)
        self._host.hide()
        self._host_label = QLabel('Host:')
        self._host_label.hide()
        self._protocoll = QLabel(self._node.conn.secop_version)
        self._protocoll.setWordWrap(True)
        self._protocoll.hide()
        self._protocoll_label = QLabel('Protocoll Version:')
        self._protocoll_label.hide()

        layout = QGridLayout()
        layout.addWidget(self._host_label, 0, 0)
        layout.addWidget(self._host, 0, 1)
        layout.addWidget(self._protocoll_label, 1, 0)
        layout.addWidget(self._protocoll, 1, 1)
        layout.addWidget(self._description_label, 2, 0)
        layout.addWidget(self._description, 3, 0, -1, -1)
        self.nodeinfo.setLayout(layout)

    def _set_node_state(self, nodename, online, state):
        p = self.palette()
        if online:
            p.setColor(self.backgroundRole(),Colors.palette.window().color())
            self.tree.setToReconnected()
        else:
            p.setColor(self.backgroundRole(), Colors.colors['orange'])
            # TODO: reset this for non-status modules!
            self.tree.setToDisconnected()
        self.setPalette(p)


    def _rebuildAdvanced(self, advanced):
        self._host.setHidden(not advanced)
        self._host_label.setHidden(not advanced)
        self._protocoll.setHidden(not advanced)
        self._protocoll_label.setHidden(not advanced)
        self.tree._rebuildAdvanced(advanced)
        for m in self._modules.values():
            m.rebuildAdvanced(advanced)

    def getSecNode(self):
        return self._node

    def changeViewContent(self, module, param, prevmod, prevparam):
        if prevmod == '':
            for mod in self._modules.values():
                mod.setHidden(True)
        elif prevparam == '':
            self._detailedModules[prevmod].setHidden(True)
        else:
            self._detailedParams[prevmod][prevparam].setHidden(True)
        if module == '':
            # no module -> reset to overview
            for mod in self._modules.values():
                mod.setHidden(False)
        elif param == '':
            # set to single module view
            self._detailedModules[module].setHidden(False)
        else:
            # set to single param view
            self._detailedParams[module][param].setHidden(False)

    def _treeContextMenu(self, pos):
        index = self.tree.indexAt(pos)
        if not index.isValid():
            return
        item = self.tree.itemFromIndex(index)

        menu = QMenu()
        opt_plot = menu.addAction('Plot')
        opt_plot.setIcon(QIcon(':/icons/plot'))
        menu_plot_ext = menu.addMenu("Plot with...")
        menu_plot_ext.setIcon(QIcon(':/icons/plot'))
        if not self._activePlots:
            menu_plot_ext.setEnabled(False)
        else:
            for (m,p),plot in self._activePlots.items():
                opt_ext = menu_plot_ext.addAction("%s:%s" % (m,p))
                opt_ext.triggered.connect(
                        lambda plot=plot: self._requestPlot(item, plot))

        menu.addSeparator()
        opt_clear = menu.addAction('Clear Selection')
        opt_plot.triggered.connect(lambda: self._requestPlot(item))
        opt_clear.triggered.connect(self.tree.clearTreeSelection)
        #menu.exec_(self.mapToGlobal(pos))
        menu.exec_(QCursor.pos())

    def _requestPlot(self, item, plot=None):
        module = item.module
        param = item.param or 'value'
        self.plotParam(module, param, plot)

    def _plotPopUp(self, module, param):
        plots = {'%s -> %s' % (m,p): (m,p) for (m,p) in self._activePlots}
        dialog = QInputDialog()
        #dialog.setInputMode()
        dialog.setOption(QInputDialog.UseListViewForComboBoxItems)
        dialog.setComboBoxItems(plots.keys())
        dialog.setTextValue(list(plots)[0])
        dialog.setWindowTitle('Plot %s with...' % param)
        dialog.setLabelText('')

        if dialog.exec_() == QInputDialog.Accepted:
            item = dialog.textValue()
            self.plotParam(module, param, self._activePlots[plots[item]])


    def plotParam(self, module, param, plot=None):
        # - liveness?
        # - better plot window management?

        # only allow one open plot per parameter TODO: change?
        if (module, param) in self._activePlots:
            return
        if plot:
            plot.addCurve(self._node, module, param)
            plot.setCurveColor(module, param, Colors.colors[len(plot.curves) % 6])
        else:
            plot = getPlotWidget(self)
            plot.addCurve(self._node, module, param)
            plot.setCurveColor(module, param, Colors.colors[1])
            self._activePlots[(module, param)] = plot
            plot.closed.connect(lambda: self._removePlot(module, param))
            plot.show()

        self.noPlots.emit(len(self._activePlots) == 0)

        # initial datapoint
        cache = self._node.queryCache(module)
        if param in cache:
            plot.update(module, param, cache[param])

    def _removePlot(self, module, param):
        self._activePlots.pop((module,param))
        self.noPlots.emit(len(self._activePlots) == 0)
