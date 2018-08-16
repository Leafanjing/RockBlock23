from __future__ import print_function
from builtins import str
import rockBlock23

from rockBlock23 import rockBlockProtocol


class MoExample(rockBlockProtocol):

    print()
    'stuff and things'

    def main(self):
        rb = rockBlock23.rockBlock("/dev/ttyUSB0", self)

        userText = input("Input what you would like RockBlock to send to the Iridium Sat \n")

        rb.sendMessage(userText)

        rb.close()

    def rockBlockTxStarted(self):
        print("rockBlockTxStarted")

    def rockBlockTxFailed(self):
        print("rockBlockTxFailed")

    def rockBlockTxSuccess(self, momsn):
        print(f"rockBlockTxSuccess{str(momsn)}")


if __name__ == '__main__':
    MoExample().main()