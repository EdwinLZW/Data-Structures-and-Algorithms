# -*- coding: utf-8 -*-
__Author__ = "Simon Liu"

import zmq
import time
import serial
import socket
import datetime
from datetime import datetime

import serial.tools.list_ports as pts
from abc import abstractmethod, ABCMeta, abstractproperty


class AbstractDriver(object):

    def __init__(self, publisher=None):
        self.publisher = publisher

    def log(self, msg):
        print_with_time(msg)
        if isinstance(self.publisher, ZmqPublisher):
            self.publisher.publish(msg)

    @abstractmethod
    def open(self):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractproperty
    def isOpen(self):
        pass

    @abstractmethod
    def send(self, cmd, description=''):
        pass

    @abstractmethod
    def receive(self, size=None):
        pass

    @abstractmethod
    def query(self, cmd, tmo, size=None):
        pass

    @abstractmethod
    def read_until(self, tmo=None, terminator=">", size=None):
        pass

    @abstractmethod
    def read_line(self, timeout):
        pass


class SerialCommunicate(AbstractDriver):

    def __init__(self, cfg, publisher=None):
        super(SerialCommunicate, self).__init__(publisher)
        self.timeout = cfg.get("timeout", "3000")
        self.terminator = cfg.get("terminator", "\n")
        self.port = cfg.get("port", None)
        self.baudrate = cfg.get("baudrate", "115200")
        self.__session = None
        self.flag = False

    def open(self):
        """
        no need open cause init Serial means open
        didn't set timeout means block
        :return: True
        """
        if not self.__session:
            try:
                self.__session = serial.Serial(self.port, self.baudrate)
            except Exception as e:
                raise RuntimeError("Open serial port error: %s", self.port)
            return True

    def close(self):
        """
        close the port
        different version has different is_open
        is_open or isOpen()
        :return:
        """
        if self.isOpen():
            self.__session.flush()
            self.__session.close()
            del self.__session
            self.__session = None
            print("close port OK")

    def isOpen(self):
        """
        whether serial is open
        :return: bool
        """
        return self.__session.isOpen()

    def send(self, cmd, description=''):
        """
        send cmd by serial port
        :return:
        """
        if self.isOpen():
            # flush buffer
            self.__session.flushInput()
            self.__session.flushOutput()
            try:
                self.__session.write(cmd)
                print " >>>>>>>> SEND TO FIXTURE: {}".format(cmd.strip())
            except Exception as e:
                raise RuntimeError("cmd send error: ", e)
        else:
            raise RuntimeError("Cmd send error, port not open: %s", self.__session.name)

    def receive(self, size=None):
        """
        block
        :param size:
        :return:
        """
        line = str()
        lenterm = len(self.terminator)
        if self.isOpen():
            while True:
                c = self.__session.read(1)
                if c:
                    line += c
                    if str(line[-lenterm:]) == self.terminator:
                        break
            return line
        else:
            return "ERROR-SERIAL_DISCONNECT"

    def query(self, cmd, tmo, size=None):
        if self.isOpen():
            self.send(cmd)
            return self.read_until(tmo,
                                   self.terminator)
        else:
            return "ERROR-SERIAL_DISCONNECT"

    def read_line(self, timeout):
        """
        timeout is xxx.ms not s
        :param timeout:
        :return:
        """
        if self.isOpen():
            res = self.__session.readline(timeout)
            return res
        else:
            return "ERROR-SERIAL_DISCONNECT"

    def read_until(self, tmo, terminator=">", size=None):
        """
        this method come from serialutil
        Read until a termination is found , the size
        is exceeded or until timeout occurs.
        no block
        """
        if self.isOpen():
            lenterm = len(terminator)
            print("terminator:" + terminator)
            line = str()

            timeout = self.timeout  # Timeout(self.timeout)
            start = time.time()
            while True:
                c = self.__session.read(1)
                if c:
                    line += c
                    if str(line[-lenterm:]) == terminator:

                        break
                    if size is not None and len(line) >= size:
                        break
                    if str(terminator) in line:
                        break
                if time.time() - start >= timeout:
                    return "ERROR - TIMEOUT"
            return line
        else:
            return "ERROR-SERIAL_DISCONNECT"

    def read_all(self):
        if self.isOpen():
            if self.__session.inWaiting():
                return self.__session.readline(1000)
            else:
                return None
        else:
            return None



    @classmethod
    def create(cls, cfg, port):
        assert isinstance(cfg, dict)
        cfg_port = cfg
        cfg_port["port"] = port
        return cls(cfg_port)

    @classmethod
    def get_port_by_location(self, location, retry=3):
        for i in range(retry):
            for ser in pts.comports():
                if ser.location == location:
                    return ser.device
            time.sleep(1)
        return None


