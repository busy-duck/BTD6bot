"""Functions that handle in-game menu navigations before and after each game.

Menu navigation is done with simulating mouse inputs on predetermined locations.
Initial start condition is to search for main menu 'Play' button using ocr.

Handles a chunk of constant values: these are wrapped under separate classes to avoid polluting module 
namespace.
"""

from __future__ import annotations
from typing import TYPE_CHECKING
import json
import pathlib
import time

import pyautogui
import pynput

from bot import kb_mouse
from bot.commands.flow import AutoStart
from bot.commands.hero import Hero
from bot.commands.monkey import Monkey
from bot.bot_vars import BotVars
import bot.hotkeys
from bot.kb_mouse import ScreenRes
from bot.menu_return import OcrLocations
from bot.ocr.ocr import OcrValues
from bot.ocr.ocr import weak_substring_check
from bot.ocr.ocr_reader import OCR_READER
from bot.rounds import Rounds
from bot.times import PauseControl
from customprint import cprint

if TYPE_CHECKING:
    from typing import Any

class MouseLocations:
    """Wrapper class for mouse click locations.
    
    Attributes:
        HEROES (dict[str, tuple[float, float]], class attribute): Dictionary of hero name keys with locations as values.
        HEROES2 (dict[str, tuple[float, float]], class attribute): Dictionary of hero names locations that don't show 
            initally; hero panel window needs to be scrolled down to access these.
        BUTTONS (dict[str, tuple[float, float]], class attribute): Menu buttons.
        DIFFICULTY (dict[str, tuple[float, float]], class attribute): Menu location of specific difficulty setting 
            (easy, medium, hard).
        MODES (dict[str, tuple[float, float]], class attribute): Menu locations of specific mode (standard, primary 
            only, reverse, impoppable, chimps etc.)
        SAVE_OVERRIDE (tuple[float, float], class attribute): After selecting mode, if user has previous save on a map, 
            a button asking overriding it pops here.
        HEROSCREEN_SCROLL (tuple[float, float], class attribute): Hero panel location to access more heroes by 
            scrolling down while mouse is in this location. 
    """
    HEROES: dict[str, tuple[float, float]] = {
        'quincy' : (0.0552083333333, 0.2018518518519),
        'gwen' : (0.1338541666667, 0.2111111111111),
        'striker' : (0.2192708333333, 0.2064814814815),
        'obyn' : (0.0567708333333, 0.3777777777778),
        'rosalia' : (0.134375, 0.387962962963),
        'churchill' : (0.2171875, 0.3916666666667),
        'benjamin' : (0.0572916666667, 0.5648148148148),
        'pat' : (0.1401041666667, 0.5731481481481),
        'ezili' : (0.2130208333333, 0.5787037037037),
        'adora' : (0.0567708333333, 0.7546296296296),
        'etienne' : (0.1354166666667, 0.75),
        'sauda' : (0.2161458333333, 0.7453703703704),
        'brickell' : (0.0526041666667, 0.9157407407407),
        'psi' : (0.1307291666667, 0.9203703703704),
        'geraldo' : (0.2104166666667, 0.9148148148148)
        }
    HEROES2: dict[str, tuple[float, float]] = {
        'corvus' : (0.0541666666667, 0.835185185185266667)
        }  
    BUTTONS: dict[str, tuple[float, float]] = {
        'heroes' : (0.275, 0.8888888888889),
        'hero_select' : (0.5734375, 0.5592592592593),

        'menu_play' : (0.5, 0.8657407407407),
        'search_map' : (0.0395833333333, 0.1518518518519),
        'search_map_bar' :(0.4338541666667, 0.0462962962963),
        'choose_map' : (0.2817708333333, 0.3055555555556),
        } 
    DIFFICULTY: dict[str, tuple[float, float]] = {
        'EASY' : (0.3255208333333, 0.3814814814815),
        'MEDIUM' : (0.5026041666667, 0.3833333333333),
        'HARD' : (0.6744791666667, 0.3861111111111)
        }   
    MODES: dict[str, tuple[float, float]] = {
        'standard' : (0.3276041666667, 0.5564814814815),
        'top_left' : (0.5036458333333, 0.4259259259259),
        'top_middle' : (0.6651041666667, 0.4425925925926),
        'top_right' : (0.8348958333333, 0.4296296296296),
        'bottom_left' : (0.503125, 0.7027777777778),
        'bottom_middle' : (0.6682291666667, 0.6981481481481),
        'bottom_right' : (0.8411458333333, 0.6990740740741)
        }
    SAVE_OVERRIDE: tuple[float, float] = (0.5984375, 0.6842592592593)
    HEROSCREEN_SCROLL: tuple[float, float] = (0.1401041666667, 0.5731481481481)


