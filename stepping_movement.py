import time
from gpiozero import OutputDevice
from gpiozero.pins.pigpio import PiGPIOFactory
# import numpy as np

# PIN settings
PIN_MOTOR_1 = (21)
PIN_MOTOR_2 = (17)
PIN_MOTOR_3 = (27)
PIN_MOTOR_4 = (22)

# wave mode
vlist_wave = [
    [1, 0, 0, 0],   # step1
    [0, 1, 0, 0],   # step2
    [0, 0, 1, 0],   # step3
    [0, 0, 0, 1],   # step4
    [1, 0, 0, 0],   # step5(step1)
    [0, 1, 0, 0],   # step6(step2)
    [0, 0, 1, 0],   # step7(step3)
    [0, 0, 0, 1],   # step8(step4)
]

# full mode
vlist_full = [
    [1, 1, 0, 0],   # step1
    [0, 1, 1, 0],   # step2
    [0, 0, 1, 1],   # step3
    [1, 0, 0, 1],   # step4
    [1, 1, 0, 0],   # step5(step1)
    [0, 1, 1, 0],   # step6(step2)
    [0, 0, 1, 1],   # step7(step3)
    [1, 0, 0, 1],   # step8(step4)
]

# half mode
vlist_half = [
    [1, 0, 0, 0],   # step1
    [1, 1, 0, 0],   # step2
    [0, 1, 0, 0],   # step3
    [0, 1, 1, 0],   # step4
    [0, 0, 1, 0],   # step5
    [0, 0, 1, 1],   # step6
    [0, 0, 0, 1],   # step7
    [1, 0, 0, 1],   # step8
]

class Stepper():
    def __init__(self,  number_of_steps, mpins, method_step="half"):
        self.step_number = 0                   # which step the motor is on
        self.direction = 0                     # motor direction
        self.last_step_time = 0                # time stamp in us of the last step taken
        self.number_of_steps = number_of_steps  # total number of steps for this motor

        # stepping method
        self._method_step = method_step
        if "full" == method_step:
            self._vlist = vlist_full
        elif "wave" == method_step:
            self._vlist = vlist_wave
        else:
            self._vlist = vlist_half
            self._method_step = "half"

        # setup the pins on the microcontroller:
        factory = PiGPIOFactory()
        self._mpins = [OutputDevice(pin, pin_factory=factory) for pin in mpins]
        self.set_speed()
        return

    def set_speed(self, what_speed=10):
        ''' Sets the speed in revs per minute
        '''
        self.step_delay = 60 * 1000 * 1000 * 1000 / self.number_of_steps / what_speed
        return

    def step(self, steps_to_move, auto_stop=True):
        ''' Moves the motor steps_to_move steps.  If the number is negative,
            the motor moves in the reverse direction.
        '''
        if "half" == self._method_step:
            steps_to_move *= 2
        steps_left = abs(steps_to_move)  # how many steps to take

        # determine direction based on whether steps_to_mode is + or -:
        self.direction = 1 if steps_to_move > 0 else 0

        # decrement the number of steps, moving one step each time:
        while steps_left > 0:
            now = time.time_ns()
            # move only if the appropriate delay has passed:
            if (now - self.last_step_time) >= self.step_delay:
                # get the timeStamp of when you stepped:
                self.last_step_time = now
                # increment or decrement the step number,
                # depending on direction:
                if self.direction == 1:
                    self.step_number += 1
                    if self.step_number == self.number_of_steps:
                        self.step_number = 0
                else:
                    if self.step_number == 0:
                        self.step_number = self.number_of_steps
                    self.step_number -= 1

                # decrement the steps left:
                steps_left -= 1
                # step the motor to step number 0, 1, 2, ..., 7
                self._step_motor(self.step_number % 8)

        if auto_stop:
            self.stop()
        return

    def _step_motor(self, this_step):
        ''' 各Pinに対し、HIGH/LOW
        '''
        for val, mpin in zip(self._vlist[this_step], self._mpins):
            mpin.on() if val else mpin.off()
        return

    def stop(self):
        for mpin in self._mpins:
            mpin.off()
        return


def main():

    MOTOR_STEPS = (2048)

    # 動作モード指定
    # my_motor = Stepper(MOTOR_STEPS, [PIN_MOTOR_1, PIN_MOTOR_2, PIN_MOTOR_3, PIN_MOTOR_4], "wave")
    # my_motor = Stepper(MOTOR_STEPS, [PIN_MOTOR_1, PIN_MOTOR_2, PIN_MOTOR_3, PIN_MOTOR_4], "full")
    my_motor = Stepper(MOTOR_STEPS, [PIN_MOTOR_1, PIN_MOTOR_2, PIN_MOTOR_3, PIN_MOTOR_4], "half")

    my_motor.set_speed(10)

    # 時計回り　-> 反時計回り
    my_motor.step(-2048)
    my_motor.step(2048)


    # 徐々にはやく回転させる
    # for speed in np.arange(5, 16, 0.01):
    #     my_motor.set_speed(speed)
    #     my_motor.step(8)

    return


if __name__ == "__main__":
    main()