class TcpCommunicate(AbstractDriver):
    def __init__(self, cfg, publisher=None):
        super(TcpCommunicate, self).__init__(publisher)
        self.__timeout = cfg.get("timeout", 0.2)
        self.__net_config = (cfg.get("ip"), cfg.get("port"))
        self.__terminator = cfg.get("terminator", "\r\n")
        self.__session = None
        self.__status = False
        self.open()

    def open(self):
        ret = False
        if not self.isOpen():
            try:
                self.__session = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.__session.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                self.__session.settimeout(self.__timeout)
            except Exception as e:
                ret = False
                raise e
            try:
                if self.__session.connect_ex(self.__net_config) == 0:

                    self.__status = True
                else:
                    self.__status = False
            except Exception as e:
                ret = False
                self.__status = False
        return ret

    def close(self):
        if self.__session and self.isOpen():
            self.__session.shutdown(socket.SHUT_RDWR)
            self.__session.close()
            del self.__session
            self.__status = False
            self.__session = None

    def isOpen(self):
        return self.__status

    def send(self, cmd, description=None):
        """
        all send's command should add description before command
        :param cmd:
        :param description:
        :return:
        """
        if self.isOpen():
            try:
                self.__session.send(cmd)
                if description:
                    self.log(str(datetime.now()) + ' '*3+"{0} Send Command:'{1}' ".format(description, cmd.strip()))
                else:
                    self.log(" >>>>>> [SEND: {}]".format(cmd.strip()))
            except Exception as e:
                raise RuntimeError("cmd send error: ", e)
        else:
            raise RuntimeError("Cmd send error, port not open: %s", self.__session.name)

    def receive(self, size=None):
        if self.isOpen():
            return self.__session.recv(size)
        else:
            return "ERROR-TCP_DISCONNECT"

    def query(self, cmd, tmo=2000, size=None, description=None):
        if self.isOpen():
            self.send(cmd, description)
            return self.read_until(tmo, terminator=self.__terminator, size=size, description=description)
        else:
            return "ERROR-TCP_DISCONNECT"

    def read_line(self, timeout):
        if self.isOpen():
            return self.read_until(timeout, terminator='\n')
        else:
            return "ERROR-TCP_DISCONNECT"

    def read_until(self, tmo=None, terminator=">", size=None, description=None):
        lenterm = len(terminator)
        timeout = 0
        line = str()
        c = str()
        if self.isOpen():
            while True:
                try:
                    c = self.__session.recv(1024)
                except Exception as e:
                    timeout += self.__timeout * 1000
                    if timeout >= tmo:
                        return "ERROR - TIMEOUT"
                if c:
                    line += c
                    if line[-lenterm:] == terminator:
                        break
                    if size is not None and len(line) >= size:
                        break
            self.log(str(datetime.now()) + ' '*3+"Receive:'{0}' \n".format(line.strip()))
            return line
        else:
            return "ERROR-TCP_DISCONNECT"


if __name__ == '__main__':
    cfg = {
            "type": "Tester",
            "id": "123456",
            "endstr": "\r\n",
            "ip": "192.168.0.100",
            "port": 1110
        }
    tcp_c = TcpCommunicate(cfg=cfg)
    cmd=None
    print tcp_c.query(cmd=cmd)