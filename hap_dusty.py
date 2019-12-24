import signal
import logging
import busio

from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import CATEGORY_SWITCH
from adafruit_pca9685 import PCA9685
from board import SCL, SDA
from python_json_config import ConfigBuilder

from dusty.dusty import DustyBridge, DustySwitch

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")
logger = logging.getLogger()

builder = ConfigBuilder()
config = builder.parse_config('config.json')

i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c)
pca = PCA9685(i2c, reference_clock_speed=config.servo.reference_clock_speed)
pca.frequency = config.servo.frequency

driver = AccessoryDriver(port=config.dusty.port)
dusty_bridge = DustyBridge(driver, config.dusty.max_switches, pca, config)
driver.add_accessory(accessory=dusty_bridge)
signal.signal(signal.SIGTERM, driver.signal_handler)

driver.start()
