from pyhap.accessory import Accessory, Bridge
from rpi_rf import RFDevice
from adafruit_motor import servo
import logging
import time
from dusty.shutdownswitch import ShutdownSwitch

logger = logging.getLogger(__name__)

class DustyBridge(Bridge):

    def __init__(self, driver, max_switches, pca, config):
        super().__init__(driver, "Dusty Bridge")

        self.config = config

        # Setup RF Transmitter
        self.rf = RFDevice(self.config.rf.pin)
        self.rf.enable_tx()
        self.rf.tx_repeat = self.config.rf.tx_repeat
        self.rf.tx_proto = self.config.rf.tx_proto

        self.dust_collector_on = False
        self.gate_to_close = None
        self.active_switch = None
        self.gate_close_counter = -1
        self.servos = {}
        for pin in range(max_switches):
            self.servos[pin] = servo.ContinuousServo(pca.channels[pin], min_pulse=self.config.servo.min_pulse, max_pulse=self.config.servo.max_pulse)
            self.add_accessory(DustySwitch(self, pin, driver, "Dusty Switch #"+str(pin)))
        shutdown_switch = ShutdownSwitch(driver,"Halt")
        self.add_accessory(shutdown_switch)

    def turn_on(self, switch):
        if self.active_switch:
            self.close_gate(self.active_switch.pin)
            self.active_switch.power_down()

        self.gate_close_counter =  0
        self.gate_to_close = None

        self.active_switch = switch
        self.open_gate(self.active_switch.pin)
        self.turn_on_dust_collector()

    def turn_off(self, switch):
        self.gate_to_close = switch.pin
        self.active_switch = None
        self.gate_close_counter = self.config.dusty.gate_close_pause
        self.turn_off_dust_collector()
        pass

    def close_gate(self, pin):
        self.servos[pin].throttle = self.config.servo.throttle
        time.sleep(self.config.servo.close_time)
        self.servos[pin].throttle = 0
        logger.info("Close Gate #" + str(pin))

    def open_gate(self, pin):
        self.servos[pin].throttle = self.config.servo.throttle * -1
        time.sleep(self.config.servo.open_time)
        self.servos[pin].throttle = 0
        logger.info("Open Gate #" + str(pin))

    def turn_on_dust_collector(self):
        if not self.dust_collector_on:
            self.dust_collector_on = True
            if self.config.rf.enabled:
                self.rf.tx_code(self.config.rf.on_code)
            else:
                logger.info("rf disbaled")
            logger.info("turn on dust collector")

    def turn_off_dust_collector(self):
        self.dust_collector_on = False
        if self.config.rf.enabled:
            self.rf.tx_code(self.config.rf.off_code)
        else:
            logger.info("rf disbaled")
        logger.info("turn off dust collector")

    def stop(self):
        self.rf.cleanup()

    @Accessory.run_at_interval(1)
    def run (self):
        if self.gate_close_counter > 0:
            self.gate_close_counter -= 1
            logger.info("counting down "+str(self.gate_close_counter))
        if self.gate_to_close != None and self.gate_close_counter == 0:
            self.close_gate(self.gate_to_close)
            self.gate_to_close = None


class DustySwitch(Accessory):

    def __init__(self, bridge, pin, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bridge = bridge
        self.pin = pin
        service = self.add_preload_service('Switch')
        self.switch_char = service.configure_char('On', setter_callback=self.set_state)

    def set_state(self, state):
        logger.info("State Change: "+str(state))
        if state  == 1:
            self.turn_on()
        else:
            self.turn_off()

    def turn_on(self):
        logger.info(self.display_name + " turn on")
        self.bridge.turn_on(self)

    def turn_off(self):
        logger.info(self.display_name + " turn off")
        self.bridge.turn_off(self)

    def power_down(self):
        logger.info(self.display_name + " power down")
        self.switch_char.set_value(0)
        pass

    def run(self):
        pass
