import copy
import crcmod
from selfdrive.config import Conversions as CV
from selfdrive.car.tesla.values import CANBUS, CarControllerParams


class TeslaCAN:
  def __init__(self, packer, longitudinal_packer):
    self.packer = packer
    self.longitudinal_packer = longitudinal_packer
    self.crc = crcmod.mkCrcFun(0x11d, initCrc=0x00, rev=False, xorOut=0xff)

  @staticmethod
  def checksum(msg_id, dat):
    # TODO: get message ID from name instead
    ret = (msg_id & 0xFF) + ((msg_id >> 8) & 0xFF)
    ret += sum(dat)
    return ret & 0xFF

  def create_steering_control(self, angle, enabled, frame):
    values = {
      "DAS_steeringAngleRequest": -angle,
      "DAS_steeringHapticRequest": 0,
      "DAS_steeringControlType": 1 if enabled else 0,
      "DAS_steeringControlCounter": (frame % 16),
    }

    data = self.packer.make_can_msg("DAS_steeringControl", CANBUS.chassis, values)[2]
    values["DAS_steeringControlChecksum"] = self.checksum(0x488, data[:3])
    return self.packer.make_can_msg("DAS_steeringControl", CANBUS.chassis, values)

  def create_action_request(self, msg_stw_actn_req, cancel, bus, counter):
    values = copy.copy(msg_stw_actn_req)

    if cancel:
      values["SpdCtrlLvr_Stat"] = 1
      values["MC_STW_ACTN_RQ"] = counter

    data = self.packer.make_can_msg("STW_ACTN_RQ", bus, values)[2]
    values["CRC_STW_ACTN_RQ"] = self.crc(data[:7])
    return self.packer.make_can_msg("STW_ACTN_RQ", bus, values)

  def create_longitudinal_command(self, enabled, speed, min_accel, max_accel, frame):
    values = {
      "DAS_setSpeed": speed * CV.MS_TO_KPH,
      "DAS_accState": 4 if enabled else 0,
      "DAS_aebEvent": 0,
      "DAS_jerkMin": CarControllerParams.JERK_LIMIT_MIN,
      "DAS_jerkMax": CarControllerParams.JERK_LIMIT_MAX,
      "DAS_accelMin": min_accel,
      "DAS_accelMax": max_accel,
      "DAS_controlCounter": (frame % 8),
    }

    data = self.longitudinal_packer.make_can_msg("DAS_control", CANBUS.powertrain, values)[2]
    values["DAS_controlChecksum"] = self.checksum(0x2bf, data[:3])
    return self.longitudinal_packer.make_can_msg("DAS_control", CANBUS.powertrain, values)
