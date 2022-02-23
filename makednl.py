import sys
#import fix_qt_import_error
from PyQt5.QtWidgets import QApplication,QMainWindow,QFileDialog,QDesktopWidget
from jiemian import Ui_MainWindow
from time import strftime,localtime,sleep
from os import getcwd,path,remove
from struct import pack
from binascii import a2b_hex,b2a_hex
from PyQt5.QtCore import pyqtSignal,QThread

destType = ['STM32系列MCU','N32G4系列MCU','CPLD']
firmwareVersion = 'V0.1'
defaultStm32SrcFile1 = r'\ER_IROM3_USE'
defaultStm32SrcFile2 = r'\ER_IROM4_USE'

defaultN32G4SrcFile1 = r'\ER_IROM3_USE'
defaultN32G4SrcFile2 = r'\ER_IROM4_USE'

defaultCpldSrcFile = r'\fpga.bin'

defaultMcuDestFile = r'\mcu.dnl'
defaultCpldDestFile = r'\fpga.dnl'

manufactureInfo = r'ROSEN'

tmpDestFileName = r'tmp.bin'
tmpFileName1 = r'tmp1.bin'
tmpHeadFileName = r'head.bin'

CRC_TA16 = [0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
            0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef]

class MyMainWindow(QMainWindow,Ui_MainWindow):
    def __init__(self):
        super(MyMainWindow, self).__init__()
        self.logMessageList = []
        self.firstTriger = True
        self.srcFile = []
        self.moduleName = ''
        self.srcFileChecked = False
        self.destFileChecked  = False
        self.ModuleNameChecked = False
        self.crcData = 0

        self.setupUi(self)
        self.initUi()

        self.calCrcThread = calCRC16Thread()
        self.calCrcThread.calCRCMsg.connect(self.recvCalCrcResult)
        self.calCrcThread.start()

        self.showInformation()

    #信号反射函数
    def recvCalCrcResult(self,result):
        if result == -1:
            self.printLog("计算CRC失败")
        else:
            self.crcData = self.calCrcThread.getCrcValue()
            self.printLog("计算CRC成功，CRC={}".format(hex(self.crcData)))
            if self.makeHeadFile() == 0:
                self.printLog("升级文件打包成功!")

        self.endMakedownloadFile()

    def initUi(self):
        self.setWindowTitle('模块升级文件打包工具{}'.format(firmwareVersion))
        self.center()
        self.moduleTypeLineEdit.setMaxLength(20)
        self.destTypeComboBox.addItems(destType)

    #显示版本信息
    def showInformation(self):
        self.printLog('欢迎使用模块升级文件打包工具{}'.format(firmwareVersion))
        self.printLog('历史版本信息:')
        self.printLog('V0.1:首发版本，支持STM32 MCU和CPLD的升级文件制作')

    def center(self):
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width()-size.width())/2,(screen.height()-size.height())/2)

    #目标类型改变槽函数，初始化默认文件
    def destTypeChanged(self):

        if self.firstTriger == True:
            self.firstTriger = False
        else:
            self.printLog('修改目标类型: {}'.format(self.destTypeComboBox.currentText()))

        self.initFile()

    #更新状态机
    def updateState(self):
        # print('updateState,srcFileChecked = {},destFileChecked = {},ModuleNameChecked = {}'.format(self.srcFileChecked, self.destFileChecked,self.ModuleNameChecked))

        if self.srcFileChecked == False or self.destFileChecked == False or self.ModuleNameChecked == False:
            self.startPushButton.setEnabled(False)
        else:
            self.startPushButton.setEnabled(True)


    #初始化默认文件
    def initFile(self):
        self.addSrcFilePushButton.setEnabled(True)
        self.addDestFilePushButton.setEnabled(True)
        self.srcFile.clear()
        initError = False
        if self.destTypeComboBox.currentText() == destType[0]:
            # print('init stm32 src file')
            file1 = getcwd() + defaultStm32SrcFile1
            if path.isfile(file1):
                self.srcFile.append(file1)
            else:
                # print('open {} failed'.format(file1))
                initError = True

            if initError == False:
                file2 = getcwd() + defaultStm32SrcFile2
                if path.isfile(file2):
                    self.srcFile.append(file2)
                else:
                    # print('open {} failed'.format(file2))
                    initError = True

            if initError == True:
                self.srcFile.clear()
                self.srcFileLineEdit1.setText('')
                self.srcFileLineEdit2.setText('')
            else:
                self.srcFileLineEdit1.setText(self.srcFile[0])
                self.srcFileLineEdit2.setText(self.srcFile[1])

        elif self.destTypeComboBox.currentText() == destType[1]:
            # print('init N32G4 src file')
            initError = True
            self.addSrcFilePushButton.setEnabled(False)
            self.addDestFilePushButton.setEnabled(False)
            # file1 = getcwd() + defaultN32G4SrcFile1
            # if path.isfile(file1):
            #     self.srcFile.append(file1)
            # else:
            #     print('open {} failed'.format(file1))
            #     initError = True
            #
            # if initError == False:
            #     file2 = getcwd() + defaultN32G4SrcFile2
            #     if path.isfile(file2):
            #         self.srcFile.append(file2)
            #     else:
            #         print('open {} failed'.format(file2))
            #         initError = True
            #
            if initError == True:
                self.srcFile.clear()
                self.srcFileLineEdit1.setText('')
                self.srcFileLineEdit2.setText('')
            else:
                self.srcFileLineEdit1.setText(self.srcFile[0])
                self.srcFileLineEdit2.setText(self.srcFile[1])
        else:
            # print('init cpld src file')
            file1 = getcwd() + defaultCpldSrcFile
            if path.isfile(file1):
                self.srcFile.append(file1)
            else:
                # print('open {} failed'.format(file1))
                initError = True

            if initError == True:
                self.srcFile.clear()
                self.srcFileLineEdit1.setText('')
            else:
                self.srcFileLineEdit1.setText(self.srcFile[0])

            self.srcFileLineEdit2.setText('')

        if initError == False:
            self.srcFileChecked = True
            if self.destTypeComboBox.currentText() == destType[0]:
                # print('init stm32 dest file')
                file = getcwd() + defaultMcuDestFile
            elif self.destTypeComboBox.currentText() == destType[1]:
                # print('init N32G4 dest file')
                file = getcwd() + defaultMcuDestFile
            else:
                # print('init N32G4 dest file')
                file = getcwd() + defaultCpldDestFile
            self.destFilelineEdit.setText(file)
            self.destFileChecked = True
        else:
            self.srcFileChecked = False

            self.destFilelineEdit.setText('')
            self.destFileChecked = False

        # print('srcFileChecked = {},destFileChecked = {}'.format(self.srcFileChecked,self.destFileChecked))

        self.updateState()


    # 选择输出文件槽函数
    def chooseDestFile(self):
        if self.srcFileChecked == True:
            (filePath,fileName) = path.split(self.srcFileLineEdit1.text())
        else:
            filePath = getcwd()
        file,ok = QFileDialog.getSaveFileName(self,"open",filePath,"All Files(*);;Text Files(*.dnl)")
        if ok:
            if file:
                # print("dest file is:", file)
                self.destFilelineEdit.setText(file)
                self.destFileChecked = True
            else:
                self.destFileChecked = False

            if self.destFileChecked == True:
                self.printLog("选择输出文件成功")
        else:
         pass

        self.updateState()

    # 选择源文件槽函数
    def addSrcFile(self):
        file,ok = QFileDialog.getOpenFileNames(self,"open",getcwd(),"All Files(*);;Text Files(*.bin)")
        if ok:
            if file:
                self.srcFile.clear()
                # print("src file is:",file)
                initError = False
                if self.destTypeComboBox.currentText() == destType[0]:
                    # print('add stm32 src file')
                    if isinstance(file,list):
                        # print('number =',len(file))
                        # if len(file) > 2 or  len(file) == 0:
                        if len(file) != 2:
                            self.printLog("源文件数量错误，请选择两个文件")
                            self.srcFileChecked = False
                        elif len(file) == 1:
                            self.srcFileLineEdit1.setText(file[0])
                            self.srcFileLineEdit2.setText('')
                            self.srcFileChecked = True
                        else:
                            self.srcFileLineEdit1.setText(file[0])
                            self.srcFileLineEdit2.setText(file[1])
                            self.srcFileChecked = True

                    else:
                        self.srcFileLineEdit1.setText('')
                        self.srcFileLineEdit2.setText('')
                        self.srcFileChecked = False

                elif self.destTypeComboBox.currentText() == destType[1]:
                    # print('add N32G4 src file')
                    pass
                else:
                    # print('add CPLD src file')
                    if isinstance(file, list):
                        # print('number =', len(file))
                        if len(file) > 1 or len(file) == 0:
                            self.printLog("源文件数量错误，请选择一个文件")
                            self.srcFileChecked = False
                        elif len(file) == 1:
                            self.srcFileLineEdit1.setText(file[0])
                            self.srcFileLineEdit2.setText('')
                            self.srcFileChecked = True
                    else:
                        self.srcFileLineEdit1.setText('')
                        self.srcFileLineEdit2.setText('')
                        self.srcFileChecked = False
            else:
                self.printLog("选择源文件失败")

            if self.srcFileChecked == True:
                self.printLog("选择源文件成功")
                # self.srcFile.append(file)
                for x in file:
                    self.srcFile.append(x)
            else:
                self.srcFileLineEdit1.setText('')
                self.srcFileLineEdit2.setText('')
        else:
            pass

        self.updateState()

    #修改模块名称槽函数
    def editModuleNameSlot(self):
        # print('editModuleNameSlot,name = {}'.format(self.moduleTypeLineEdit.text()))
        if self.moduleTypeLineEdit.text() != '' and self.moduleTypeLineEdit.text() != ' ':
            self.ModuleNameChecked = True
        else:
            self.printLog("模块名称错误")
            self.moduleTypeLineEdit.setText('')
            self.ModuleNameChecked = False

        # self.ModuleNameChecked = True

        self.updateState()

    # 开始打包文件槽函数
    def startMakedownloadFile(self):
        self.addSrcFilePushButton.setEnabled(False)
        self.addDestFilePushButton.setEnabled(False)
        self.destTypeComboBox.setEnabled(False)
        self.moduleTypeLineEdit.setEnabled(False)
        self.startPushButton.setEnabled(False)

        self.printLog('生成升级文件开始...')

        if self.makeTempFile() == 0:
            self.printLog("开始计算文件CRC...")
            self.calCrcThread.startCal()
        else:
            self.endMakedownloadFile()

    def endMakedownloadFile(self):

        self.addSrcFilePushButton.setEnabled(True)
        self.addDestFilePushButton.setEnabled(True)
        self.destTypeComboBox.setEnabled(True)
        self.moduleTypeLineEdit.setEnabled(True)

        self.updateState()

        try:
            # remove(tmpDestFileName)
            remove(tmpFileName1)
            remove(tmpHeadFileName)
        except Exception as e:
            pass

        self.printLog('生成升级文件结束')

    #生成临时文件
    def makeTempFile(self):
        if self.destTypeComboBox.currentText() == destType[2]:
            # print('case 1,file = ',self.srcFile[0])
            try:
                with open(tmpDestFileName,'wb')as fout:
                    with open(self.srcFile[0],'rb') as fin:
                        fout.write(fin.read())
            except Exception as e:
                self.printLog("生成临时文件失败:{}".format(e))
                return -1
        elif self.destTypeComboBox.currentText() == destType[0]:
            if len(self.srcFile) != 2:
                self.printLog("源文件数量错误")
                return -1
            elif  path.getsize(self.srcFile[0]) > 2048:
                self.printLog("源文件{} 大于2048字节".format(self.srcFile[0]))
                return -1
            # print('case 1')
            try:
                with open(self.srcFile[0],'rb') as f:
                    data = f.read()
            except Exception as e:
                self.printLog("读取源文件{} 失败:{}".format(self.srcFile[0],e))
                return -1
            # print('case 2,data =', data)
            #将第一个文件补齐为2048大小的文件
            packInfo = '>{}s2048s'.format(path.getsize(self.srcFile[0]))
            # print('case 3,packInfo =',packInfo)
            reverstr = 'FF'*2048
            fileData = pack(packInfo,data,a2b_hex(reverstr))
            # print('case 4')
            fileData = fileData[0:2048]
            # print(fileData)
            with open(tmpFileName1,'wb') as f:
                f.write(fileData)
            # print('case 5')
            #将两个文件合并为一个文件
            try:
                with open(tmpDestFileName,'wb')as fout:
                    for file in [tmpFileName1,self.srcFile[1]]:
                        with open(file,'rb') as fin:
                            fout.write(fin.read())
            except Exception as e:
                self.printLog("生成临时文件失败:{}".format(e))
                return -1
            # print('case 6')
        else:
            return -1

        self.printLog("生成临时文件成功")
        return 0

    #生成头文件
    def makeHeadFile(self):
