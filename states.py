from aiogram.fsm.state import State, StatesGroup


class FrameStates(StatesGroup):
    waiting_for_frame_number = State()


class EngineerStates(StatesGroup):
    waiting_for_frame_number = State()
