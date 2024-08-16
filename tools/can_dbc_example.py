import math
import can
import cantools
import time

db = cantools.database.load_file("odrive-cansimple.dbc")
#print(db)

# bus = can.Bus("vcan0", bustype="virtual")
bus = can.Bus("can0", bustype="socketcan")
axisID = 0x07

print("\nRequesting AXIS_STATE_FULL_CALIBRATION_SEQUENCE (0x03) on axisID: " + str(axisID))
msg = db.get_message_by_name('Axis'+str(axisID)+'_Set_Axis_State')
data = msg.encode({'Axis_Requested_State': 0x03})
msg = can.Message(arbitration_id=msg.frame_id | axisID << 5, is_extended_id=False, data=data)
print(db.decode_message('Axis'+str(axisID)+'_Set_Axis_State', msg.data))
print(msg)

try:
    bus.send(msg)
    print("Message sent on {}".format(bus.channel_info))
except can.CanError:
    print("Message NOT sent!  Please verify can0 is working first")

print("Waiting for calibration to finish...")
# Read messages infinitely and wait for the right ID to show up
while True:
    msg = bus.recv()
    if msg.arbitration_id == ((axisID << 5) | db.get_message_by_name('Axis'+str(axisID)+'_Heartbeat').frame_id):
        current_state = db.decode_message('Axis'+str(axisID)+'_Heartbeat', msg.data)['Axis_State']
        print("Current state: " + str(current_state))
        if current_state == "IDLE":
            print("\nAxis has returned to Idle state.")
            break

for msg in bus:
    if msg.arbitration_id == ((axisID << 5) | db.get_message_by_name('Axis'+str(axisID)+'_Heartbeat').frame_id):
        errorCode = db.decode_message('Axis'+str(axisID)+'_Heartbeat', msg.data)['Axis_Error']
        if errorCode == "NONE":
            print("No errors")
        else:
            print("Axis error!  Error code: "+str(errorCode))
        break

print("\nPutting axis",axisID,"into AXIS_STATE_CLOSED_LOOP_CONTROL (0x08)...")
data = db.encode_message('Axis'+str(axisID)+'_Set_Axis_State', {'Axis_Requested_State': 0x08})
msg = can.Message(arbitration_id=0x07 | axisID << 5, is_extended_id=False, data=data)
print(msg)

try:
    bus.send(msg)
    print("Message sent on {}".format(bus.channel_info))
except can.CanError:
    print("Message NOT sent!")

for msg in bus:
    if msg.arbitration_id == 0x01 | axisID << 5:
        print("\nReceived Axis heartbeat message:")
        msg = db.decode_message('Axis'+str(axisID)+'_Heartbeat', msg.data)
        print(msg)
        if msg['Axis_State'] == "CLOSED_LOOP_CONTROL":
            print("Axis has entered closed loop")
        else:
            print("Axis failed to enter closed loop")
        break

target = 0

data = db.encode_message('Axis'+str(axisID)+'_Set_Limits', {'Velocity_Limit':10.0, 'Current_Limit':10.0})
msg = can.Message(arbitration_id=axisID << 5 | 0x00F, is_extended_id=False, data=data)
bus.send(msg)

t0 = time.monotonic()
while True:
    setpoint = 1.0 * math.sin((time.monotonic() - t0)*2)
    # print("goto " + str(setpoint))
    data = db.encode_message('Axis'+str(axisID)+'_Set_Input_Pos', {'Input_Pos':setpoint, 'Vel_FF':0.0, 'Torque_FF':0.0})
    msg = can.Message(arbitration_id=axisID << 5 | 0x00C, data=data, is_extended_id=False)
    bus.send(msg)
    time.sleep(0.01)