#对应的C语言升级文件头格式为：
# typedef struct
# {
#         Uint8 downloadSoftType; // 下载的代码类型 SOFT_TYPE_MCU = 0, mcu代码
#                                 // SOFT_TYPE_CPLD = 1, FPGA代码
#                                 // SOFT_TYPE_CPLD_ZIP = 3, FPGA压缩文件
#         Uint8 manufacturer[5]; // 厂商
#         Uint8 model[20]; // 模块型号
#         Uint8 crcData[2]; // 代码校验和，仅文件部分
#         Uint8 chipInfo[2]; // fpga芯片信息
# }S_dnlSlvDataHeadStruct;
        if self.destTypeComboBox.currentText() == destType[2]:
            downloadSoftType = 0x31
        else:
            downloadSoftType = 0x30

        chipInfo = 0xFFFF
        data = pack('<B5s20sHH',downloadSoftType,manufactureInfo.encode(),self.moduleTypeLineEdit.text().encode(),self.crcData,chipInfo)

        # print(data)
        # print(len(data))

        #mcu的头文件比cpld的头文件少两个字节
        if self.destTypeComboBox.currentText() != destType[2]:
            data = data[0:28]

        try:
            with open('head.bin','wb') as f:
                f.write(data)

            with open(self.destFilelineEdit.text(),'wb') as fout:
                for file in ['head.bin',tmpDestFileName]:
                    with open(file,'rb') as fin:
                        fout.write(fin.read())
        except Exception as e:
            self.printLog("生成头文件失败:{}".format(e))
            return -1


        self.printLog("生成头文件成功")
        return 0


    # 显示日志信息
    def printLog(self, log):
        if len(self.logMessageList) >= 100:  # 滚动显示500条信息
            self.logMessageList = self.logMessageList[1:]
        #return
        info_string = '[' + strftime('%Y-%m-%d %H:%M:%S', localtime()) + '] '
        info_string += log
        self.logMessageList.append(info_string)
        #print(self.logMessageList)

        self.logMessageTextEdit.setText('\n'.join(self.logMessageList))
        # 滚动显示最新内容
        cursor = self.logMessageTextEdit.textCursor()
        pos = len(self.logMessageTextEdit.toPlainText())
        cursor.setPosition(pos - 1)
        self.logMessageTextEdit.setTextCursor(cursor)

    # def closeEvent(self, event):
    #     print("closed")
    #     self.close()
