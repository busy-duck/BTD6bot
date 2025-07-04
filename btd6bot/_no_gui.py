"""Gui-free lite version of BTD6bot.

Cannot change settings or enable game modes, as these are controlled via gui.

Can play any currently supported plan, though, as bot is entirely separated from gui functionality-wise. 
"""

import json
import os
from pathlib import Path
import signal
import threading
import time

import pynput.keyboard
from pynput.keyboard import Key, KeyCode

from bot.bot_vars import BotVars
from customprint import cprint, cinput
import set_plan
import utils.plan_data
import gui.gui_tools as gui_tools
from gui.guihotkeys import GuiHotkeys

class BotThread:
    bot_thread: threading.Thread

def run() -> None:
    """Main loop for no-gui version of BTD6bot."""
    def exit(key: Key | KeyCode | None) -> None:
        """Program termination via hotkey.

        Args:
            key: Latest keyboard key the user has pressed.       
        """
        if key == GuiHotkeys.exit_hotkey or (isinstance(key, KeyCode) and key.char == GuiHotkeys.exit_hotkey):
            cprint("Process terminated.")
            os.kill(os.getpid(), signal.SIGTERM)
        elif (key == GuiHotkeys.start_stop_hotkey or 
             (isinstance(key, KeyCode) and key.char == GuiHotkeys.start_stop_hotkey)):
            gui_tools.terminate_thread(BotThread.bot_thread)

    # listener thread object sends keyboard inputs to exit function
    kb_listener = pynput.keyboard.Listener(on_press = exit)
    kb_listener.daemon = True
    kb_listener.start()

    with open(Path(__file__).parent.parent/'Logs.txt', 'w') as f:
        ...
    with open(Path(__file__).parent/'Files'/'gui_vars.json') as f:
        if json.load(f)["logging"]:
            BotVars.logging = True
    
    INFO_MESSAGE = ('*This version does not currently support collection event/queue/replay modes. To change any '
          'settings/hotkeys,\n'
          'use the gui version, make changes there and they will be shared with this version as well.\n'
          'Gui hotkeys \'start-stop\', \'exit\' and \'pause\' also work.\n'
          '/////////\n'
          '--Commands--\n'
          'help = displays this message again\n'
          'adjust = if ocr adjust setting is enabled, runs adjusting process\n'
          'plans = lists all available plans.\n'
          'run plan_name = run the plan plan_name <- replace this with an existing plan name.\n'
          '                  >Note that when you use \'run ...\' command first time after running this script,\n'
          '                   the ocr reader is loaded into memory which might take a bit, just wait.\n'
          '                  >Example: run dark_castleEasyStandard\n'
          'exit = exit program.'
          )
    
    cprint('===================================\n'
          '|   Welcome to gui-free BTD6bot   |\n'
          '===================================\n'
          ">>> Ocr reader model is loaded into memory, please wait...")
    from bot.ocr.ocr_reader import OCR_READER # type: ignore
    cprint('Model loaded.')
    print(INFO_MESSAGE)
    plans = utils.plan_data.read_plans()
    while 1:
        user_input = cinput('=>')
        if len(user_input) == 0:
            ...
        elif user_input.lower() == 'help':
            print(INFO_MESSAGE)
        elif user_input.lower() == 'adjust':
            with open(Path(__file__).parent/'Files'/'gui_vars.json') as f:
                    gui_vars_dict= json.load(f)
            if gui_vars_dict["ocr_adjust_deltas"]:
                print(".-------------------------.\n"
                "| Ocr adjust mode enabled |\n"
                ".-------------------------.\n")
                set_plan.run_delta_adjust()
            else:
                cprint("Auto-adjusting not enabled.")
        elif user_input.lower() == 'plans':
            print('All available plans: \n')
            for p in plans:
                print(p)
        elif user_input.split()[0] == 'run':
            try:
                plan_name = user_input.split()[1]
                if plan_name in plans:
                    cprint("Running plan: "+"'"+plan_name+"'.\n" 
                            "============================================")
                    BotThread.bot_thread = threading.Thread(target=set_plan.plan_setup, args=[plan_name], daemon=True)
                    BotThread.bot_thread.start()
                    while BotThread.bot_thread.is_alive():
                        time.sleep(0.1)
                    print()
                else:
                    cprint('Plan not found.')
            except (TypeError, IndexError):
                cprint("Invalid plan input.")
        elif user_input.lower() == 'exit':
            break