def _scroll_down_heroes() -> None:
    """Scrolls down hero screen allowing access to more heroes."""
    m = pynput.mouse.Controller()
    pyautogui.moveTo(kb_mouse.pixel_position(MouseLocations.HEROSCREEN_SCROLL)) 
    for _ in range(0,4):
        m.scroll(0, -1)
        time.sleep(0.1)

def _choose_hero(hero_name: str | None) -> bool:
    """In menu screen, chooses a correct hero.

    Can also choose set None so hero won't change - useful in modes like deflation where hero might not be necessary.

    Updates current hero name for Hero class.

    Args:
        hero_name: Lower/uppercase doesn't matter, only that name is spelled correctly.
    """
    all_heroes = (tuple(MouseLocations.HEROES.keys()),
                  tuple(MouseLocations.HEROES2.keys()))
    if hero_name is None or hero_name.lower() not in set().union(*all_heroes):
        cprint('No hero used in current plan')
        Hero.current_plan_hero_name = hero_name
        return True
    else:
        cprint("Selecting", hero_name.capitalize(), "as hero... ", end='')
        kb_mouse.click(MouseLocations.BUTTONS['heroes'])
        start: int = time.time()
        loop: int = 1
        while loop:
            for letter in ('s','e','l','e','c','t','e','d'):
                if not weak_substring_check(letter, (0.5296875, 0.5472222222222, 0.6338541666667, 0.5916666666667),
                                       OCR_READER):
                    if time.time()-start >= 10:
                        return False
                    time.sleep(0.3)
                else:
                    loop = 0
                    break
        if hero_name.lower() in MouseLocations.HEROES:
            kb_mouse.click(MouseLocations.HEROES[hero_name.lower()])
            Hero.current_plan_hero_name = hero_name
        elif hero_name.lower() in MouseLocations.HEROES2:
            _scroll_down_heroes()
            kb_mouse.click(MouseLocations.HEROES2[hero_name.lower()])
            Hero.current_plan_hero_name = hero_name
    time.sleep(0.3)
    kb_mouse.click(MouseLocations.BUTTONS['hero_select'])
    time.sleep(0.3)
    kb_mouse.press_esc()
    cprint("Hero selected!")
    return True

def _choose_map(map_name: str) -> bool:
    """Chooses correct map by first clicking the map search bar and then typing the map name.
    
    Args:
        map_name: Map name.

    Returns:
        A boolean indicating if map selection was succesful. If False value is returned, it allows for bot to return
            to main menu screen.
    """
    start: int = time.time()
    loop: int = 1
    while loop:
        for letter in ('p','l','a','y'):
            if not weak_substring_check(letter, OcrLocations.MENU_PLAYTEXT, OCR_READER):
                if time.time()-start >= 10:
                    return False
                time.sleep(0.3)
            else:
                loop = 0
                break
    search_map = pynput.keyboard.Controller()
    map_str = map_name.replace('_', ' ')
    kb_mouse.click(MouseLocations.BUTTONS['menu_play'])
    start = time.time()
    search_found = 0
    time.sleep(0.4)
    kb_mouse.click(MouseLocations.BUTTONS['search_map'])
    if BotVars.windowed:
        loop = 1
        while time.time()-start <= 5 and loop:
            for letter in ('s','e','a','r','c','h'):
                if weak_substring_check(letter, (0.4140625, 0.0203703703704, 0.4651041666667, 0.0537037037037),
                                        OCR_READER):
                    search_found = 1
                    loop = 0
                    break
                else:
                    time.sleep(0.3)
        if not search_found:
            search_found = 0
            kb_mouse.click(MouseLocations.BUTTONS['search_map'], ignore_windowed=True)
            start = time.time()
            while time.time()-start <= 5 and loop:
                for letter in ('s','e','a','r','c','h'):
                    if weak_substring_check('r', (0.4140625, 0.0203703703704, 0.4651041666667, 0.0537037037037), 
                                            OCR_READER):
                        search_found = 1
                        loop = 0
                        break
                    else:
                        time.sleep(0.3)
            if not search_found:
                return False        
    time.sleep(0.4)
    kb_mouse.click(MouseLocations.BUTTONS['search_map_bar'])
    time.sleep(0.4)
    search_map.type(map_str)  # types map name to search bar.
    kb_mouse.click(MouseLocations.BUTTONS['choose_map'])
    return True

def _choose_diff(d: str) -> None:
    """Chooses correct difficulty setting.

    Difficulties are written all capitalized.

    Args:
        d: Difficulty.
    """
    kb_mouse.click(MouseLocations.DIFFICULTY[d])