class calCRC16Thread(QThread):
    calCRCMsg = pyqtSignal(object)
    def __init__(self):
        super(calCRC16Thread,self).__init__()
        self.startFlag = False
        self.crcValue = 0
        self.fileName = ''

    def run(self):
        while(True):
            if self.startFlag == False:
                sleep(1)
                continue
            result = self.calFileCrCValue()
            self.calCRCMsg.emit(result)
            self.startFlag = False

    def startCal(self):
        self.startFlag = True

    def getCrcValue(self):
        return self.crcValue

    # 计算文件的CRC
    def calFileCrCValue(self):
        try:
            with open(tmpDestFileName, 'rb')as f:
                fileData = f.read()
        except Exception as e:
            return -1
        try:
            crc = 0
            data = b2a_hex(fileData).decode().upper()
            data = bytearray.fromhex(data)
            # print(data)

            for x in data:
                da = ((crc >> 8) & 0xFF) >> 4
                crc <<= 4
                crc ^= CRC_TA16[da ^ (x >> 4)]
                da = ((crc >> 8) & 0xFF) >> 4
                crc <<= 4
                crc ^= CRC_TA16[da ^ (x & 0x0f)]

            crc = crc & 0xffff
        except Exception as e:
            return -1


        # print("crc = ", crc)
        self.crcValue = crc
        return 0



if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWin = MyMainWindow()
    myWin.show()
    sys.exit(app.exec_())