def _choose_mode(m: str) -> None:
    """Chooses correct game mode.

    Modes are written all capitalized.

    Args:
        m: Game mode.
    """
    if m == 'STANDARD':
        kb_mouse.click(MouseLocations.MODES['standard'])
    elif m in {'PRIMARY', 'MILITARY', 'MAGIC'}:
        kb_mouse.click(MouseLocations.MODES['top_left'])
    elif m in {'DEFLATION', 'APOPALYPSE', 'DOUBLE_HP'}:
        kb_mouse.click(MouseLocations.MODES['top_middle'])
    elif m == 'HALFCASH':
        kb_mouse.click(MouseLocations.MODES['top_right'])
    elif m in {'REVERSE', 'ALTERNATE'}:
        kb_mouse.click(MouseLocations.MODES['bottom_left'])
    elif m == 'IMPOPPABLE':
        kb_mouse.click(MouseLocations.MODES['bottom_middle'])
    elif m == 'CHIMPS':                                          
        kb_mouse.click(MouseLocations.MODES['bottom_right'])
    kb_mouse.click(MouseLocations.SAVE_OVERRIDE)  # if a previous save exists, overwrite it.

def _reset_global_targeting() -> None:
    Monkey._wingmonkey = 0
    Monkey._elite_sniper = 0

def _update_external_variables(begin_r: int, end_r: int) -> None:
    """Initializes all external class-level variables used within bot package.
    
    This function should only be called by menu.load.

    Args:
        begin_r: First round.
        end_r: Final round.
    """
    OcrValues._log_ocr_deltas = False
    bot.hotkeys.generate_hotkeys(bot.hotkeys.hotkeys)
    Rounds.begin_round, Rounds.end_round = begin_r, end_r
    BotVars.defeat_status = False
    Rounds.exit_type = 'defeat'
    AutoStart.called_forward = False
    PauseControl.pause_length = 0
    BotVars.paused = False 
    _reset_global_targeting()
    try:
        with open(pathlib.Path(__file__).parent.parent/'Files'/'gui_vars.json') as f:
            gui_vars_dict: dict[str, Any] = json.load(f)
    except json.decoder.JSONDecodeError:
        cprint('gui_vars.json not found or cannot be read. Defaulting to bot_vars default values.')
        return
    try:
        customres_val: bool = gui_vars_dict["check_resolution"]
        resolution_val: list[int] = list(map(int, gui_vars_dict["custom_resolution"].split('x')))
        if customres_val:
            ScreenRes.update_res(resolution_val[0], resolution_val[1])
        else:
            ScreenRes.set_baseres()
        windowed_val: bool = gui_vars_dict["windowed"]
        event_val: str = gui_vars_dict["current_event_status"]
        time_limit_val: int = gui_vars_dict["checking_time_limit"]
        deltaocr_val: bool = gui_vars_dict["delta_ocrtext"]
        substringocr_val: bool = gui_vars_dict["substring_ocrtext"]
        frequency_val: float = gui_vars_dict["ocr_frequency"]
        BotVars.windowed = windowed_val
        BotVars.current_event_status = event_val
        BotVars.checking_time_limit = time_limit_val
        BotVars.print_delta_ocrtext = deltaocr_val
        BotVars.print_substring_ocrtext = substringocr_val
        OcrValues.read_file_frequency = frequency_val
    except ValueError:
        cprint("Unable to read at least one of the gui_vars.json keys. Defaulting to bot_vars initial values.")

def _start_plan() -> None:
    """Resets counter if mouse moves during it."""
    cprint('Starting plan in...', end=' ')
    timer = 3
    x, y = pyautogui.position()
    while timer > 0:
        for i in range(3, 0, -1):
            if (x, y) != tuple(pyautogui.position()):
                cprint("\nMouse moved, reseting timer!")
                cprint('Starting plan in...', end=' ')
                time.sleep(0.1)
                timer = 3
                x, y = pyautogui.position()
                break
            cprint(i, end=' ', flush=True)
            time.sleep(1)
            timer -= 1
    cprint()
    cprint('--> *Bot running*')

def load(map_name: str, diff: str, mode: str, begin_round: int, end_round: int, hero: str) -> tuple[int, int]:
    """Sets up pre-game conditions for the plan by choosing correct hero, map, difficulty and game mode.

    Updates begin and end rounds for bot.rounds.

    Args:
        map_name: Map name.
        diff: Difficulty setting.
        mode: Game mode.
        begin_round: First round of selected game mode.
        end_round: Final round of selected game mode.
        hero: Hero name.

    Returns:
        Begin and end rounds.
    """
    _update_external_variables(begin_round, end_round)
    cprint('Searching for main menu screen...')
    loop: int = 1
    while loop:
        for letter in ('p','l','a','y'):
            if not weak_substring_check(letter, OcrLocations.MENU_PLAYTEXT, OCR_READER):
                time.sleep(0.3)
            else:
                loop = 0
                break
    _start_plan()
    if not _choose_hero(hero):
        return 0, 0
    if not _choose_map(map_name):
        return 0, 0
    _choose_diff(diff)
    _choose_mode(mode)
    return begin_round, end_round